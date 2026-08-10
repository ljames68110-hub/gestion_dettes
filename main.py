# main.py - Point d'entree Gestion Perso
"""
Lance Flask en arriere-plan puis ouvre une fenetre native via PyWebView.
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
        appdata = os.environ.get("APPDATA", "") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        d = os.path.join(appdata, "GestionPerso")
        os.makedirs(d, exist_ok=True)
        # Migration unique depuis Documents\GestionPerso (ancien emplacement)
        try:
            if not os.path.exists(os.path.join(d, "dettes.db.enc")) and not os.path.exists(os.path.join(d, "dettes.db")):
                home = os.path.expanduser("~")
                old_dir = os.path.join(home, "Documents", "GestionPerso")
                if os.path.isdir(old_dir):
                    import shutil
                    for _n in ("dettes.db.enc", "dettes.salt", "dettes.db", "dettes_backup.db"):
                        _s = os.path.join(old_dir, _n)
                        if os.path.exists(_s):
                            shutil.copy2(_s, os.path.join(d, _n))
                    _ob = os.path.join(old_dir, "backups")
                    if os.path.isdir(_ob):
                        _nb = os.path.join(d, "backups")
                        os.makedirs(_nb, exist_ok=True)
                        for _n in os.listdir(_ob):
                            try:
                                shutil.copy2(os.path.join(_ob, _n), os.path.join(_nb, _n))
                            except Exception:
                                pass
                    print("[Gestion Perso] Donnees migrees depuis Documents vers AppData")
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

ENC_PATH  = os.path.join(DATA_DIR, "dettes.db.enc")
SALT_PATH = os.path.join(DATA_DIR, "dettes.salt")
ENCRYPTION_ON = os.path.exists(ENC_PATH)
DB_PASSWORD = None
_SALT = None
_LOCKED_DONE = False
_BOOTED = False
_FLASK_STARTED = False
PHONE_CERT = os.path.join(DATA_DIR, "phone.crt")
PHONE_KEY  = os.path.join(DATA_DIR, "phone.key")
_PHONE_STARTED = False

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

def _info_box(msg):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showwarning("Gestion Perso", msg)
        root.destroy()
    except Exception:
        print("[Gestion Perso]", msg)


def _unlock_db():
    """Repli : si la base est chiffree, demande le mot de passe (prompt natif) et la dechiffre."""
    global DB_PASSWORD, _SALT
    if not ENCRYPTION_ON:
        return
    import crypto_db
    try:
        from cryptography.fernet import InvalidToken
    except Exception:
        InvalidToken = ()
    if _SALT is None:
        try:
            with open(SALT_PATH, "rb") as f:
                _SALT = f.read()
        except Exception:
            print("[Gestion Perso] Sel introuvable, base illisible."); sys.exit(1)
    _preserve_crash_db()
    _msg = "Entrez votre mot de passe :"
    for _ in range(5):
        pwd = _ask_password(_msg)
        if not pwd:
            sys.exit(0)
        try:
            crypto_db.decrypt_file(ENC_PATH, DB_PATH, pwd, _SALT)
            DB_PASSWORD = pwd
            _rescue_crash_db()
            print("[Gestion Perso] Base dechiffree.")
            return
        except InvalidToken:
            _msg = "Mot de passe incorrect, reessayez :"
            print("[Gestion Perso] Mot de passe incorrect.")
        except (PermissionError, OSError):
            _info_box("Gestion Perso est deja ouvert.\n\nFerme l'autre fenetre (ou termine GestionPerso.exe dans le Gestionnaire des taches), puis relance.")
            print("[Gestion Perso] Base verrouillee : instance deja ouverte."); sys.exit(1)
        except Exception:
            _msg = "Mot de passe incorrect, reessayez :"
            print("[Gestion Perso] Erreur de dechiffrement.")
    print("[Gestion Perso] Trop d'essais, arret."); sys.exit(1)

def _lock_db_on_exit():
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

def _wait_url(path):
    """Attend qu'une URL statique reponde (sans toucher a la base)."""
    import urllib.request
    for _ in range(40):
        time.sleep(0.25)
        try:
            urllib.request.urlopen(f"{URL}{path}", timeout=1)
            return True
        except: continue
    return False

def start_flask():
    api.start(host=HOST, port=PORT, debug=False)

def _ensure_phone_cert():
    if os.path.exists(PHONE_CERT) and os.path.exists(PHONE_KEY):
        return True
    try:
        import datetime
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"GestionPerso")])
        san = x509.SubjectAlternativeName([x509.DNSName(u"localhost")])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(san, critical=False)
            .sign(key, hashes.SHA256()))
        with open(PHONE_KEY, "wb") as f:
            f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
        with open(PHONE_CERT, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        return True
    except Exception as e:
        print("[Gestion Perso] Certificat scan KO:", e)
        return False

def _start_phone_server():
    """Serveur HTTPS sur le reseau local pour le scan telephone (best-effort)."""
    global _PHONE_STARTED
    if _PHONE_STARTED:
        return
    if not _ensure_phone_cert():
        return
    _PHONE_STARTED = True
    def _run():
        try:
            api.start_phone_https(PHONE_CERT, PHONE_KEY)
        except Exception as e:
            print("[Gestion Perso] Serveur scan telephone KO:", e)
    threading.Thread(target=_run, daemon=True).start()
    print("[Gestion Perso] Serveur scan telephone (HTTPS) demarre.")

_AUTOSAVE_ON = False

def _snapshot_encrypt(tag=""):
    """Rechiffre la base courante (copie coherente SQLite) vers le .enc. Atomique."""
    import sqlite3, tempfile
    if DB_PASSWORD is None or _SALT is None or not os.path.exists(DB_PATH):
        return False
    import crypto_db
    fd, tmpdb = tempfile.mkstemp(suffix=".db", dir=DATA_DIR, prefix=".gp_save_")
    os.close(fd)
    try:
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(tmpdb)
        with dst:
            src.backup(dst)
        dst.close(); src.close()
        crypto_db.encrypt_file(tmpdb, ENC_PATH, DB_PASSWORD, _SALT)
        return True
    finally:
        try:
            os.remove(tmpdb)
        except Exception:
            pass

def _autosave_loop(interval=180):
    import time
    while True:
        time.sleep(interval)
        try:
            if _snapshot_encrypt("auto"):
                print("[Gestion Perso] Sauvegarde auto OK")
        except Exception as e:
            print("[Gestion Perso] Sauvegarde auto echouee :", e)

def _start_autosave():
    global _AUTOSAVE_ON
    if _AUTOSAVE_ON or DB_PASSWORD is None:
        return
    _AUTOSAVE_ON = True
    threading.Thread(target=_autosave_loop, daemon=True).start()
    print("[Gestion Perso] Sauvegarde automatique activee (3 min)")

def _preserve_crash_db():
    """Si un dettes.db en clair est plus recent que le .enc : arret brutal -> on le met de cote."""
    try:
        if not (os.path.exists(DB_PATH) and os.path.exists(ENC_PATH)):
            return
        if os.path.getmtime(DB_PATH) > os.path.getmtime(ENC_PATH) + 2:
            os.replace(DB_PATH, DB_PATH + ".crash")
            print("[Gestion Perso] Arret brutal detecte : base non rechiffree mise de cote.")
    except Exception as e:
        print("[Gestion Perso] Preservation crash echouee :", e)

def _rescue_crash_db():
    """Apres deverrouillage : chiffre la base rescapee dans backups/ puis efface le clair."""
    src = DB_PATH + ".crash"
    if not os.path.exists(src) or DB_PASSWORD is None or _SALT is None:
        return
    try:
        import crypto_db, datetime, sqlite3
        sqlite3.connect(src).close()
        bdir = os.path.join(DATA_DIR, "backups")
        os.makedirs(bdir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dst = os.path.join(bdir, "dettes-CRASH-" + stamp + ".db.enc")
        crypto_db.encrypt_file(src, dst, DB_PASSWORD, _SALT)
        print("[Gestion Perso] Base rescapee sauvegardee :", dst)
    except Exception as e:
        print("[Gestion Perso] Sauvegarde rescapee echouee :", e)
    finally:
        try:
            os.remove(src)
        except Exception:
            pass

def _ensure_flask_started():
    global _FLASK_STARTED
    if _FLASK_STARTED:
        return
    _FLASK_STARTED = True
    threading.Thread(target=start_flask, daemon=True).start()
    try:
        _start_autosave()
    except Exception as _e:
        print("[Gestion Perso] Autosave non demarre:", _e)
    try:
        _start_phone_server()
    except Exception as e:
        print("[Gestion Perso] Scan telephone non demarre:", e)


def _backup_enc(keep=15):
    """Sauvegarde datee de la base chiffree au lancement. Garde les <keep> plus recentes."""
    try:
        import shutil, glob, hashlib, datetime
        if not (ENC_PATH and os.path.exists(ENC_PATH) and os.path.getsize(ENC_PATH) > 0):
            return
        bdir = os.path.join(DATA_DIR, "backups")
        os.makedirs(bdir, exist_ok=True)
        try:
            _sb = os.path.join(bdir, "dettes.salt")
            if os.path.exists(SALT_PATH) and not os.path.exists(_sb):
                shutil.copy2(SALT_PATH, _sb)
        except Exception:
            pass
        existing = sorted(glob.glob(os.path.join(bdir, "dettes-*.db.enc")))
        try:
            with open(ENC_PATH, "rb") as _f:
                _cur = hashlib.md5(_f.read()).hexdigest()
            if existing:
                with open(existing[-1], "rb") as _f:
                    if hashlib.md5(_f.read()).hexdigest() == _cur:
                        return
        except Exception:
            pass
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dst = os.path.join(bdir, "dettes-" + stamp + ".db.enc")
        shutil.copy2(ENC_PATH, dst)
        print("[Gestion Perso] Sauvegarde :", dst)
        existing = sorted(glob.glob(os.path.join(bdir, "dettes-*.db.enc")))
        for _old in existing[:-keep]:
            try:
                os.remove(_old)
            except Exception:
                pass
    except Exception as _e:
        print("[Gestion Perso] Echec sauvegarde :", _e)


def _save_backup_on_exit():
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


def _boot_app_after_unlock():
    """Repli tkinter : Init DB + PIN + updater + Flask (une seule fois)."""
    global _BOOTED
    if _BOOTED:
        return
    _BOOTED = True
    db.init_db()
    if not db.has_pin():
        db.set_pin("1234")
        print("[Gestion Perso] PIN par defaut cree : 1234")
    try:
        import updater
        updater.check_in_background(
            notify_flask_fn=lambda r: print(f"[Gestion Perso] MAJ : {r.get('version')}")
        )
    except ImportError:
        pass
    _ensure_flask_started()
    print("[Gestion Perso] Attente Flask...")
    wait_for_flask()
    print("[Gestion Perso] Flask OK !")


class _GpApi:
    def screens(self):
        try:
            mons = _monitors()
            cur = _win_cfg().get("screen", None)
            return {"ok": True, "current": cur,
                    "screens": [{"index": i, "w": m["w"], "h": m["h"], "primary": m["primary"]}
                                for i, m in enumerate(mons)]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_screen(self, i):
        try:
            i = int(i)
            cfg = _win_cfg(); cfg["screen"] = i; _win_cfg_save(cfg)
            import webview as _wv
            wins = list(getattr(_wv, "windows", []) or [])
            if wins:
                _place_window(wins[0], i)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def open_second(self, i=None, page=""):
        try:
            import webview as _wv
            mons = _monitors()
            if not mons:
                return {"ok": False, "error": "Aucun ecran detecte"}
            try:
                idx = int(i)
            except Exception:
                idx = None
            if idx is None or not (0 <= idx < len(mons)):
                main_i, _ = _screen_index(None)
                idx = next((k for k in range(len(mons)) if k != main_i), main_i)
            w2 = _wv.create_window(
                title            = "Gestion Perso - 2e ecran",
                url              = URL + (page or ""),
                frameless        = True,
                easy_drag        = False,
                width            = 1280,
                height           = 800,
                background_color = "#0a0a0f",
                js_api           = _GpApi(),
            )
            threading.Timer(1.0, lambda: _place_window(w2, idx)).start()
            return {"ok": True, "screen": idx}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def minimize(self):
        try:
            import webview as _wv
            for w in list(getattr(_wv, "windows", []) or []):
                try:
                    w.minimize()
                except Exception:
                    pass
        except Exception:
            pass

    def quit(self):
        try:
            import webview as _wv
            for w in list(getattr(_wv, "windows", []) or []):
                try:
                    w.destroy()
                except Exception:
                    pass
        except Exception:
            pass


def _do_unlock(pwd):
    """Handler appele par Flask (/api/unlock) depuis l'ecran HTML. Dechiffre + prepare l'app."""
    global DB_PASSWORD
    if DB_PASSWORD is not None:
        return {"ok": True}
    if not pwd:
        return {"ok": False, "error": "Mot de passe vide"}
    import crypto_db
    try:
        from cryptography.fernet import InvalidToken
    except Exception:
        InvalidToken = ()
    try:
        _preserve_crash_db()
        crypto_db.decrypt_file(ENC_PATH, DB_PATH, pwd, _SALT)
        DB_PASSWORD = pwd
        _rescue_crash_db()
    except InvalidToken:
        return {"ok": False, "error": "Mot de passe incorrect"}
    except (PermissionError, OSError):
        return {"ok": False, "error": "Gestion Perso est deja ouvert. Ferme l'autre fenetre puis relance."}
    except Exception:
        return {"ok": False, "error": "Mot de passe incorrect"}
    try:
        db.init_db()
        if not db.has_pin():
            db.set_pin("1234")
            print("[Gestion Perso] PIN par defaut cree : 1234")
        try:
            import updater
            updater.check_in_background(
                notify_flask_fn=lambda r: print(f"[Gestion Perso] MAJ : {r.get('version')}")
            )
        except ImportError:
            pass
        print("[Gestion Perso] Base dechiffree (ecran HTML).")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": "Erreur demarrage: " + str(e)}


def _open_main_window():
    try:
        import webview
        icon = get_icon_path()
        print("[Gestion Perso] PyWebView - fenetre native")
        webview.create_window(
            title            = "Gestion Perso",
            frameless        = True,
            easy_drag        = False,
            url              = URL,
            width            = 1280,
            height           = 800,
            min_size         = (900, 600),
            resizable        = True,
            maximized        = True,
            background_color = "#0a0a0f",
            js_api           = _GpApi(),
        )
        def _pw1():
            try:
                import webview as _wv
                _ws = list(getattr(_wv, "windows", []) or [])
                if _ws:
                    _place_window(_ws[0])
            except Exception:
                pass
        webview.start(_pw1, debug=False, icon=icon, gui="edgechromium")
        _save_backup_on_exit()
    except ImportError:
        print("[Gestion Perso] PyWebView absent - navigateur")
        import webbrowser; webbrowser.open(URL)


WIN_CFG_PATH = os.path.join(DATA_DIR, "window.json")

def _win_cfg():
    try:
        import json
        with open(WIN_CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _win_cfg_save(d):
    try:
        import json
        with open(WIN_CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass

def _monitors():
    out = []
    try:
        import ctypes
        user32 = ctypes.windll.user32
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        class MONITORINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                        ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]
        PROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.POINTER(RECT), ctypes.c_void_p)
        def _cb(hmon, hdc, lprc, lparam):
            try:
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(mi)):
                    w = mi.rcWork
                    out.append({"x": int(w.left), "y": int(w.top),
                                "w": int(w.right - w.left), "h": int(w.bottom - w.top),
                                "primary": bool(mi.dwFlags & 1)})
            except Exception:
                pass
            return 1
        user32.EnumDisplayMonitors(None, None, PROC(_cb), 0)
    except Exception as e:
        print("[Gestion Perso] Detection ecrans impossible :", e)
    return out

def _screen_index(idx=None):
    mons = _monitors()
    if not mons:
        return None, []
    if idx is None:
        try:
            idx = int(_win_cfg().get("screen", -1))
        except Exception:
            idx = -1
    if not (0 <= idx < len(mons)):
        idx = next((i for i, m in enumerate(mons) if m.get("primary")), 0)
    return idx, mons

def _place_window(win, idx=None):
    """Place la fenetre plein ecran sur l'ecran choisi (hors barre des taches)."""
    try:
        try:
            win.restore()
        except Exception:
            pass
        _i, _mons = _screen_index(idx)
        if _mons:
            m = _mons[_i]
            try:
                win.resize(m["w"], m["h"])
            except Exception:
                pass
            try:
                win.move(m["x"], m["y"])
            except Exception:
                pass
            return
        import ctypes
        class _RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        r = _RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)
        w = int(r.right - r.left)
        h = int(r.bottom - r.top)
        if w > 200 and h > 200:
            try:
                win.resize(w, h)
            except Exception:
                pass
            try:
                win.move(int(r.left), int(r.top))
            except Exception:
                pass
    except Exception:
        pass


def main():
    global _SALT
    atexit.register(_save_backup_on_exit)
    _backup_enc()
    print(f"[Gestion Perso] Demarrage {URL}")
    print(f"[Gestion Perso] DB : {DB_PATH}")

    # --- Base chiffree : ecran de connexion HTML servi par Flask (http://, via /api/unlock) ---
    if ENCRYPTION_ON:
        try:
            with open(SALT_PATH, "rb") as f:
                _SALT = f.read()
        except Exception:
            _info_box("Sel introuvable, base illisible.")
            sys.exit(1)

        login_file = os.path.join(base_dir(), "web", "login.html")
        if os.path.exists(login_file):
            try:
                api.set_unlock_handler(_do_unlock)   # /api/unlock -> dechiffrement
                _ensure_flask_started()
                print("[Gestion Perso] Attente ecran de connexion...")
                if _wait_url("/login.html"):
                    import webview
                    icon = get_icon_path()
                    _win = webview.create_window(
                        title            = "Gestion Perso",
                        frameless        = True,
                        easy_drag        = False,
                        url              = URL + "/login.html?v=" + str(int(time.time())),
                        width            = 1280,
                        height           = 800,
                        min_size         = (900, 600),
                        resizable        = True,
                        maximized        = True,
                        background_color = "#0a0a0f",
                        js_api           = _GpApi(),
                    )
                    webview.start(lambda: _place_window(_win), debug=False, icon=icon, gui="edgechromium")
                    _save_backup_on_exit()
                    return
                else:
                    print("[Gestion Perso] /login.html injoignable, repli classique.")
            except Exception as e:
                print("[Gestion Perso] Ecran HTML indisponible, repli classique:", e)

        # Repli ultime : prompt natif (toujours fonctionnel)
        _unlock_db()
        _boot_app_after_unlock()
        _open_main_window()
        return

    # --- Base non chiffree : flux normal ---
    db.init_db()
    if not db.has_pin():
        db.set_pin("1234")
        print("[Gestion Perso] PIN par defaut cree : 1234")
    try:
        import updater
        updater.check_in_background(
            notify_flask_fn=lambda r: print(f"[Gestion Perso] MAJ : {r.get('version')}")
        )
    except ImportError:
        pass
    _ensure_flask_started()
    print("[Gestion Perso] Attente Flask...")
    if not wait_for_flask():
        print("[Gestion Perso] Timeout - fallback navigateur")
        import webbrowser; webbrowser.open(URL)
        return
    print("[Gestion Perso] Flask OK !")
    _open_main_window()


if __name__ == "__main__":
    main()
