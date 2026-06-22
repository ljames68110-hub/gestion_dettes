#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
corriger_frais_imed.py
Frais PCS d'Imed deja payes : on les retire de SA dette.
Sur les 3 remboursements PCS (id 24/25/27) : frais=0, net=brut, note [FRAIS PAYE],
et frais_dus -> 'paye'. Le solde doit passer de 225,95 a 61,45 EUR.
Sauvegarde auto dans dettes.db.avant_frais_imed.bak. Ne touche a rien d'autre.
A lancer dans le dossier projet : python corriger_frais_imed.py
"""
import sqlite3, os, shutil
DB = "dettes.db"
if not os.path.exists(DB):
    print("ATTENTION : dettes.db introuvable ici"); raise SystemExit
shutil.copy(DB, "dettes.db.avant_frais_imed.bak")
print("Sauvegarde : dettes.db.avant_frais_imed.bak")

c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
def solde_imed():
    return c.execute(
        "SELECT COALESCE(SUM(CASE WHEN type='debit' THEN montant_net ELSE 0 END),0)"
        "-COALESCE(SUM(CASE WHEN type='credit' THEN montant_net ELSE 0 END),0) "
        "FROM transactions WHERE client_id=10").fetchone()[0]

print("Solde Imed AVANT :", round(solde_imed() or 0, 2), "EUR")
for tid in (24, 25, 27):
    r = c.execute("SELECT montant_brut, frais, COALESCE(notes,'') AS notes "
                  "FROM transactions WHERE id=?", (tid,)).fetchone()
    if not r:
        print("ATTENTION : tx", tid, "absente"); continue
    brut = r["montant_brut"]; notes = r["notes"]
    if "[FRAIS PAYE]" not in notes:
        notes = (notes + " [FRAIS PAYE]").strip()
    c.execute("UPDATE transactions SET frais=0, montant_net=?, notes=? WHERE id=?",
              (brut, notes, tid))
    c.execute("UPDATE frais_dus SET statut='paye' WHERE transaction_id=?", (tid,))
    print("tx %d : frais %s -> 0, net -> %s" % (tid, r["frais"], brut))
c.commit()
print("Solde Imed APRES :", round(solde_imed() or 0, 2), "EUR")
c.close()
print("=== TERMINE ===")
