#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeP_fusion_associes.py
Transforme les anciennes fiches (avec historique) en associes, supprime les doublons vides.
  Mahmoud : 7 devient associe, 27 supprime
  Imed    : 10 devient associe, 28 supprime
  SidAli  : 9 devient associe, 29 supprime
Sauvegarde dettes.db.avant_fusion_associes.bak deja faite.
A lancer dans le dossier projet : python etapeP_fusion_associes.py
"""
import sqlite3, os
DB="dettes.db"
if not os.path.exists(DB):
    print("ATTENTION : dettes.db introuvable ici"); raise SystemExit

c=sqlite3.connect(DB)

print("=== AVANT ===")
for r in c.execute("SELECT cl.id, cl.nom, cl.associe, (SELECT COUNT(*) FROM transactions t WHERE t.client_id=cl.id) FROM clients cl WHERE cl.id IN (7,10,9,27,28,29) ORDER BY cl.nom, cl.associe").fetchall():
    print(r)

pairs=[(7,27,'Mahmoud'),(10,28,'Imed'),(9,29,'SidAli')]
for old_id,new_id,nom in pairs:
    # l'ancienne fiche (historique) devient associe
    c.execute("UPDATE clients SET associe=1 WHERE id=?", (old_id,))
    # supprimer le doublon vide SEULEMENT s'il n'a aucune transaction
    row=c.execute("SELECT COUNT(*) FROM clients WHERE id=?", (new_id,)).fetchone()
    if row and row[0]:
        nb=c.execute("SELECT COUNT(*) FROM transactions WHERE client_id=?", (new_id,)).fetchone()[0]
        if nb==0:
            c.execute("DELETE FROM clients WHERE id=?", (new_id,))
            print("OK %-8s : fiche %d -> associe, doublon %d supprime" % (nom, old_id, new_id))
        else:
            print("ATTENTION %-8s : le doublon %d a %d transaction(s), NON supprime" % (nom, new_id, nb))
    else:
        print("OK %-8s : fiche %d -> associe (pas de doublon %d a supprimer)" % (nom, old_id, new_id))

c.commit()

print("=== APRES ===")
for r in c.execute("SELECT cl.id, cl.nom, cl.associe, (SELECT COUNT(*) FROM transactions t WHERE t.client_id=cl.id) FROM clients cl WHERE cl.nom IN ('Mahmoud','Imed','SidAli') ORDER BY cl.nom").fetchall():
    print(r)
c.close()
print("=== TERMINE ===")
