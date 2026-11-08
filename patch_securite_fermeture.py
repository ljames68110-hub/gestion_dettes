#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_securite_fermeture.py  (Point 5)
Quand le chiffrement est actif, supprime tout fichier de base EN CLAIR qui pourrait
trainer dans le dossier de donnees (anciennes sauvegardes .db, fichiers .tmp/.ancien,
base clair obsolete), au demarrage ET a la fermeture. Objectif : rien de sensible
lisible quand l'appli est fermee (la base, les photos et les tickets sont deja
dans le coffre chiffre dettes.db.enc).
  - main.py : fonction _purge_clear_artifacts() + appels (demarrage + fermeture)
Idempotent, verifie la syntaxe. A lancer dans le dossier du projet.
"""
import os, sys, py_compile

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def J(lines, eol): return eol.join(lines)

PURGE_FUNC = [
"def _purge_clear_artifacts():",
'    """Supprime les fichiers de base EN CLAIR qui pourraient trainer (chiffrement actif),',
"    pour que rien de sensible ne soit lisible quand l'appli est fermee.\"\"\"",
"    try:",
'        for _n in ("dettes_backup.db", "dettes.db.ancien", "dettes.db.ancien2",',
'                   "dettes.db.tmp", "dettes.db.old", "dettes.db.DESACTIVE",',
'                   "dettes.db.crash.old"):',
"            _p = os.path.join(DATA_DIR, _n)",
"            try:",
"                if os.path.exists(_p):",
"                    os.remove(_p)",
'                    print("[Gestion Perso] Fichier clair purge :", _n)',
"            except Exception:",
"                pass",
"        try:",
"            if os.path.exists(DB_PATH) and os.path.exists(ENC_PATH):",
"                if DB_PASSWORD is None and os.path.getmtime(DB_PATH) <= os.path.getmtime(ENC_PATH) + 2:",
"                    os.remove(DB_PATH)",
'                    print("[Gestion Perso] Base clair obsolete purgee.")',
"        except Exception:",
"            pass",
"    except Exception as _e:",
'        print("[Gestion Perso] Purge clair echouee :", _e)',
"",
"",
]

def repl(t, eol, old_lines, new_lines, label):
    old = J(old_lines, eol); new = J(new_lines, eol)
    n = t.count(old)
    if n != 1:
        print("  [X] %s : ancre trouvee %dx (attendu 1)" % (label, n)); sys.exit(1)
    return t.replace(old, new, 1)

def main():
    if not os.path.exists("main.py"):
        print("ERREUR : lance depuis le dossier du projet (main.py manquant)"); sys.exit(1)
    t = read("main.py"); eol = eol_of(t)

    if "_purge_clear_artifacts" in t:
        print("  [=] main.py : deja patche")
    else:
        # 1) definition de la fonction, juste avant _cloud_backup_safe
        t = repl(t, eol,
          ["def _cloud_backup_safe():"],
          PURGE_FUNC + ["def _cloud_backup_safe():"],
          "main.py definition _purge_clear_artifacts")
        # 2) appel a la fermeture (branche chiffree de _save_backup_on_exit)
        t = repl(t, eol,
          ["        _lock_db_on_exit(); _cloud_backup_safe(); return"],
          ["        _lock_db_on_exit(); _purge_clear_artifacts(); _cloud_backup_safe(); return"],
          "main.py appel fermeture")
        # 3) appel au demarrage (apres _backup_enc, si chiffrement actif)
        t = repl(t, eol,
          ["    _backup_enc()",
           '    print(f"[Gestion Perso] Demarrage {URL}")'],
          ["    _backup_enc()",
           "    if ENCRYPTION_ON:",
           "        _purge_clear_artifacts()",
           '    print(f"[Gestion Perso] Demarrage {URL}")'],
          "main.py appel demarrage")
        write("main.py", t)
        print("  [+] main.py : purge des fichiers clairs (demarrage + fermeture)")

    print("Verification syntaxe...")
    try:
        py_compile.compile("main.py", doraise=True); print("  [ok] main.py")
    except py_compile.PyCompileError as e:
        print("  [X] main.py : %s" % e); sys.exit(1)
    print("\nTermine (securite a la fermeture).")

if __name__ == "__main__":
    main()
