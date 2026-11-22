# -*- coding: utf-8 -*-
"""
patch_recap_associe_comptant.py  (v4.30)
Pour un ASSOCIE, une vente payee comptant fait quand meme partie de ce qu'il te doit :
sa dette doit TOUJOURS afficher le total (ex. 418.50), partout.
  1) db.py : ANNULE le changement de 4.29 -> la fiche associe reprend le total.
  2) web/index.html : le recap mensuel n'exclut plus les ventes comptant pour les
     associes (il continue de les exclure pour les clients normaux).
Idempotent, CRLF/LF preserves, verifie la syntaxe py. A lancer dans le dossier du projet.
"""
import os, sys, py_compile

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)

# --- db.py : revert 4.29 ---
DB_OLD = '        _excl_paye = " AND " + excl_paye_clause()  # [CAISSE PAYE] exclu aussi pour les associes (vente comptant = pas une dette)'
DB_NEW = '        _excl_paye = "" if _assoc else (" AND " + excl_paye_clause())'
# variante si 4.29 pas installee (deja a l'etat d'origine)
DB_ALREADY = '        _excl_paye = "" if _assoc else (" AND " + excl_paye_clause())'

# --- web/index.html : _skip garde les ventes comptant pour les associes ---
JS_OLD = "  function _skip(t){return (t.type==='debit'&&t.notes&&t.notes.indexOf('[CAISSE PAYE]')>=0);}"
JS_NEW = "  function _skip(t){if(!(t.type==='debit'&&t.notes&&t.notes.indexOf('[CAISSE PAYE]')>=0))return false;var _sc=(clientsCache||[]).find(function(x){return x.id==t.client_id;});return !(_sc&&_sc.associe);}"

def patch_db():
    t = read("db.py")
    if DB_OLD in t:
        t = t.replace(DB_OLD, DB_NEW, 1); write("db.py", t)
        print("  [+] db.py : 4.29 annulee (fiche associe = total)")
    elif DB_ALREADY in t:
        print("  [=] db.py : deja a l'etat d'origine (4.29 non installee)")
    else:
        print("  [X] db.py : ligne _excl_paye introuvable"); sys.exit(1)
    try:
        py_compile.compile("db.py", doraise=True); print("  [ok] db.py")
    except py_compile.PyCompileError as e:
        print("  [X] db.py : %s" % e); sys.exit(1)

def patch_front():
    t = read("web/index.html")
    if "x.id==t.client_id" in t and "_sc&&_sc.associe" in t:
        print("  [=] web/index.html : deja patche"); return
    n = t.count(JS_OLD)
    if n != 1:
        print("  [X] web/index.html : ancre _skip trouvee %dx (attendu 1)" % n); sys.exit(1)
    t = t.replace(JS_OLD, JS_NEW, 1); write("web/index.html", t)
    print("  [+] web/index.html : recap garde les ventes comptant pour les associes")

def main():
    for f in ("db.py", "web/index.html"):
        if not os.path.exists(f):
            print("ERREUR : lance depuis le dossier du projet (%s manquant)" % f); sys.exit(1)
    patch_db()
    patch_front()
    print("\nTermine (dette associe = total partout).")

if __name__ == "__main__":
    main()
