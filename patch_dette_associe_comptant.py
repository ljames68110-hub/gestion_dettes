# -*- coding: utf-8 -*-
"""
patch_dette_associe_comptant.py
Corrige l'ecart de dette pour les ASSOCIES : une vente payee comptant a la caisse
([CAISSE PAYE]) n'est pas une dette. Les clients normaux (et le recap mensuel, et
le tableau de bord) l'excluent deja ; les associes etaient les seuls a l'inclure,
d'ou une dette sur-evaluee sur leur fiche. On aligne les associes sur le reste.
db.py : get_stats_client -> exclure [CAISSE PAYE] aussi pour les associes.
Idempotent, verifie la syntaxe. A lancer dans le dossier du projet.
"""
import os, sys, py_compile

F = "db.py"
OLD = '        _excl_paye = "" if _assoc else (" AND " + excl_paye_clause())'
NEW = '        _excl_paye = " AND " + excl_paye_clause()  # [CAISSE PAYE] exclu aussi pour les associes (vente comptant = pas une dette)'

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)

def main():
    if not os.path.exists(F):
        print("ERREUR : lance depuis le dossier du projet (%s manquant)" % F); sys.exit(1)
    t = read(F)
    if "exclu aussi pour les associes" in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)
    n = t.count(OLD)
    if n != 1:
        print("  [X] ancre trouvee %dx (attendu 1) -- rien modifie" % n); sys.exit(1)
    t = t.replace(OLD, NEW, 1)
    write(F, t)
    print("  [+] db.py : dette associe exclut les ventes payees comptant")
    try:
        py_compile.compile(F, doraise=True); print("  [ok] db.py")
    except py_compile.PyCompileError as e:
        print("  [X] db.py : %s" % e); sys.exit(1)
    print("\nTermine (coherence dette associe).")

if __name__ == "__main__":
    main()
