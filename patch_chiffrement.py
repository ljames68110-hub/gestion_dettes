#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_chiffrement.py
 - cree crypto_db.py (si absent)
 - patche main.py : deverrouillage au demarrage + rechiffrement a la fermeture,
   ACTIF UNIQUEMENT si dettes.db.enc existe (sinon comportement inchange).
A lancer dans le dossier projet : python patch_chiffrement.py
(le module crypto_db.py doit etre present : ce script le cree)
"""
import os
def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def to_eol(b,eol): return eol.join(b.split("\n"))

CRYPTO_DB = '''# crypto_db.py — Chiffrement de la base au repos (Fernet + PBKDF2)
import os, base64, hashlib
from cryptography.fernet import Fernet
_ITER = 200000
def derive_key(password, salt):
    raw = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITER)
    return base64.urlsafe_b64encode(raw)
def new_salt():
    return os.urandom(16)
def encrypt_file(plain_path, enc_path, password, salt):
    with open(plain_path, "rb") as f:
        data = f.read()
    token = Fernet(derive_key(password, salt)).encrypt(data)
    tmp = enc_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(token)
    os.replace(tmp, enc_path)
def decrypt_file(enc_path, plain_path, password, salt):
    with open(enc_path, "rb") as f:
        token = f.read()
    data = Fernet(derive_key(password, salt)).decrypt(token)
    tmp = plain_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, plain_path)
'''

CRYPTO_BLOCK = '''
# -- Chiffrement de la base (actif seulement si dettes.db.enc existe) ----------
ENC_PATH  = os.path.join(DATA_DIR, "dettes.db.enc")
SALT_PATH = os.path.join(DATA_DIR, "dettes.salt")
ENCRYPTION_ON = os.path.exists(ENC_PATH)
DB_PASSWORD = None
_SALT = None

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
    """Rechiffre la base et efface la version en clair."""
    try:
        import crypto_db
        if os.path.exists(DB_PATH) and DB_PASSWORD is not None and _SALT is not None:
            crypto_db.encrypt_file(DB_PATH, ENC_PATH, DB_PASSWORD, _SALT)
            os.remove(DB_PATH)
            print("[Gestion Perso] Base rechiffree.")
    except Exception as e:
        print("[Gestion Perso] Echec rechiffrement:", e)
'''

GUARD = '''    if ENCRYPTION_ON and DB_PASSWORD is not None:
        _lock_db_on_exit(); return'''

def patch_main(path="main.py"):
    t=read(path); eol=eol_of(t)
    if "def _unlock_db" in t:
        print("main.py : chiffrement deja patche, saute"); return
    # 1) bloc crypto apres "db.DB_FILE = DB_PATH"
    a="db.DB_FILE = DB_PATH"
    i=t.find(a)
    if i==-1:
        print("ATTENTION main.py : ancre 'db.DB_FILE = DB_PATH' introuvable"); return
    i=i+len(a)
    t=t[:i]+eol+to_eol(CRYPTO_BLOCK,eol)+t[i:]
    # 2) garde au debut de _save_backup_on_exit (apres sa docstring)
    doc='    """Copie de secours unique de la base, ecrasee a chaque fermeture."""'
    j=t.find(doc)
    if j==-1:
        print("ATTENTION main.py : docstring _save_backup_on_exit introuvable"); return
    j=j+len(doc)
    t=t[:j]+eol+to_eol(GUARD,eol)+t[j:]
    # 3) appel _unlock_db() avant db.init_db()
    k_anchor="    db.init_db()"
    k=t.find(k_anchor)
    if k==-1:
        print("ATTENTION main.py : 'db.init_db()' introuvable"); return
    t=t[:k]+"    _unlock_db()"+eol+t[k:]
    write(path,t)
    print("main.py : deverrouillage demarrage + rechiffrement fermeture ajoutes OK")

if __name__=="__main__":
    if not os.path.exists("crypto_db.py"):
        write("crypto_db.py", CRYPTO_DB); print("crypto_db.py cree")
    else:
        print("crypto_db.py deja present")
    if os.path.exists("main.py"): patch_main()
    else: print("ATTENTION main.py introuvable")
    print("=== TERMINE ===")
