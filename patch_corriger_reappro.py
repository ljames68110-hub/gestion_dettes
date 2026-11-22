# -*- coding: utf-8 -*-
"""
patch_corriger_reappro.py  (v4.31)
Permet de CORRIGER un reapprovisionnement sans casser le stock.
Un reappro cree un lot (entree, notes="Reappro") ET ajoute au stock du catalogue.
Jusqu'ici, editer ou supprimer ce lot ne touchait pas le stock du catalogue.
Desormais :
  - editer la quantite d'un reappro repercute la difference sur le stock du catalogue ;
  - supprimer un reappro retire sa quantite du stock.
L'article est retrouve par son nom (comme le fait le reappro lui-meme).
api.py seulement. Idempotent, LF/CRLF preserves, verifie la syntaxe.
A lancer dans le dossier du projet : python patch_corriger_reappro.py
"""
import os, sys, py_compile

F = "api.py"

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def J(lines, eol): return eol.join(lines)

HELPER = [
"def _reappro_stock_sync(eid, new_qte=None, deleting=False):",
'    """Si l\'entree est un reappro, repercute le changement de quantite sur le stock catalogue."""',
"    try:",
"        with db.get_conn() as conn:",
"            row = conn.execute(\"SELECT description, quantite, COALESCE(notes,'') AS notes FROM entrees_materiel WHERE id=?\", (eid,)).fetchone()",
"        if not row:",
"            return",
'        if "Reappro" not in (row["notes"] or ""):',
"            return",
"        old_qte = float(row[\"quantite\"] or 0)",
"        nom = (row[\"description\"] or \"\").strip().lower()",
"        art = None",
"        for a in db.get_catalogue():",
"            if (a.get(\"nom\", \"\") or \"\").strip().lower() == nom:",
"                art = a; break",
"        if not art:",
"            return",
"        delta = (-old_qte) if deleting else (float(new_qte or 0) - old_qte)",
"        if abs(delta) > 1e-9:",
"            db.adjust_stock_catalogue(art[\"id\"], delta)",
"    except Exception:",
"        pass",
"",
"",
]

UPD_OLD = [
'    data = request.json or {}',
'    db.update_entree(eid, data.get("description",""), float(data.get("quantite",1)),',
]
UPD_NEW = [
'    data = request.json or {}',
'    _reappro_stock_sync(eid, new_qte=float(data.get("quantite",1) or 0))',
'    db.update_entree(eid, data.get("description",""), float(data.get("quantite",1)),',
]

DEL_OLD = [
'def entrees_delete(eid):',
'    db.delete_entree(eid)',
]
DEL_NEW = [
'def entrees_delete(eid):',
'    _reappro_stock_sync(eid, deleting=True)',
'    db.delete_entree(eid)',
]

ANCHOR_HELPER = '@app.route("/api/entrees/<int:eid>", methods=["PUT"])'

def repl(t, eol, old_lines, new_lines, label):
    old = J(old_lines, eol); new = J(new_lines, eol)
    n = t.count(old)
    if n != 1:
        print("  [X] %s : ancre trouvee %dx (attendu 1)" % (label, n)); sys.exit(1)
    return t.replace(old, new, 1)

def main():
    if not os.path.exists(F):
        print("ERREUR : lance depuis le dossier du projet (%s manquant)" % F); sys.exit(1)
    t = read(F); eol = eol_of(t)
    if "_reappro_stock_sync" in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)

    # 1) helper juste avant la route PUT entrees
    if t.count(ANCHOR_HELPER) != 1:
        print("  [X] ancre route PUT entrees %dx" % t.count(ANCHOR_HELPER)); sys.exit(1)
    t = t.replace(ANCHOR_HELPER, J(HELPER, eol) + ANCHOR_HELPER, 1)
    print("  [+] helper _reappro_stock_sync")

    # 2) edition d'une entree -> sync stock
    t = repl(t, eol, UPD_OLD, UPD_NEW, "entrees_update")
    print("  [+] edition reappro -> stock ajuste")

    # 3) suppression d'une entree -> sync stock
    t = repl(t, eol, DEL_OLD, DEL_NEW, "entrees_delete")
    print("  [+] suppression reappro -> stock ajuste")

    write(F, t)
    try:
        py_compile.compile(F, doraise=True); print("  [ok] api.py")
    except py_compile.PyCompileError as e:
        print("  [X] api.py : %s" % e); sys.exit(1)
    print("\nTermine (correction des reappros avec maj du stock).")

if __name__ == "__main__":
    main()
