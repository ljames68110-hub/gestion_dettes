#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeN_dashboard_mois.py  (CRLF-safe, web/index.html)
Tableau de bord : ventes / encaisse / solde du MOIS EN COURS (au lieu du cumul depuis le debut).
A lancer dans le dossier projet : python etapeN_dashboard_mois.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in html else "\n"

# 1) Valeurs : mois en cours au lieu du cumul
old_lines=[
"  document.getElementById('s-credit').textContent=fmt(d.total_credit);",
"  const se=document.getElementById('s-solde');",
"  se.textContent=fmt(d.solde_net);se.style.color=d.solde_net>=0?'var(--green)':'var(--red)';",
"  document.getElementById('s-debit').textContent=fmt(d.total_debit);",
"  document.getElementById('s-clients').textContent=d.nb_clients;",
]
old_block=eol.join(old_lines)
new_lines=[
"  document.getElementById('s-clients').textContent=d.nb_clients;",
"  var _ym=new Date().toISOString().slice(0,7);",
"  var _tdash=await api('/api/transactions?limit=5000');",
"  var _mDeb=0,_mCre=0;",
"  if(_tdash&&_tdash.ok){_tdash.data.forEach(function(t){if((t.date||'').slice(0,7)!==_ym)return;if((t.compte||'euro')==='tabac')return;var n=parseFloat(t.montant_net||0);if(t.type==='debit')_mDeb+=n;else _mCre+=n;});}",
"  document.getElementById('s-debit').textContent=fmt(_mDeb);",
"  document.getElementById('s-credit').textContent=fmt(_mCre);",
"  var se=document.getElementById('s-solde');var _mNet=_mDeb-_mCre;se.textContent=fmt(_mNet);se.style.color=_mNet>=0?'var(--green)':'var(--red)';",
]
new_block=eol.join(new_lines)
if "_tdash=await api('/api/transactions?limit=5000')" in html:
    print("1) deja present")
elif old_block in html:
    html=html.replace(old_block,new_block,1)
    print("1) valeurs du tableau de bord = mois en cours")
else:
    print("1) ATTENTION bloc de valeurs loadDashboard non trouve a l'identique")

# 2) Libelles des cartes
labels=[
('<div class="stat-label">Total encaissé</div>','<div class="stat-label">Encaissé ce mois</div>'),
('<div class="stat-sub">Crédits nets</div>','<div class="stat-sub">Crédits du mois</div>'),
('<div class="stat-label">Solde net</div>','<div class="stat-label">Solde du mois</div>'),
('<div class="stat-sub">Débit − Crédit</div>','<div class="stat-sub">Ce mois (D − C)</div>'),
('<div class="stat-label">Total débits</div>','<div class="stat-label">Ventes ce mois</div>'),
('<div class="stat-sub">Ventes totales</div>','<div class="stat-sub">Débits du mois</div>'),
]
n=0
for o,nw in labels:
    if o in html:
        html=html.replace(o,nw,1); n+=1
print("2) %d/6 libelles mis a jour" % n)

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
