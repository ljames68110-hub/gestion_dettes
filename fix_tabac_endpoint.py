#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_tabac_endpoint.py  (CRLF-safe : insertions par .find et remplacements 1 ligne)
  - API : nouvel endpoint /api/clients/<id>/tabac-paquets
  - WEB : la fiche client recupere les paquets et les fusionne dans comptes.tabac
A lancer dans le dossier projet : python fix_tabac_endpoint.py
"""
import io

# ---------- API ----------
ap="api.py"
api=io.open(ap,encoding="utf-8",newline="").read()
if "/api/clients/<int:cid>/tabac-paquets" in api:
    print("API) endpoint deja present")
else:
    route=('@app.route("/api/clients/<int:cid>/tabac-paquets")\n'
'@require_auth\n'
'def client_tabac_paquets(cid):\n'
'    with db.get_conn() as conn:\n'
'        rows = conn.execute("""SELECT COALESCE(mode_paiement,\'Tabac\') as nom, type, COALESCE(SUM(quantite),0) as qte FROM transactions WHERE client_id=? AND COALESCE(compte,\'euro\')=\'tabac\' GROUP BY COALESCE(mode_paiement,\'Tabac\'), type""", (cid,)).fetchall()\n'
'        prix_map = {}\n'
'        try:\n'
'            for t in conn.execute("SELECT nom, prix FROM types_tabac").fetchall():\n'
'                prix_map[t["nom"]] = t["prix"]\n'
'        except Exception:\n'
'            pass\n'
'    detail = {}\n'
'    for r in rows:\n'
'        nom = r["nom"] or "Tabac"\n'
'        d = detail.setdefault(nom, {"nom": nom, "paquets": 0, "prix": prix_map.get(nom, 0)})\n'
'        if r["type"] == "debit":\n'
'            d["paquets"] += r["qte"]\n'
'        else:\n'
'            d["paquets"] -= r["qte"]\n'
'    total_p = 0; total_v = 0; details = []\n'
'    for nom, d in detail.items():\n'
'        d["paquets"] = round(d["paquets"], 2)\n'
'        d["valeur"] = round(d["paquets"] * (d["prix"] or 0), 2)\n'
'        if d["paquets"] != 0:\n'
'            total_p += d["paquets"]; total_v += d["valeur"]; details.append(d)\n'
'    return ok({"paquets": round(total_p,2), "valeur": round(total_v,2), "details": details})\n\n\n')
    eol="\r\n" if "\r\n" in api else "\n"
    route=route.replace("\n",eol)
    needle='@app.route("/", defaults'
    i=api.find(needle)
    if i!=-1:
        api=api[:i]+route+api[i:]
        io.open(ap,"w",encoding="utf-8",newline="").write(api)
        print("API) endpoint tabac-paquets ajoute")
    else:
        print("API) ATTENTION route racine introuvable")

# ---------- WEB (remplacements 1 ligne) ----------
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()

old1="api('/api/clients/'+cid)]);var sr=_r277[0];var tr2=_r277[1];var sc=_r277[2];var cr=_r277[3];"
new1="api('/api/clients/'+cid),api('/api/clients/'+cid+'/tabac-paquets')]);var sr=_r277[0];var tr2=_r277[1];var sc=_r277[2];var cr=_r277[3];var tp=_r277[4];"
if old1 in html:
    html=html.replace(old1,new1,1)
    print("WEB-1) fiche client recupere les paquets tabac")
elif "var tp=_r277[4];" in html:
    print("WEB-1) deja present")
else:
    print("WEB-1) ATTENTION ligne Promise.all non trouvee")

old2="var comptes = sc && sc.ok ? sc.data : {euro:{solde:0},cantine:{solde:0},tabac:{solde:0}};"
new2=old2+"if(tp&&tp.ok&&tp.data){comptes.tabac.paquets=tp.data.paquets;comptes.tabac.valeur=tp.data.valeur;comptes.tabac.details=tp.data.details;}"
if old2 in html and "comptes.tabac.paquets=tp.data.paquets" not in html:
    html=html.replace(old2,new2,1)
    print("WEB-2) paquets fusionnes dans comptes.tabac")
elif "comptes.tabac.paquets=tp.data.paquets" in html:
    print("WEB-2) deja present")
else:
    print("WEB-2) ATTENTION ligne comptes non trouvee")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("=== TERMINE ===")
