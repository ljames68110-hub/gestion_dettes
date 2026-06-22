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
import atexit

def base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def data_dir():
    if getattr(sys, "frozen", False):
        # Stockage dans Documents\GestionPerso (toutes versions de l exe)
        home = os.path.expanduser("~")
        docs = os.path.join(home, "Documents")
        if not os.path.isdir(docs):
            docs = home
        d = os.path.join(docs, "GestionPerso")
        os.makedirs(d, exist_ok=True)
        # Migration unique depuis l ancien emplacement AppData
        try:
            new_db = os.path.join(d, "dettes.db")
            if not os.path.exists(new_db):
                appdata = os.environ.get("APPDATA", "")
                if appdata:
                    old_dir = os.path.join(appdata, "GestionPerso")
                    old_db = os.path.join(old_dir, "dettes.db")
                    if os.path.exists(old_db):
                        import shutil
                        shutil.copy2(old_db, new_db)
                        old_bak = os.path.join(old_dir, "dettes_backup.db")
                        if os.path.exists(old_bak):
                            shutil.copy2(old_bak, os.path.join(d, "dettes_backup.db"))
        except Exception:
            pass
        return d
    return os.path.dirname(os.path.abspath(__file__))

DATA_DIR = data_dir()
DB_PATH  = os.path.join(DATA_DIR, "dettes.db")
os.chdir(DATA_DIR)
sys.path.insert(0, base_dir())

import db
import api

db.DB_FILE = DB_PATH

# -- Chiffrement de la base (actif seulement si dettes.db.enc existe) ----------
ENC_PATH  = os.path.join(DATA_DIR, "dettes.db.enc")
SALT_PATH = os.path.join(DATA_DIR, "dettes.salt")
ENCRYPTION_ON = os.path.exists(ENC_PATH)
DB_PASSWORD = None
_SALT = None
_LOCKED_DONE = False

def _ask_password(msg):
    try:
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk(); root.withdraw()
        pwd = simpledialog.askstring("Gestion Perso", msg, show="*", parent=root)
        root.destroy()
        return pwd
    except Exception as e:
        print("[Gestion Perso] Saisie graphique impossible:", e)
        try:
            import getpass
            return getpass.getpass(msg + " ")
        except Exception:
            return None

def _unlock_db():
    """Si la base est chiffree, demande le mot de passe et la dechiffre."""
    global DB_PASSWORD, _SALT
    if not ENCRYPTION_ON:
        return
    import crypto_db
    try:
        with open(SALT_PATH, "rb") as f:
            _SALT = f.read()
    except Exception:
        print("[Gestion Perso] Sel introuvable, base illisible."); sys.exit(1)
    for _ in range(5):
        pwd = _ask_password("Entrez votre mot de passe :")
        if not pwd:
            sys.exit(0)
        try:
            crypto_db.decrypt_file(ENC_PATH, DB_PATH, pwd, _SALT)
            DB_PASSWORD = pwd
            print("[Gestion Perso] Base dechiffree.")
            return
        except Exception:
            print("[Gestion Perso] Mot de passe incorrect.")
    print("[Gestion Perso] Trop d'essais, arret."); sys.exit(1)

def _lock_db_on_exit():
    """Rechiffre la base et efface la version en clair (fiabilise)."""
    global _LOCKED_DONE
    if _LOCKED_DONE:
        return
    try:
        import crypto_db, time, gc
        if os.path.exists(DB_PATH) and DB_PASSWORD is not None and _SALT is not None:
            crypto_db.encrypt_file(DB_PATH, ENC_PATH, DB_PASSWORD, _SALT)
            gc.collect()
            removed = False
            for _ in range(12):
                try:
                    os.remove(DB_PATH); removed = True; break
                except OSError:
                    time.sleep(0.3)
            _LOCKED_DONE = True
            if removed:
                print("[Gestion Perso] Base rechiffree.")
            else:
                print("[Gestion Perso] Base rechiffree (clair non efface, sera ecrase au prochain demarrage).")
    except Exception as e:
        print("[Gestion Perso] Echec rechiffrement:", e)


# Chiffrement desactive
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


def _save_backup_on_exit():
    """Copie de secours unique de la base, ecrasee a chaque fermeture."""
    if ENCRYPTION_ON and DB_PASSWORD is not None:
        _lock_db_on_exit(); return
    try:
        import shutil
        if os.path.exists(DB_PATH):
            backup_path = os.path.join(DATA_DIR, "dettes_backup.db")
            shutil.copy2(DB_PATH, backup_path)
            print(f"[Gestion Perso] Sauvegarde de secours : {backup_path}")
    except Exception as e:
        print(f"[Gestion Perso] Echec sauvegarde fermeture : {e}")

def main():
    atexit.register(_save_backup_on_exit)
    print(f"[Gestion Perso] Demarrage {URL}")
    print(f"[Gestion Perso] DB : {DB_PATH}")

    # Chiffrement désactivé temporairement — base SQLite standard
    _unlock_db()
    db.init_db()
    if not db.has_pin():
        db.set_pin("1234")
        print("[Gestion Perso] PIN par defaut cree : 1234")

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
            maximized        = True,
            background_color = "#0a0a0f",
        )
        webview.start(debug=False, icon=icon, gui="edgechromium")
        _save_backup_on_exit()  # apres fermeture fenetre
    except ImportError:
        print("[Gestion Perso] PyWebView absent — navigateur")
        import webbrowser; webbrowser.open(URL)
        flask_thread.join()

if __name__ == "__main__":
    main()
