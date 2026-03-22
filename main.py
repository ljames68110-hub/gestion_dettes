# main.py — Point d'entrée Gestion Perso
"""
Lance Flask en arrière-plan puis ouvre une fenêtre native via PyWebView.
Si PyWebView n'est pas disponible, fallback sur le navigateur.
Compatible PyInstaller --onefile et installateur Inno Setup.
"""

import sys
import os
import time
import threading

def base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def data_dir():
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        prog_files   = os.environ.get("PROGRAMFILES",      "C:\\Program Files")
        prog_files86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
        if exe_dir.lower().startswith(prog_files.lower()) or \
           exe_dir.lower().startswith(prog_files86.lower()):
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            d = os.path.join(appdata, "GestionPerso")
            os.makedirs(d, exist_ok=True)
            return d
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))

DATA_DIR = data_dir()
DB_PATH  = os.path.join(DATA_DIR, "dettes.db")
os.chdir(DATA_DIR)
sys.path.insert(0, base_dir())

import db
import api

db.DB_FILE = DB_PATH

# Import module de chiffrement
try:
    import crypto_db
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("[Gestion Perso] crypto_db absent — base non chiffree")
HOST = "127.0.0.1"
PORT = 5000
URL  = f"http://{HOST}:{PORT}"

def get_icon_path():
    for p in [
        os.path.join(base_dir(), "app_icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "app_icon.ico"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico"),
    ]:
        if os.path.exists(p): return p
    return None

def wait_for_flask():
    import urllib.request
    for _ in range(40):
        time.sleep(0.25)
        try:
            urllib.request.urlopen(f"{URL}/api/auth/status", timeout=1)
            return True
        except: continue
    return False

def start_flask():
    api.start(host=HOST, port=PORT, debug=False)

def main():
    print(f"[Gestion Perso] Demarrage {URL}")
    print(f"[Gestion Perso] DB : {DB_PATH}")

    # ── Chiffrement AES-256 ──────────────────────────────────────────────
    if HAS_CRYPTO:
        # Récupérer le PIN depuis la base auth (s'il existe déjà)
        # Au tout premier lancement : pas de base chiffrée, on init normalement
        enc_exists = os.path.exists(DB_PATH + ".enc")
        plain_exists = os.path.exists(DB_PATH)

        if not enc_exists and not plain_exists:
            # Premier lancement : créer la base, puis chiffrer avec PIN par défaut
            db.init_db()
            if not db.has_pin():
                db.set_pin("1234")
                print("[Gestion Perso] PIN par defaut : 1234")
            pin_for_crypto = "1234"
        elif plain_exists and not enc_exists:
            # Base existante non chiffrée → migration
            db.init_db()
            if not db.has_pin():
                db.set_pin("1234")
            # Lire le PIN hashé — on utilise "1234" comme clé par défaut pour migration
            pin_for_crypto = "1234"
            crypto_db.migrate_existing_db(DB_PATH, pin_for_crypto)
        else:
            # Base chiffrée existante — déchiffrer avec PIN par défaut
            # (le vrai PIN sera vérifié par l'interface web via /api/auth/login)
            pin_for_crypto = "1234"

        # Ouvrir session chiffrée — retourne chemin fichier temp
        try:
            temp_path = crypto_db.open_encrypted_session(DB_PATH, pin_for_crypto)
            db.DB_FILE = temp_path
            print(f"[Gestion Perso] Session chiffree ouverte")
        except ValueError as e:
            print(f"[Gestion Perso] ERREUR dechiffrement : {e}")
            print("[Gestion Perso] La base est peut-etre corrompue")
    else:
        db.init_db()
        if not db.has_pin():
            db.set_pin("1234")
            print("[Gestion Perso] PIN par defaut : 1234")

    db.init_db()

    try:
        import updater
        updater.check_in_background(
            notify_flask_fn=lambda r: print(f"[Gestion Perso] MAJ : {r.get('version')}")
        )
    except ImportError: pass

    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    print("[Gestion Perso] Attente Flask...")
    if not wait_for_flask():
        print("[Gestion Perso] Timeout — fallback navigateur")
        import webbrowser; webbrowser.open(URL)
        flask_thread.join(); return

    print("[Gestion Perso] Flask OK !")

    try:
        import webview
        icon = get_icon_path()
        print("[Gestion Perso] PyWebView — fenetre native")
        window = webview.create_window(
            title            = "Gestion Perso",
            url              = URL,
            width            = 1280,
            height           = 800,
            min_size         = (900, 600),
            resizable        = True,
            background_color = "#0a0a0f",
        )
        webview.start(debug=False, icon=icon)
    except ImportError:
        print("[Gestion Perso] PyWebView absent — navigateur")
        import webbrowser; webbrowser.open(URL)
        flask_thread.join()

if __name__ == "__main__":
    main()
