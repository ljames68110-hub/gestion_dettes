#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_photo_materiel_back.py  (Point 4 - backend)
Ajoute une photo aux entrees materiel (stockee DANS la base -> chiffree a la
fermeture + envoyee sur le cloud, comme les photos clients).
  - db.py  : colonne photo sur entrees_materiel + add_entree/update_entree
  - api.py : transmet le champ photo en creation et modification
Idempotent, LF/CRLF preserves, verifie la syntaxe. A lancer dans le dossier du projet.
"""
import os, sys, py_compile

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def J(lines, eol): return eol.join(lines)

def repl(t, eol, old_lines, new_lines, label):
    old = J(old_lines, eol); new = J(new_lines, eol)
    n = t.count(old)
    if n != 1:
        print("  [X] %s : ancre trouvee %dx (attendu 1)" % (label, n)); sys.exit(1)
    return t.replace(old, new, 1)

def main():
    for f in ("db.py", "api.py"):
        if not os.path.exists(f):
            print("ERREUR : lance depuis le dossier du projet (%s manquant)" % f); sys.exit(1)

    # ---------- db.py ----------
    t = read("db.py"); eol = eol_of(t)
    if "entrees_materiel ADD COLUMN photo" in t:
        print("  [=] db.py : deja patche")
    else:
        # 1) migration colonne photo
        t = repl(t, eol,
          ['        if "stock_restant" not in ent_cols:',
           '            c.execute("ALTER TABLE entrees_materiel ADD COLUMN stock_restant REAL DEFAULT NULL")'],
          ['        if "stock_restant" not in ent_cols:',
           '            c.execute("ALTER TABLE entrees_materiel ADD COLUMN stock_restant REAL DEFAULT NULL")',
           '        if "photo" not in ent_cols:',
           '            c.execute("ALTER TABLE entrees_materiel ADD COLUMN photo TEXT DEFAULT \'\'")'],
          "db.py migration photo")
        # 2) add_entree
        t = repl(t, eol,
          ['def add_entree(description, quantite, prix_achat, date=None, notes="", unite="piece"):',
           '    with get_conn() as conn:',
           '        cur = conn.execute(',
           '            "INSERT INTO entrees_materiel (description,quantite,prix_achat,date,notes,unite,stock_restant) VALUES (?,?,?,?,?,?,?)",',
           '            (description, quantite, prix_achat, date or "", notes or "", unite, quantite)',
           '        )'],
          ['def add_entree(description, quantite, prix_achat, date=None, notes="", unite="piece", photo=""):',
           '    with get_conn() as conn:',
           '        cur = conn.execute(',
           '            "INSERT INTO entrees_materiel (description,quantite,prix_achat,date,notes,unite,stock_restant,photo) VALUES (?,?,?,?,?,?,?,?)",',
           '            (description, quantite, prix_achat, date or "", notes or "", unite, quantite, photo or "")',
           '        )'],
          "db.py add_entree")
        # 3) update_entree
        t = repl(t, eol,
          ['def update_entree(eid, description, quantite, prix_achat, date, notes="", unite="piece"):',
           '    with get_conn() as conn:',
           '        conn.execute(',
           '            "UPDATE entrees_materiel SET description=?,quantite=?,prix_achat=?,date=?,notes=?,unite=? WHERE id=?",',
           '            (description, quantite, prix_achat, date, notes or "", unite, eid)',
           '        )',
           '        conn.commit()'],
          ['def update_entree(eid, description, quantite, prix_achat, date, notes="", unite="piece", photo=None):',
           '    with get_conn() as conn:',
           '        if photo is None:',
           '            conn.execute(',
           '                "UPDATE entrees_materiel SET description=?,quantite=?,prix_achat=?,date=?,notes=?,unite=? WHERE id=?",',
           '                (description, quantite, prix_achat, date, notes or "", unite, eid)',
           '            )',
           '        else:',
           '            conn.execute(',
           '                "UPDATE entrees_materiel SET description=?,quantite=?,prix_achat=?,date=?,notes=?,unite=?,photo=? WHERE id=?",',
           '                (description, quantite, prix_achat, date, notes or "", unite, photo or "", eid)',
           '            )',
           '        conn.commit()'],
          "db.py update_entree")
        write("db.py", t)
        print("  [+] db.py : colonne photo + add/update_entree")

    # ---------- api.py ----------
    t = read("api.py"); eol = eol_of(t)
    if 'data.get("photo", "")' in t and "add_entree" in t and "entrees_create" in t and 'photo       = data.get("photo"' in t:
        print("  [=] api.py : deja patche")
    else:
        # entrees_create : ajoute photo
        t = repl(t, eol,
          ['        unite       = data.get("unite", "piece"),',
           '    )',
           '    return ok({"id": eid}), 201'],
          ['        unite       = data.get("unite", "piece"),',
           '        photo       = data.get("photo", ""),',
           '    )',
           '    return ok({"id": eid}), 201'],
          "api.py entrees_create")
        # entrees_update : ajoute photo
        t = repl(t, eol,
          ['    db.update_entree(eid, data.get("description",""), float(data.get("quantite",1)),',
           '                     float(data.get("prix_achat",0)), data.get("date",""), data.get("notes",""),',
           '                     data.get("unite","piece"))'],
          ['    db.update_entree(eid, data.get("description",""), float(data.get("quantite",1)),',
           '                     float(data.get("prix_achat",0)), data.get("date",""), data.get("notes",""),',
           '                     data.get("unite","piece"), photo=data.get("photo", None))'],
          "api.py entrees_update")
        write("api.py", t)
        print("  [+] api.py : champ photo en creation + modification")

    print("Verification syntaxe...")
    for f in ("db.py", "api.py"):
        try:
            py_compile.compile(f, doraise=True); print("  [ok] %s" % f)
        except py_compile.PyCompileError as e:
            print("  [X] %s : %s" % (f, e)); sys.exit(1)
    print("\nTermine (backend photo materiel).")

if __name__ == "__main__":
    main()
