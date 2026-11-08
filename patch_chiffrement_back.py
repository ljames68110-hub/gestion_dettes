#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_chiffrement_back.py
Permet d'activer le chiffrement de la base depuis l'appli (quand elle est en clair) :
  - main.py : fonction _setup_encryption(pwd) + enregistrement du handler
  - api.py  : routes /api/encrypt/status et /api/encrypt/setup
Une fois active, le mot de passe sera demande au prochain lancement, et la base
(photos comprises, elles sont dans la base) est protegee.
Idempotent, verifie la syntaxe. A lancer dans le dossier projet.
"""
import os, sys, py_compile

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def L(b, eol): return eol.join(b.split("\n"))

MAIN_FUNC = '''def _setup_encryption(pwd):
    """Active le chiffrement quand la base est en clair. Cree le sel + le .enc."""
    global DB_PASSWORD, _SALT, ENCRYPTION_ON
    pwd = str(pwd or "").strip()
    if len(pwd) < 4:
        return {"ok": False, "error": "Mot de passe trop court (4 caracteres minimum)"}
    if os.path.exists(ENC_PATH):
        return {"ok": False, "error": "La base est deja chiffree"}
    if not os.path.exists(DB_PATH):
        return {"ok": False, "error": "Aucune base a chiffrer"}
    try:
        import crypto_db
        salt = crypto_db.new_salt()
        with open(SALT_PATH, "wb") as f:
            f.write(salt)
        _SALT = salt
        DB_PASSWORD = pwd
        ENCRYPTION_ON = True
        crypto_db.encrypt_file(DB_PATH, ENC_PATH, pwd, salt)
        print("[Gestion Perso] Chiffrement active depuis l'appli.")
        return {"ok": True, "message": "Base chiffree. Le mot de passe sera demande au prochain lancement."}
    except Exception as e:
        return {"ok": False, "error": "Echec du chiffrement : %s" % e}


'''

API_BLOCK = '''

# CHIFFREMENT DEPUIS L'APPLI -- ne pas dupliquer
_ENCRYPT_HANDLER = None
def set_encrypt_handler(fn):
    global _ENCRYPT_HANDLER
    _ENCRYPT_HANDLER = fn

@app.route("/api/encrypt/status")
@require_auth
def encrypt_status():
    enc = os.path.join(os.path.dirname(os.path.abspath(db.DB_FILE)), "dettes.db.enc")
    return ok({"encrypted": os.path.exists(enc)})

@app.route("/api/encrypt/setup", methods=["POST"])
@require_auth
def encrypt_setup():
    if _ENCRYPT_HANDLER is None:
        return err("Indisponible ici (relance l'appli normalement)")
    data = request.json or {}
    res = _ENCRYPT_HANDLER(str(data.get("password", ""))) or {}
    if res.get("ok"):
        return ok({"message": res.get("message", "Base chiffree")})
    return err(res.get("error", "Echec du chiffrement"))
'''

def main():
    for f in ("main.py", "api.py"):
        if not os.path.exists(f):
            print("ERREUR : lance depuis le dossier du projet (%s manquant)" % f); sys.exit(1)

    # --- main.py
    m = read("main.py"); eol = eol_of(m)
    if "_setup_encryption" not in m:
        a1 = "def _boot_app_after_unlock():"
        if m.count(a1) != 1:
            print("  [X] main.py : ancre _boot_app_after_unlock %dx" % m.count(a1)); sys.exit(1)
        m = m.replace(a1, L(MAIN_FUNC, eol) + a1, 1)
        a2 = "    atexit.register(_save_backup_on_exit)"
        if m.count(a2) != 1:
            print("  [X] main.py : ancre atexit.register %dx" % m.count(a2)); sys.exit(1)
        m = m.replace(a2, a2 + eol + "    api.set_encrypt_handler(_setup_encryption)", 1)
        write("main.py", m)
        print("  [+] main.py : _setup_encryption + handler enregistre")
    else:
        print("  [=] main.py : deja patche")

    # --- api.py
    a = read("api.py"); eol = eol_of(a)
    if "/api/encrypt/setup" not in a:
        if not a.endswith(("\n", "\r")): a += eol
        a += L(API_BLOCK, eol)
        write("api.py", a)
        print("  [+] api.py : routes /api/encrypt/status + /api/encrypt/setup")
    else:
        print("  [=] api.py : deja patche")

    print("Verification syntaxe...")
    for f in ("main.py", "api.py"):
        try:
            py_compile.compile(f, doraise=True); print("  [ok] %s" % f)
        except py_compile.PyCompileError as e:
            print("  [X] %s : %s" % (f, e)); sys.exit(1)
    print("\nTermine (backend chiffrement).")

if __name__ == "__main__":
    main()
