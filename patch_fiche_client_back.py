#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fiche_client_back.py
Ajoute batiment, etage et type (exterieur/cd) a la fiche client (base + API).
Idempotent, LF/CRLF preserves, verifie la syntaxe.
A lancer dans le dossier projet : python patch_fiche_client_back.py
"""
import os, sys, py_compile

def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def J(lines,eol): return eol.join(lines)

def repl(t, eol, old_lines, new_lines, label):
    old=J(old_lines,eol); new=J(new_lines,eol)
    n=t.count(old)
    if n!=1:
        print("  [X] %s : ancre trouvee %dx (attendu 1)" % (label,n)); sys.exit(1)
    return t.replace(old,new,1)

def main():
    for f in ("db.py","api.py"):
        if not os.path.exists(f):
            print("ERREUR : lance depuis le dossier du projet (%s manquant)"%f); sys.exit(1)

    # ---------- db.py ----------
    t=read("db.py"); eol=eol_of(t)
    if "type_client" in t:
        print("  [=] db.py : deja patche")
    else:
        # 1) colonnes
        t=repl(t,eol,
          ['        if "photo" not in cols:',
           '            conn.execute("ALTER TABLE clients ADD COLUMN photo TEXT DEFAULT \'\'")',
           '            conn.commit()'],
          ['        if "photo" not in cols:',
           '            conn.execute("ALTER TABLE clients ADD COLUMN photo TEXT DEFAULT \'\'")',
           '            conn.commit()',
           '        if "batiment" not in cols:',
           '            conn.execute("ALTER TABLE clients ADD COLUMN batiment TEXT DEFAULT \'\'")',
           '            conn.commit()',
           '        if "etage" not in cols:',
           '            conn.execute("ALTER TABLE clients ADD COLUMN etage TEXT DEFAULT \'\'")',
           '            conn.commit()',
           '        if "type_client" not in cols:',
           '            conn.execute("ALTER TABLE clients ADD COLUMN type_client TEXT DEFAULT \'exterieur\'")',
           '            conn.commit()'],
          "db.py colonnes clients")
        # 2) add_client signature
        t=repl(t,eol,
          ["def add_client(nom, email=None, tel=None, notes=None, associe=0, photo=None):"],
          ["def add_client(nom, email=None, tel=None, notes=None, associe=0, photo=None, batiment=None, etage=None, type_client=None):"],
          "db.py add_client sig")
        # 3) add_client INSERT
        t=repl(t,eol,
          ['            "INSERT INTO clients (nom,email,tel,notes,associe,photo) VALUES (?,?,?,?,?,?)",',
           '            (nom, email or "", tel or "", notes or "", int(associe or 0), photo or "")'],
          ['            "INSERT INTO clients (nom,email,tel,notes,associe,photo,batiment,etage,type_client) VALUES (?,?,?,?,?,?,?,?,?)",',
           '            (nom, email or "", tel or "", notes or "", int(associe or 0), photo or "", batiment or "", etage or "", type_client or "exterieur")'],
          "db.py add_client INSERT")
        # 4) update_client signature
        t=repl(t,eol,
          ["def update_client(client_id: int, nom=None, email=None, tel=None, notes=None, photo=None):"],
          ["def update_client(client_id: int, nom=None, email=None, tel=None, notes=None, photo=None, batiment=None, etage=None, type_client=None):"],
          "db.py update_client sig")
        # 5) update_client UPDATE
        t=repl(t,eol,
          ['            "UPDATE clients SET nom=?,email=?,tel=?,notes=?,photo=? WHERE id=?",',
           '            (nom or row["nom"], email or row["email"],',
           '             tel or row["tel"], notes or row["notes"],',
           '             (photo if photo is not None else row["photo"]), client_id)'],
          ['            "UPDATE clients SET nom=?,email=?,tel=?,notes=?,photo=?,batiment=?,etage=?,type_client=? WHERE id=?",',
           '            (nom or row["nom"], email or row["email"],',
           '             tel or row["tel"], notes or row["notes"],',
           '             (photo if photo is not None else row["photo"]),',
           '             (batiment if batiment is not None else row["batiment"]),',
           '             (etage if etage is not None else row["etage"]),',
           '             (type_client if type_client is not None else row["type_client"]), client_id)'],
          "db.py update_client UPDATE")
        # 6) get_clients SELECT
        t=repl(t,eol,
          ['            "SELECT id, nom, email, tel, notes, COALESCE(associe,0) as associe, COALESCE(photo,\'\') as photo, "'],
          ['            "SELECT id, nom, email, tel, notes, COALESCE(associe,0) as associe, COALESCE(photo,\'\') as photo, "',
           '            "COALESCE(batiment,\'\') as batiment, COALESCE(etage,\'\') as etage, COALESCE(type_client,\'exterieur\') as type_client, "'],
          "db.py get_clients SELECT")
        write("db.py",t)
        print("  [+] db.py : batiment/etage/type_client (colonnes + add/update/get)")

    # ---------- api.py ----------
    t=read("api.py"); eol=eol_of(t)
    if '"batiment"' in t and "/api/clients" in t:
        print("  [=] api.py : deja patche")
    else:
        t=repl(t,eol,
          ['        photo=data.get("photo", ""),',
           '    )'],
          ['        photo=data.get("photo", ""),',
           '        batiment=data.get("batiment", ""),',
           '        etage=data.get("etage", ""),',
           '        type_client=data.get("type_client", "exterieur"),',
           '    )'],
          "api.py clients_create")
        t=repl(t,eol,
          ['    if not db.update_client(cid, **{k: data.get(k) for k in ("nom","email","tel","notes","photo")}):'],
          ['    if not db.update_client(cid, **{k: data.get(k) for k in ("nom","email","tel","notes","photo","batiment","etage","type_client")}):'],
          "api.py clients_update")
        write("api.py",t)
        print("  [+] api.py : champs batiment/etage/type_client transmis")

    print("Verification syntaxe...")
    for f in ("db.py","api.py"):
        try:
            py_compile.compile(f,doraise=True); print("  [ok] %s"%f)
        except py_compile.PyCompileError as e:
            print("  [X] %s : %s"%(f,e)); sys.exit(1)
    print("\nTermine (backend fiche client).")

if __name__=="__main__":
    main()
