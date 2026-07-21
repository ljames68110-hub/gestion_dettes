# updater.py — Mise à jour automatique depuis GitHub Releases
"""
Vérifie si une nouvelle version est disponible sur GitHub,
télécharge le nouvel exe et le remplace après redémarrage.
"""

import os
import sys
import json
import hashlib
import tempfile
import threading
import subprocess
import urllib.request
from pathlib import Path

LATEST_URL = "https://raw.githubusercontent.com/ljames68110-hub/gestion_dettes/main/latest.json"
CHECK_INTERVAL = 3600  # vérifier toutes les heures

APP_VERSION = "3.79"  # version courante - incremente a chaque MAJ

def get_current_exe():
    """Retourne le chemin de l'exe en cours d'exécution."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return None  # mode dev — pas de mise à jour

def get_current_version():
    """Version courante de l'app. En mode compile, lue depuis APP_VERSION (elle
    voyage donc avec l'exe). En dev, depuis latest.json local s'il existe."""
    if getattr(sys, "frozen", False):
        return {"version": APP_VERSION}
    local = Path(__file__).parent / "latest.json"
    if False and local.exists():   # dev: ignore latest.json perime, on prend APP_VERSION
        try:
            return json.loads(local.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": APP_VERSION}

REPO = "ljames68110-hub/gestion_dettes"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

def fetch_remote_info():
    """Recupere la derniere release depuis l API GitHub."""
    try:
        req = urllib.request.Request(
            LATEST_URL,
            headers={"User-Agent": "GestionPerso-Updater/1.0", "Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if not data.get("version"):
            return None
        return {
            "version":   data["version"],
            "asset_url": data.get("asset_url"),
            "sha256":    data.get("sha256")
        }
    except Exception as e:
        print(f"[Updater] Impossible de verifier : {e}")
        return None

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def version_gt(remote, local):
    """Compare deux versions semver ex: v0.1.33 > v0.1.32"""
    def parse(v):
        return [int(x) for x in v.lstrip("v").split(".") if x.isdigit()]
    try:
        return parse(remote) > parse(local)
    except Exception:
        return False

def download_update(url, dest, expected_sha=None, progress_cb=None):
    """Télécharge le fichier et vérifie le sha256."""
    req = urllib.request.Request(url, headers={"User-Agent": "DebtManager-Updater/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total:
                    progress_cb(downloaded / total)

    if expected_sha:
        actual = sha256_file(dest)
        if actual.lower() != expected_sha.lower():
            os.remove(dest)
            raise ValueError(f"SHA256 invalide : attendu {expected_sha}, obtenu {actual}")

def apply_update_windows(new_exe, current_exe):
    """
    Cree un .bat qui attend la fermeture de l'app, remplace l'exe, EFFACE les
    variables PyInstaller heritees (_MEIPASS2...) puis relance. Sans cet effacement,
    le nouveau .exe cherche python3xx.dll dans le dossier temp de l'ancienne
    instance (supprime) -> 'python3xx.dll introuvable'.
    """
    bat_path = os.path.join(os.path.dirname(current_exe), "_gp_update.bat")
    exe_name = os.path.basename(current_exe)
    bat = (
        "@echo off\r\n"
        "setlocal enabledelayedexpansion\r\n"
        "echo Mise a jour en cours...\r\n"
        ":waitproc\r\n"
        'tasklist /fi "imagename eq __EXE__" 2>nul | find /i "__EXE__" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "    ping -n 2 127.0.0.1 >nul\r\n"
        "    goto waitproc\r\n"
        ")\r\n"
        "set /a tries=0\r\n"
        ":domove\r\n"
        'move /y "__NEW__" "__CUR__" >nul 2>&1\r\n'
        "if not errorlevel 1 goto moveok\r\n"
        "set /a tries+=1\r\n"
        "if !tries! geq 30 goto movefail\r\n"
        "ping -n 2 127.0.0.1 >nul\r\n"
        "goto domove\r\n"
        ":moveok\r\n"
        'set "_MEIPASS2="\r\n'
        'set "_PYI_ARCHIVE_INDEX="\r\n'
        'set "_PYI_APPLICATION_HOME_DIR="\r\n'
        'set "_PYI_PARENT_PROCESS_LEVEL="\r\n'
        "ping -n 3 127.0.0.1 >nul\r\n"
        'start "" "__CUR__"\r\n'
        "goto cleanup\r\n"
        ":movefail\r\n"
        "echo ERREUR: fichier verrouille.\r\n"
        "pause\r\n"
        ":cleanup\r\n"
        'del "%~f0"\r\n'
    )
    bat = bat.replace("__EXE__", exe_name).replace("__NEW__", new_exe).replace("__CUR__", current_exe)
    with open(bat_path, "w", encoding="ascii") as f:
        f.write(bat)
    subprocess.Popen(
        'cmd /c "' + bat_path + '"',
        shell=True,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )

def check_and_update(on_update_available=None, on_progress=None, on_done=None):
    """
    Vérifie et applique la mise à jour.
    Callbacks:
      on_update_available(remote_info) → appelé si mise à jour dispo, retourne True pour continuer
      on_progress(float 0-1)           → progression du téléchargement
      on_done(success, message)        → fin du processus
    """
    current = get_current_version()
    remote  = fetch_remote_info()

    if not remote:
        if on_done: on_done(False, "Impossible de vérifier les mises à jour.")
        return

    if not version_gt(remote.get("version", "0"), current.get("version", "0")):
        if on_done: on_done(True, f"Déjà à jour ({current.get('version', '?')}).")
        return

    # Mise à jour disponible
    if on_update_available:
        proceed = on_update_available(remote)
        if not proceed:
            if on_done: on_done(False, "Mise à jour annulée.")
            return

    current_exe = get_current_exe()
    if not current_exe:
        if on_done: on_done(False, "Mode développement — pas de remplacement d'exe.")
        return

    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".exe",
            dir=current_exe.parent,
            delete=False
        )
        tmp.close()

        download_update(
            url          = remote["asset_url"],
            dest         = tmp.name,
            expected_sha = remote.get("sha256"),
            progress_cb  = on_progress,
        )

        apply_update_windows(tmp.name, str(current_exe))

        if on_done: on_done(True, f"Mise a jour {remote['version']} prete - redemarrage...")
        # Attendre 2 secondes pour que Flask reponde OK au frontend
        import time
        time.sleep(2)
        os._exit(0)

    except Exception as e:
        if on_done: on_done(False, f"Erreur : {e}")

def check_in_background(notify_flask_fn=None):
    """Lance la vérification dans un thread, appelle notify_flask_fn si update dispo."""
    def _run():
        current = get_current_version()
        remote  = fetch_remote_info()
        if not remote:
            return
        if version_gt(remote.get("version","0"), current.get("version","0")):
            print(f"[Updater] Mise à jour disponible : {remote['version']}")
            if notify_flask_fn:
                notify_flask_fn(remote)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
