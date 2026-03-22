# main.py — Point d'entrée Gestion Dettes Premium
"""
Lance le serveur Flask en arrière-plan puis ouvre l'interface dans le navigateur.
Compatible PyInstaller --onefile et installateur Inno Setup.
"""

import sys
import os
import time
import threading
import webbrowser

# ── Résolution des chemins PyInstaller ───────────────────────────────────────

def base_dir():
    """Retourne le dossier des fichiers embarqués (_MEIPASS si frozen)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def data_dir():
    """
    Retourne le dossier où stocker dettes.db :
    - Mode installe  : %APPDATA%/Gestion Perso/
    - Mode portable  : dossier de l'exe
    - Mode dev       : dossier du script
    """
    if getattr(sys, "frozen", False):
        # Vérifier si on est installé dans Program Files
        exe_dir = os.path.dirname(sys.executable)
        prog_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        prog_files86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
        is_installed = (
            exe_dir.lower().startswith(prog_files.lower()) or
            exe_dir.lower().startswith(prog_files86.lower())
        )
        if is_installed:
            # Installé → données dans AppData (accessible sans droits admin)
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            d = os.path.join(appdata, "Gestion Perso")
            os.makedirs(d, exist_ok=True)
            return d
        else:
            # Portable → données à côté de l'exe
            return exe_dir
    return os.path.dirname(os.path.abspath(__file__))

# Configurer les chemins
DATA_DIR = data_dir()
DB_PATH  = os.path.join(DATA_DIR, "dettes.db")

os.chdir(DATA_DIR)
sys.path.insert(0, base_dir())

# ── Imports après résolution du path ─────────────────────────────────────────

import db
import api

# Pointer la base vers le bon dossier
db.DB_FILE = DB_PATH

HOST = "127.0.0.1"
PORT = 5000
URL  = f"http://{HOST}:{PORT}"

# ── Démarrage ────────────────────────────────────────────────────────────────

def _wait_then_open():
    """Attend que Flask soit prêt, puis ouvre le navigateur."""
    import urllib.request
    for _ in range(20):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"{URL}/api/auth/status", timeout=1)
            break
        except Exception:
            continue
    webbrowser.open(URL)

def main():
    print(f"[Gestion Perso] Démarrage sur {URL}")
    print(f"[Gestion Perso] Base de données : {DB_PATH}")

    db.init_db()

    # Vérifier que l'interface web est accessible
    web_path = os.path.join(base_dir(), "web", "index.html")
    if not os.path.exists(web_path):
        print(f"[Gestion Perso] ERREUR : interface web introuvable a {web_path}")
    else:
        print(f"[Gestion Perso] Interface web trouvee : {web_path}")

    # PIN par défaut si premier lancement
    if not db.has_pin():
        db.set_pin("1234")
        print("[Gestion Perso] PIN par defaut cree : 1234")

    # Ouvrir le navigateur dans un thread séparé
    t = threading.Thread(target=_wait_then_open, daemon=True)
    t.start()

    # Vérifier mise à jour en arrière-plan
    try:
        import updater
        updater.check_in_background(
            notify_flask_fn=lambda r: print(f"[Gestion Perso] Mise a jour disponible : {r.get('version')}")
        )
    except ImportError:
        pass

    # Lancer Flask (bloquant)
    api.start(host=HOST, port=PORT, debug=False)

if __name__ == "__main__":
    main()