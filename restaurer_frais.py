#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
restaurer_frais.py
Annule l'operation "Frais paye" : remet frais / montant_net / notes d'origine
sur toutes les transactions marquees [FRAIS PAYE], en lisant les vraies valeurs
depuis la sauvegarde dettes.db.avant_fusion_associes.bak, et repasse les lignes
frais_dus en 'en_attente'. Ne touche a RIEN d'autre (la fusion associes reste).
A lancer dans le dossier projet : python restaurer_frais.py
"""
import sqlite3, os
LIVE = "dettes.db"
BAK  = "dettes.db.avant_fusion_associes.bak"
if not os.path.exists(LIVE):
    print("ATTENTION : dettes.db introuvable ici"); raise SystemExit
if not os.path.exists(BAK):
    print("ATTENTION : sauvegarde introuvable :", BAK); raise SystemExit

live = sqlite3.connect(LIVE); live.row_factory = sqlite3.Row
bak  = sqlite3.connect(BAK);  bak.row_factory  = sqlite3.Row

print("=== AVANT (transactions marquees [FRAIS PAYE]) ===")
affected = live.execute(
    "SELECT id, client_id, montant_brut, frais, montant_net, notes "
    "FROM transactions WHERE notes LIKE '%[FRAIS PAYE]%'").fetchall()
if not affected:
    print("(aucune transaction marquee [FRAIS PAYE] - rien a restaurer)")
for r in affected:
    print(dict(r))

restored = 0
for r in affected:
    tid = r["id"]
    orig = bak.execute(
        "SELECT frais, montant_net, COALESCE(notes,'') AS notes "
        "FROM transactions WHERE id=?", (tid,)).fetchone()
    if not orig:
        print("ATTENTION : tx", tid, "absente de la sauvegarde, NON restauree")
        continue
    live.execute("UPDATE transactions SET frais=?, montant_net=?, notes=? WHERE id=?",
                 (orig["frais"], orig["montant_net"], orig["notes"], tid))
    live.execute("UPDATE frais_dus SET statut='en_attente' WHERE transaction_id=?", (tid,))
    print("restaure tx %d -> frais %s, net %s" % (tid, orig["frais"], orig["montant_net"]))
    restored += 1

live.commit()
print("=== APRES (Imed : tx 24/25/27) ===")
for r in live.execute("SELECT id, montant_brut, frais, montant_net, notes "
                       "FROM transactions WHERE id IN (24,25,27)").fetchall():
    print(dict(r))
print("Transactions restaurees :", restored)
live.close(); bak.close()
print("=== TERMINE ===")
