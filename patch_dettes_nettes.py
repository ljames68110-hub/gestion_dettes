# -*- coding: utf-8 -*-
"""
patch_dettes_nettes.py  (v4.32)
Corrige l'affichage des "dettes ouvertes" : un credit (ex. un achat au client
enregistre AVANT la vente) n'etait applique qu'aux debits deja presents, donc il
etait perdu et la dette restait affichee alors que le solde net etait a zero.
Desormais, les credits non appliques sont gardes et deverses sur les debits
restants du MEME compte a la fin -> la somme des dettes affichees = le solde net.
Resultat : client a zero => aucune dette affichee.
api.py seulement. Idempotent, LF/CRLF preserves, verifie la syntaxe.
A lancer dans le dossier du projet : python patch_dettes_nettes.py
"""
import os, sys, py_compile

F = "api.py"

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def J(lines, eol): return eol.join(lines)

A1_OLD = [
"        compte_de = {}   # {debit_id: compte} -- cloisonnement FIFO par compte",
]
A1_NEW = [
"        compte_de = {}   # {debit_id: compte} -- cloisonnement FIFO par compte",
"        leftover = {}    # credits non encore appliques, par compte",
]

A2_OLD = [
"                        if rem.get(did, 0) > 0:",
"                            take = min(rem[did], amt); rem[did] -= take; amt -= take",
"        result = []",
]
A2_NEW = [
"                        if rem.get(did, 0) > 0:",
"                            take = min(rem[did], amt); rem[did] -= take; amt -= take",
"                if amt > 0:",
"                    leftover[rcompte] = leftover.get(rcompte, 0) + amt",
"        # credits non appliques (ex. achat enregistre avant la vente) -> debits restants du meme compte",
"        for _did in reversed(opened):",
"            _c = compte_de.get(_did, 'euro')",
"            if leftover.get(_c, 0) > 0 and rem.get(_did, 0) > 0:",
"                _t = min(rem[_did], leftover[_c]); rem[_did] -= _t; leftover[_c] -= _t",
"        result = []",
]

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
    if "leftover = {}" in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)
    t = repl(t, eol, A1_OLD, A1_NEW, "init leftover")
    print("  [+] init leftover")
    t = repl(t, eol, A2_OLD, A2_NEW, "deversement credits restants")
    print("  [+] deversement des credits restants")
    write(F, t)
    try:
        py_compile.compile(F, doraise=True); print("  [ok] api.py")
    except py_compile.PyCompileError as e:
        print("  [X] api.py : %s" % e); sys.exit(1)
    print("\nTermine (dettes ouvertes = solde net).")

if __name__ == "__main__":
    main()
