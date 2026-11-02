# -*- coding: utf-8 -*-
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
