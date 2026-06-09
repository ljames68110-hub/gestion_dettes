#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyse_frais.py - LECTURE SEULE. N'ecrit RIEN dans la base.
  - Fait une copie de sauvegarde horodatee (securite)
  - Affiche, par client : dette actuelle + total 'frais dus' calcule
  - Affiche le detail des remboursements avec frais
But : verifier les chiffres AVANT toute migration.
Usage (dossier projet): python analyse_frais.py
"""
import os, sqlite3, shutil
from datetime import datetime

# Trouver la base : dossier projet (dev) ou AppData (exe)
candidates = [
    "dettes.db",
    os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "GestionPerso", "dettes.db"),
]
DB = None
for c in candidates:
    if os.path.exists(c):
        DB = c
        break

if not DB:
    print("ERREUR : dettes.db introuvable (ni dans le dossier, ni dans AppData).")
    raise SystemExit(1)

print("Base analysee : %s" % os.path.abspath(DB))

# Sauvegarde horodatee de securite (meme si on ne fait que lire)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
safe = DB + ".analyse_" + ts + ".bak"
shutil.copy2(DB, safe)
print("Copie de securite : %s" % safe)
print("")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

clients = conn.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()

print("="*70)
print("%-22s %14s %14s %12s" % ("CLIENT", "DETTE ACTU.", "FRAIS DUS", "NB REMB."))
print("="*70)

total_dette = 0.0
total_frais_dus = 0.0

for cl in clients:
    cid = cl["id"]
    # Dette actuelle = somme(debit net) - somme(credit net)
    deb = conn.execute("SELECT COALESCE(SUM(montant_net),0) FROM transactions WHERE client_id=? AND type='debit'", (cid,)).fetchone()[0]
    cre = conn.execute("SELECT COALESCE(SUM(montant_net),0) FROM transactions WHERE client_id=? AND type='credit'", (cid,)).fetchone()[0]
    dette = round(deb - cre, 2)
    # Frais dus = somme des frais sur les remboursements (credits) ou des frais ont ete appliques
    frais_dus = conn.execute("SELECT COALESCE(SUM(frais),0) FROM transactions WHERE client_id=? AND type='credit' AND frais>0", (cid,)).fetchone()[0]
    frais_dus = round(frais_dus, 2)
    nb_remb = conn.execute("SELECT COUNT(*) FROM transactions WHERE client_id=? AND type='credit' AND frais>0", (cid,)).fetchone()[0]

    total_dette += dette
    total_frais_dus += frais_dus

    if dette != 0 or frais_dus != 0:
        print("%-22s %12.2f E %12.2f E %12d" % (cl["nom"][:22], dette, frais_dus, nb_remb))

print("="*70)
print("%-22s %12.2f E %12.2f E" % ("TOTAL", round(total_dette,2), round(total_frais_dus,2)))
print("")

# Detail des remboursements avec frais (pour verification)
print("DETAIL DES REMBOURSEMENTS AVEC FRAIS (max 30) :")
print("-"*70)
rows = conn.execute("""
    SELECT t.date, c.nom, t.montant_brut, t.frais, t.montant_net, t.mode_paiement
    FROM transactions t LEFT JOIN clients c ON t.client_id=c.id
    WHERE t.type='credit' AND t.frais>0
    ORDER BY t.date DESC LIMIT 30
""").fetchall()
if not rows:
    print("Aucun remboursement avec frais dans la base.")
else:
    print("%-12s %-16s %8s %7s %8s %-10s" % ("DATE","CLIENT","BRUT","FRAIS","NET","MODE"))
    for r in rows:
        d = (r["date"] or "")[:10]
        print("%-12s %-16s %8.2f %7.2f %8.2f %-10s" % (
            d, (r["nom"] or "?")[:16], r["montant_brut"] or 0, r["frais"] or 0, r["montant_net"] or 0, r["mode_paiement"] or ""))

conn.close()
print("")
print("=== FIN ANALYSE (aucune modification effectuee) ===")
print("Verifie ces chiffres. Si 'FRAIS DUS' correspond a ce que tu attends,")
print("on pourra ajouter l'affichage de ce compteur sur la fiche client.")
