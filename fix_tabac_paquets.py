#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_tabac_paquets.py
Affiche le compte tabac en PAQUETS (par type) + prix de revient,
au lieu du montant en euros.
  - API : stats-comptes calcule les paquets de tabac (debit - credit) par type
  - WEB : la fiche client affiche les paquets + valeur indicative
A lancer dans le dossier projet : python fix_tabac_paquets.py
"""
import io

# ════════════════════════════════════════════════════════════════
# API.PY : enrichir stats-comptes avec les paquets de tabac
# ════════════════════════════════════════════════════════════════
ap="api.py"
api=io.open(ap,encoding="utf-8").read()

if "result[\"tabac\"][\"paquets\"]" not in api:
    # On insere le calcul juste avant le 'return ok(result)' de client_stats_comptes
    # Reperage : la fonction se termine par "return ok(result)" apres la boucle des soldes.
    marker="    for c in result:\n        result[c][\"solde\"] = round(result[c][\"debit\"] - result[c][\"credit\"], 2)\n        result[c][\"debit\"] = round(result[c][\"debit\"], 2)\n        result[c][\"credit\"] = round(result[c][\"credit\"], 2)\n    return ok(result)"
    if marker in api:
        insert='''    for c in result:
        result[c]["solde"] = round(result[c]["debit"] - result[c]["credit"], 2)
        result[c]["debit"] = round(result[c]["debit"], 2)
        result[c]["credit"] = round(result[c]["credit"], 2)
    # --- Tabac en paquets (par type) ---
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
    return ok(result)'''
        api=api.replace(marker, insert, 1)
        io.open(ap,"w",encoding="utf-8").write(api)
        print("API) stats-comptes calcule les paquets de tabac")
    else:
        print("API) ATTENTION fin de client_stats_comptes non trouvee")
else:
    print("API) deja present")

# ════════════════════════════════════════════════════════════════
# WEB : affichage paquets sur la fiche client
# ════════════════════════════════════════════════════════════════
p="web/index.html"
html=io.open(p,encoding="utf-8").read()

old_t="🚬 Compte tabac</div><div style=\"font-size:28px;font-weight:700;color:'+(comptes.tabac.solde>0?'var(--green)':'var(--text3)')+'\">'+(comptes.tabac.solde>0?'+':'')+fmt(comptes.tabac.solde)+'</div></div>"
new_t=("🚬 Compte tabac</div>"
       "<div style=\"font-size:28px;font-weight:700;color:'+(((comptes.tabac.paquets||0)!=0)?'var(--gold2)':'var(--text3)')+'\">'+(comptes.tabac.paquets||0)+' paquet(s)</div>"
       "<div style=\"font-size:12px;color:var(--text3);margin-top:4px\">Prix de revient ~ '+fmt(comptes.tabac.valeur||0)+'</div>'"
       "+((comptes.tabac.details&&comptes.tabac.details.length)?('<div style=\"font-size:11px;color:var(--text3);margin-top:6px;text-align:left\">'+comptes.tabac.details.map(function(d){return d.nom+' : '+d.paquets+' ('+fmt(d.valeur)+')';}).join('<br>')+'</div>'):'')+'</div>")

if old_t in html:
    html=html.replace(old_t,new_t,1)
    io.open(p,"w",encoding="utf-8").write(html)
    print("WEB) fiche client : compte tabac affiche en paquets + prix de revient")
elif "comptes.tabac.paquets||0)+' paquet(s)'" in html or "paquet(s)</div>" in html:
    print("WEB) deja present")
else:
    print("WEB) ATTENTION affichage compte tabac non trouve a l'identique")

print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
