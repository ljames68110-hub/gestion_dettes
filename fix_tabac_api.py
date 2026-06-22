#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_tabac_api.py
Insere (cote serveur) le calcul des PAQUETS de tabac dans stats-comptes,
avec un point d'ancrage robuste (avant la route /stats).
A lancer dans le dossier projet : python fix_tabac_api.py
"""
import io
ap="api.py"
api=io.open(ap,encoding="utf-8").read()

if 'result["tabac"]["paquets"]' in api:
    print("API) deja present")
else:
    anchor='    return ok(result)\n@app.route("/api/clients/<int:cid>/stats")'
    if anchor in api:
        block='''    # --- Tabac en paquets (par type) ---
    try:
        with db.get_conn() as conn:
            tab_rows = conn.execute("""
                SELECT COALESCE(mode_paiement,'Tabac') as nom, type, COALESCE(SUM(quantite),0) as qte
                FROM transactions
                WHERE client_id=? AND COALESCE(compte,'euro')='tabac'
                GROUP BY COALESCE(mode_paiement,'Tabac'), type
            """, (cid,)).fetchall()
            prix_map = {}
            try:
                for t in conn.execute("SELECT nom, prix FROM types_tabac").fetchall():
                    prix_map[t["nom"]] = t["prix"]
            except Exception:
                pass
        detail = {}
        for r in tab_rows:
            nom = r["nom"] or "Tabac"
            d = detail.setdefault(nom, {"nom": nom, "paquets": 0, "prix": prix_map.get(nom, 0)})
            if r["type"] == "debit":
                d["paquets"] += r["qte"]
            else:
                d["paquets"] -= r["qte"]
        total_p = 0; total_v = 0; details = []
        for nom, d in detail.items():
            d["paquets"] = round(d["paquets"], 2)
            d["valeur"] = round(d["paquets"] * (d["prix"] or 0), 2)
            if d["paquets"] != 0:
                total_p += d["paquets"]; total_v += d["valeur"]; details.append(d)
        result["tabac"]["paquets"] = round(total_p, 2)
        result["tabac"]["valeur"] = round(total_v, 2)
        result["tabac"]["details"] = details
    except Exception:
        result["tabac"]["paquets"] = 0
        result["tabac"]["valeur"] = 0
        result["tabac"]["details"] = []
    return ok(result)
@app.route("/api/clients/<int:cid>/stats")'''
        api=api.replace(anchor, block, 1)
        io.open(ap,"w",encoding="utf-8").write(api)
        print("API) calcul des paquets de tabac insere (ancre robuste)")
    else:
        print("API) ATTENTION ancre introuvable - colle-moi sed -n '204,206p' api.py")

