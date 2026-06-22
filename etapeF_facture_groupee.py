#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeF_facture_groupee.py  (CRLF-safe)
Facture groupee : une seule facture multi-lignes pour tout le panier de la caisse.
A lancer dans le dossier projet : python etapeF_facture_groupee.py
"""
import io

ap="api.py"
api=io.open(ap,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in api else "\n"

# 1) drapeau no_facture
old_if='        if created:'
new_if='        if created and not data.get("no_facture"):'
if old_if in api and 'not data.get("no_facture")' not in api:
    api=api.replace(old_if,new_if,1)
    print("API-1) drapeau no_facture ajoute")
elif 'not data.get("no_facture")' in api:
    print("API-1) deja present")
else:
    print("API-1) ATTENTION 'if created:' non trouve")

# 2) endpoint groupee + fonction (avant la route racine)
if "/api/factures/groupee" not in api:
    code = '''def _build_facture_groupee_html(transs, client, type_):
    from datetime import datetime
    date_str = datetime.now().strftime("%d/%m/%Y a %H:%M")
    is_vente = type_ == "vente"
    titre = "FACTURE DE VENTE" if is_vente else "BON DE REMBOURSEMENT"
    couleur = "#16a34a" if is_vente else "#c9a84c"
    client_nom = client.get("nom","-") if client else "-"
    client_tel = client.get("tel","") or ""
    tid0 = transs[0].get("id",0)
    prefix = "FAC" if is_vente else "BON"
    numero = f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{tid0:05d}"
    date_t = (transs[0].get("date","") or "")[:10].split("-")
    date_fmt = "/".join(reversed(date_t)) if len(date_t)==3 else ""
    rows_html = ""
    total = 0
    for t in transs:
        qty = t.get("quantite",1) or 1
        pu = t.get("prix_unitaire",0) or 0
        mb = t.get("montant_brut",0) or 0
        mode = t.get("mode_paiement","-")
        motif = t.get("motif","-")
        unite = t.get("unite","piece")
        ulabel = "g" if unite=="gramme" else ("L" if unite=="litre" else ("paquet(s)" if unite=="paquet" else "pcs"))
        total += mb
        rows_html += f"<tr><td><strong>{motif}</strong></td><td>{float(qty):.1f} {ulabel}</td><td>{float(pu):.2f} EUR</td><td>{mode}</td><td style='text-align:right;font-weight:600'>{float(mb):.2f} EUR</td></tr>"
    total = round(total,2)
    total_label = "Total du" if is_vente else "Montant rembourse"
    html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>{titre} {numero}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Arial,sans-serif;font-size:12px;color:#111;padding:32px;max-width:600px;margin:auto}}
.header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:28px;padding-bottom:16px;border-bottom:3px solid {couleur}}}
.app-name{{font-size:22px;font-weight:bold;color:{couleur}}}.app-sub{{font-size:11px;color:#666}}
.doc-type{{text-align:right}}.doc-type h1{{font-size:18px;color:{couleur}}}.numero{{font-size:13px;font-family:monospace;color:#333;margin-top:4px}}.date{{font-size:11px;color:#666}}
.section{{margin-bottom:20px}}.section-title{{font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#888;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee}}
.info-box{{background:#f9f9f9;border:1px solid #eee;border-radius:6px;padding:12px}}.info-box strong{{display:block;margin-bottom:4px;color:#333}}
table{{width:100%;border-collapse:collapse;margin-bottom:16px}}thead tr{{background:{couleur};color:white}}th{{padding:8px 10px;text-align:left;font-size:11px}}td{{padding:8px 10px;border-bottom:1px solid #f0f0f0}}
.total-section{{background:#f5f5f5;border:1px solid #ddd;border-radius:6px;padding:16px}}.total-row.main{{font-size:16px;font-weight:bold;color:{couleur};border-top:2px solid {couleur};margin-top:8px;padding-top:8px;display:flex;justify-content:space-between}}
.footer{{margin-top:32px;padding-top:16px;border-top:1px solid #eee;text-align:center;font-size:10px;color:#999}}</style></head><body>
<div class="header"><div><div class="app-name">Gestion Perso</div><div class="app-sub">Gestion de dettes &amp; creances</div></div>
<div class="doc-type"><h1>{titre}</h1><div class="numero">{numero}</div><div class="date">Emis le {date_str}</div></div></div>
<div class="section"><div class="section-title">Client</div><div class="info-box"><strong>{client_nom}</strong><span>{client_tel}</span></div></div>
<div class="section"><div class="section-title">Detail ({date_fmt})</div><table><thead><tr><th>Article</th><th>Qte</th><th>P.U.</th><th>Mode</th><th style="text-align:right">Montant</th></tr></thead><tbody>{rows_html}</tbody></table></div>
<div class="total-section"><div class="total-row main"><span>{total_label}</span><span>{total:.2f} EUR</span></div></div>
<div class="footer">Gestion Perso - Document genere le {date_str}</div></body></html>"""
    return html, numero

@app.route("/api/factures/groupee", methods=["POST"])
@require_auth
def factures_groupee():
    data = request.json or {}
    cid = data.get("client_id")
    tids = data.get("transaction_ids", [])
    type_ = data.get("type", "vente")
    if not cid or not tids:
        return err("Donnees manquantes")
    client = db.get_client(cid)
    with db.get_conn() as conn:
        qmarks = ",".join("?" for _ in tids)
        rows = conn.execute("SELECT * FROM transactions WHERE id IN (%s)" % qmarks, tuple(tids)).fetchall()
    transs = [dict(r) for r in rows]
    if not transs:
        return err("Transactions introuvables")
    total_net = round(sum((t.get("montant_net") or 0) for t in transs), 2)
    html_content, numero = _build_facture_groupee_html(transs, client, type_)
    fid, num = db.create_facture(transs[0]["id"], cid, type_, html_content, total_net)
    return ok({"facture_id": fid, "numero": num}), 201

'''
    code=code.replace("\n",eol)
    needle='@app.route("/", defaults'
    i=api.find(needle)
    if i!=-1:
        api=api[:i]+code+api[i:]
        print("API-2) endpoint factures/groupee + fonction ajoutes")
    else:
        print("API-2) ATTENTION route racine introuvable")
else:
    print("API-2) deja present")

io.open(ap,"w",encoding="utf-8",newline="").write(api)

# ---- WEB (remplacements 1 ligne) ----
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()

a_old="var ok=0,fail=0;"
a_new="var ok=0,fail=0;var venteTids=[];"
if a_old in html and "var venteTids=[]" not in html:
    html=html.replace(a_old,a_new,1); print("WEB-a) venteTids declare")
elif "var venteTids=[]" in html: print("WEB-a) deja present")
else: print("WEB-a) ATTENTION 'var ok=0,fail=0;' non trouve")

b_old="compte:_compteVente,date:_posDate};"
b_new="compte:_compteVente,date:_posDate,no_facture:true};"
if b_old in html:
    html=html.replace(b_old,b_new,1); print("WEB-b) no_facture ajoute")
elif "no_facture:true};" in html: print("WEB-b) deja present")
else: print("WEB-b) ATTENTION corps de vente non trouve")

c_old="try{var r=await api('/api/transactions',{method:'POST',body:body});if(r&&r.ok)ok++;else fail++;}catch(e){fail++;}"
c_new="try{var r=await api('/api/transactions',{method:'POST',body:body});if(r&&r.ok){ok++;if(r.data&&r.data.id)venteTids.push(r.data.id);}else fail++;}catch(e){fail++;}"
if c_old in html:
    html=html.replace(c_old,c_new,1); print("WEB-c) collecte des ids")
elif "venteTids.push(r.data.id)" in html: print("WEB-c) deja present")
else: print("WEB-c) ATTENTION ligne POST transaction non trouvee")

d_old="notify('Encaisse : '+msg.join(' + '));"
d_new="notify('Encaisse : '+msg.join(' + '));if(venteTids.length){api('/api/factures/groupee',{method:'POST',body:{client_id:cid,transaction_ids:venteTids,type:'vente'}}).catch(function(){});}"
if d_old in html and "api('/api/factures/groupee'" not in html:
    html=html.replace(d_old,d_new,1); print("WEB-d) facture groupee au succes")
elif "api('/api/factures/groupee'" in html: print("WEB-d) deja present")
else: print("WEB-d) ATTENTION ligne de succes non trouvee")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
