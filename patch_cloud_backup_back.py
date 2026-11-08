#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_cloud_backup_back.py
Sauvegarde automatique de la base vers un dossier cloud (OneDrive / Google Drive)
a chaque fermeture de l'appli. La base part CHIFFREE (.enc + .salt).

  - cree cloud_backup.py (module)
  - main.py  : helper _cloud_backup_safe() + appels a la fermeture (chiffre et secours)
  - api.py   : routes /api/cloud-backup (get/set/pick/run)
  - release.yml : bundle cloud_backup.py dans l'exe

Idempotent, verifie la syntaxe. A lancer dans le dossier projet.
"""
import os, sys, py_compile

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"

CLOUD_MODULE = '''# -*- coding: utf-8 -*-
"""Sauvegarde de la base vers un dossier cloud synchronise (OneDrive / Google Drive).
Config dans <data_dir>/cloud_backup.json : {"enabled": bool, "dir": "chemin"}.
La base copiee est CHIFFREE (dettes.db.enc + dettes.salt) ; si pas de chiffrement,
copie la base en clair (ton cloud, prive)."""
import os, json, shutil, datetime

def _cfg_path(data_dir):
    return os.path.join(data_dir, "cloud_backup.json")

def load_config(data_dir):
    try:
        with open(_cfg_path(data_dir), "r", encoding="utf-8") as f:
            d = json.load(f)
        return {"enabled": bool(d.get("enabled")), "dir": d.get("dir") or ""}
    except Exception:
        return {"enabled": False, "dir": ""}

def save_config(data_dir, enabled, folder):
    cfg = {"enabled": bool(enabled), "dir": (folder or "").strip()}
    try:
        with open(_cfg_path(data_dir), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except Exception:
        pass
    return cfg

def do_backup(data_dir, enc_path, salt_path, db_path, keep=15):
    """Copie la base vers le dossier cloud. Retourne (ok:bool, msg:str, dest:str)."""
    cfg = load_config(data_dir)
    if not cfg.get("enabled"):
        return (False, "desactive", "")
    d = cfg.get("dir") or ""
    if not d or not os.path.isdir(d):
        return (False, "dossier introuvable", "")
    dest = os.path.join(d, "GestionPerso")
    try:
        os.makedirs(dest, exist_ok=True)
    except Exception as e:
        return (False, "dossier non accessible (%s)" % e, "")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        if os.path.exists(enc_path):
            shutil.copy2(enc_path, os.path.join(dest, "dettes.db.enc"))
            shutil.copy2(enc_path, os.path.join(dest, "dettes-%s.db.enc" % stamp))
            if os.path.exists(salt_path):
                shutil.copy2(salt_path, os.path.join(dest, "dettes.salt"))
            suffix = ".db.enc"
        elif os.path.exists(db_path):
            shutil.copy2(db_path, os.path.join(dest, "dettes.db"))
            shutil.copy2(db_path, os.path.join(dest, "dettes-%s.db" % stamp))
            suffix = ".db"
        else:
            return (False, "aucune base a sauvegarder", "")
    except Exception as e:
        return (False, "copie echouee (%s)" % e, "")
    # purge : garder les N copies horodatees les plus recentes
    try:
        hist = sorted(f for f in os.listdir(dest)
                      if f.startswith("dettes-") and f.endswith(suffix))
        for old in hist[:-keep]:
            try: os.remove(os.path.join(dest, old))
            except Exception: pass
    except Exception:
        pass
    return (True, "ok", dest)
'''

MAIN_HELPER = '''

def _cloud_backup_safe():
    """Copie la base chiffree vers le dossier cloud configure (jamais bloquant)."""
    try:
        import cloud_backup
        ok_, msg, dest = cloud_backup.do_backup(DATA_DIR, ENC_PATH, SALT_PATH, DB_PATH)
        if ok_:
            print("[Gestion Perso] Sauvegarde cloud ->", dest)
        elif msg != "desactive":
            print("[Gestion Perso] Sauvegarde cloud:", msg)
    except Exception as e:
        print("[Gestion Perso] Sauvegarde cloud echouee:", e)
'''

API_BLOCK = '''

# SAUVEGARDE CLOUD -- ne pas dupliquer
def _gp_data_dir():
    return os.path.dirname(os.path.abspath(db.DB_FILE)) or "."

@app.route("/api/cloud-backup", methods=["GET"])
@require_auth
def cloud_backup_get():
    import cloud_backup
    return ok(cloud_backup.load_config(_gp_data_dir()))

@app.route("/api/cloud-backup", methods=["POST"])
@require_auth
def cloud_backup_set():
    import cloud_backup
    d = request.json or {}
    return ok(cloud_backup.save_config(_gp_data_dir(), d.get("enabled"), d.get("dir")))

@app.route("/api/cloud-backup/pick", methods=["POST"])
@require_auth
def cloud_backup_pick():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="Choisir le dossier cloud (OneDrive / Google Drive)")
        root.destroy()
    except Exception as e:
        return err("Impossible d'ouvrir le selecteur : %s" % e)
    return ok({"dir": path or ""})

@app.route("/api/cloud-backup/run", methods=["POST"])
@require_auth
def cloud_backup_run():
    import cloud_backup
    dd = _gp_data_dir()
    enc = os.path.join(dd, "dettes.db.enc")
    salt = os.path.join(dd, "dettes.salt")
    ok_, msg, dest = cloud_backup.do_backup(dd, enc, salt, db.DB_FILE)
    if ok_:
        return ok({"message": "Sauvegarde envoyee", "dest": dest})
    return err("Sauvegarde impossible : %s" % msg)
'''

def main():
    for f in ("main.py", "api.py"):
        if not os.path.exists(f):
            print("ERREUR : lance depuis le dossier du projet (%s manquant)" % f); sys.exit(1)

    # 1) module cloud_backup.py
    if os.path.exists("cloud_backup.py") and "def do_backup(" in read("cloud_backup.py"):
        print("  [=] cloud_backup.py : deja present")
    else:
        write("cloud_backup.py", CLOUD_MODULE)
        print("  [+] cloud_backup.py cree")

    # 2) main.py : helper + 2 hooks
    m = read("main.py"); eol = eol_of(m)
    def L(block): return eol.join(block.split("\n"))
    if "_cloud_backup_safe" not in m:
        anchor = '        print("[Gestion Perso] Echec rechiffrement:", e)'
        if m.count(anchor) != 1:
            print("  [X] main.py : ancre helper %dx" % m.count(anchor)); sys.exit(1)
        m = m.replace(anchor, anchor + L(MAIN_HELPER), 1)
        # hook chiffre
        h1o = "        _lock_db_on_exit(); return"
        h1n = "        _lock_db_on_exit(); _cloud_backup_safe(); return"
        if m.count(h1o) == 1:
            m = m.replace(h1o, h1n, 1)
        else:
            print("  [X] main.py : ancre hook chiffre %dx" % m.count(h1o)); sys.exit(1)
        # hook secours (clair)
        h2o = ('    except Exception as e:' + eol +
               '        print(f"[Gestion Perso] Echec sauvegarde fermeture : {e}")')
        h2n = h2o + eol + "    _cloud_backup_safe()"
        if m.count(h2o) == 1:
            m = m.replace(h2o, h2n, 1)
        else:
            print("  [!] main.py : hook secours non trouve (%dx) -- le mode chiffre reste couvert" % m.count(h2o))
        write("main.py", m)
        print("  [+] main.py : sauvegarde cloud branchee sur la fermeture")
    else:
        print("  [=] main.py : deja patche")

    # 3) api.py : routes
    a = read("api.py"); eol = eol_of(a)
    if "/api/cloud-backup" not in a:
        if not a.endswith(("\n", "\r")): a += eol
        a += eol.join(API_BLOCK.split("\n"))
        write("api.py", a)
        print("  [+] api.py : routes /api/cloud-backup ajoutees")
    else:
        print("  [=] api.py : deja patche")

    # 4) release.yml : bundler cloud_backup.py
    ry = os.path.join(".github", "workflows", "release.yml")
    if os.path.exists(ry):
        y = read(ry); yeol = eol_of(y)
        if "cloud_backup.py;." not in y:
            lines = y.split(yeol)
            idx = [i for i, ln in enumerate(lines) if '--add-data "crypto_db.py;."' in ln]
            if len(idx) == 1:
                base = lines[idx[0]]
                indent = base[:len(base) - len(base.lstrip())]
                tick = " `" if base.rstrip().endswith("`") else ""
                lines.insert(idx[0] + 1, indent + '--add-data "cloud_backup.py;."' + tick)
                write(ry, yeol.join(lines))
                print("  [+] release.yml : cloud_backup.py bundle dans l'exe")
            else:
                print("  [!] release.yml : ancre add-data non trouvee -- ajoute a la main si besoin")
        else:
            print("  [=] release.yml : deja a jour")
    else:
        print("  [!] release.yml absent (ok si tu ne construis pas via GitHub)")

    print("Verification syntaxe...")
    for f in ("cloud_backup.py", "main.py", "api.py"):
        try:
            py_compile.compile(f, doraise=True); print("  [ok] %s" % f)
        except py_compile.PyCompileError as e:
            print("  [X] %s : %s" % (f, e)); sys.exit(1)
    print("\nTermine (backend).")

if __name__ == "__main__":
    main()
