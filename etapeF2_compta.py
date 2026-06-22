#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeF2_compta.py  (CRLF-safe)
Page Compta dediee : periode (du/au) + filtre client, cartes ventes/encaisse/benefice/dette,
tableau des operations, export PDF (via la fenetre d'impression existante).
A lancer dans le dossier projet : python etapeF2_compta.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in html else "\n"
orig=len(html)

# 1) Nav item Compta (apres Recap mensuel)
nav_anchor='<div class="nav-item" onclick="goPage(\'recap\',this)"><span class="nav-icon">📊</span> Récap mensuel</div>'
nav_new=nav_anchor+eol+'    <div class="nav-item" onclick="goPage(\'compta\',this)"><span class="nav-icon">📒</span> Compta</div>'
if "goPage('compta'" not in html and nav_anchor in html:
    html=html.replace(nav_anchor,nav_new,1)
    print("1) nav-item Compta ajoute")
elif "goPage('compta'" in html:
    print("1) deja present")
else:
    print("1) ATTENTION nav recap non trouve")

# 2) goPage case
go_anchor="  if(name==='factures'){initFactures();}"
go_new=go_anchor+eol+"  if(name==='compta'){initCompta();}"
if "if(name==='compta')" not in html and go_anchor in html:
    html=html.replace(go_anchor,go_new,1)
    print("2) goPage: cas compta ajoute")
elif "if(name==='compta')" in html:
    print("2) deja present")
else:
    print("2) ATTENTION cas factures non trouve")

# 3) TITLES
if "compta:'Comptabilite'" not in html and "recap:'Recap mensuel'" in html:
    html=html.replace("recap:'Recap mensuel'","recap:'Recap mensuel',compta:'Comptabilite'",1)
    print("3) TITLES: compta ajoute")
else:
    print("3) deja present ou TITLES recap non trouve")

# 4) Page pg-compta (avant pg-rappels)
page_anchor='<div class="page" id="pg-rappels">'
if 'id="pg-compta"' not in html and page_anchor in html:
    PAGE=('<div class="page" id="pg-compta">\n'
'        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:16px;background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:16px">\n'
'          <span style="font-size:13px;color:var(--text3)">Du</span>\n'
'          <input type="date" id="comptaDu" onchange="computeCompta()" style="padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text)">\n'
'          <span style="font-size:13px;color:var(--text3)">au</span>\n'
'          <input type="date" id="comptaAu" onchange="computeCompta()" style="padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text)">\n'
'          <select id="comptaClient" onchange="computeCompta()" style="padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);min-width:160px"><option value="">Tous les clients</option></select>\n'
'          <button class="btn primary" onclick="exportComptaPDF()" style="margin-left:auto">🧾 Export PDF</button>\n'
'        </div>\n'
'        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:16px">\n'
'          <div class="stat-card green"><div class="stat-label">Ventes (periode)</div><div class="stat-value" id="comptaVentes">—</div></div>\n'
'          <div class="stat-card blue"><div class="stat-label">Encaisse (periode)</div><div class="stat-value" id="comptaEncaisse">—</div></div>\n'
'          <div class="stat-card gold"><div class="stat-label">Benefice estime</div><div class="stat-value" id="comptaBenef">—</div></div>\n'
'          <div class="stat-card red"><div class="stat-label">Dette totale</div><div class="stat-value" id="comptaDette">—</div></div>\n'
'        </div>\n'
'        <div class="table-wrap">\n'
'          <div class="table-header"><span>Operations de la periode</span></div>\n'
'          <table><thead><tr><th>Date</th><th>Client</th><th>Type</th><th>Motif</th><th>Mode</th><th style="text-align:right">Montant</th></tr></thead><tbody id="comptaTbody"></tbody></table>\n'
'        </div>\n'
'      </div>\n'
'      ')
    PAGE=PAGE.replace("\n",eol)
    html=html.replace(page_anchor,PAGE+page_anchor,1)
    print("4) page pg-compta ajoutee")
elif 'id="pg-compta"' in html:
    print("4) deja presente")
else:
    print("4) ATTENTION pg-rappels non trouve")

# 5) JS Compta
if "function initCompta" not in html:
    JS=r"""
<script>
// ===== COMPTA =====
var comptaData=null;
function initCompta(){
  var now=new Date();
  var first=new Date(now.getFullYear(),now.getMonth(),1);
  var du=document.getElementById('comptaDu');var au=document.getElementById('comptaAu');
  if(du&&!du.value)du.value=first.toISOString().slice(0,10);
  if(au&&!au.value)au.value=now.toISOString().slice(0,10);
  var sel=document.getElementById('comptaClient');
  if(sel){var prev=sel.value;sel.innerHTML='<option value="">Tous les clients</option>';(clientsCache||[]).filter(function(c){return !c.associe;}).forEach(function(c){var o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);});if(prev)sel.value=prev;}
  computeCompta();
}
async function computeCompta(){
  var du=(document.getElementById('comptaDu')||{}).value||'';
  var au=(document.getElementById('comptaAu')||{}).value||'';
  var cidf=(document.getElementById('comptaClient')||{}).value||'';
  var res=await api('/api/transactions?limit=5000');
  var trans=(res&&res.ok)?res.data:[];
  var cmap={};(clientsCache||[]).forEach(function(c){cmap[c.id]=c.nom;});
  var costmap={};(catalogueCache||[]).forEach(function(a){costmap[a.nom]=parseFloat(a.prix_achat||0);});
  var ventes=0,encaisse=0,benef=0,detteTotale=0;var rows=[];
  trans.forEach(function(t){
    var compte=t.compte||'euro';
    if(!cidf || String(t.client_id)===String(cidf)){
      if(compte!=='tabac'){
        if(t.type==='debit')detteTotale+=parseFloat(t.montant_net||0);
        else detteTotale-=parseFloat(t.montant_net||0);
      }
    }
    var d=(t.date||'').slice(0,10);
    if(du&&d<du)return;if(au&&d>au)return;
    if(cidf&&String(t.client_id)!==String(cidf))return;
    if(compte==='tabac')return;
    var net=parseFloat(t.montant_net||0);
    if(t.type==='debit'){ventes+=net;var cost=(costmap[t.motif]||0)*parseFloat(t.quantite||1);benef+=(net-cost);}
    else{encaisse+=net;}
    rows.push(t);
  });
  document.getElementById('comptaVentes').textContent=fmt(ventes);
  document.getElementById('comptaEncaisse').textContent=fmt(encaisse);
  document.getElementById('comptaBenef').textContent=fmt(benef);
  document.getElementById('comptaDette').textContent=fmt(detteTotale);
  var tb=document.getElementById('comptaTbody');tb.innerHTML='';
  if(!rows.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:20px">Aucune operation</td></tr>';}
  else rows.slice().sort(function(a,b){return (b.date||'').localeCompare(a.date||'');}).forEach(function(t){
    var tr=document.createElement('tr');
    tr.innerHTML='<td>'+((t.date||'').slice(0,10))+'</td><td>'+(cmap[t.client_id]||'?')+'</td><td>'+(t.type==='debit'?'Vente':'Encaissement')+'</td><td>'+(t.motif||'')+'</td><td>'+(t.mode_paiement||'')+'</td><td style="text-align:right;font-weight:600;color:'+(t.type==='debit'?'var(--green)':'var(--red)')+'">'+(t.type==='debit'?'+':'-')+fmt(parseFloat(t.montant_net||0))+'</td>';
    tb.appendChild(tr);
  });
  comptaData={ventes:ventes,encaisse:encaisse,benef:benef,detteTotale:detteTotale,rows:rows,du:du,au:au,client:(cidf?(cmap[cidf]||'?'):'Tous les clients')};
}
function exportComptaPDF(){
  if(!comptaData){computeCompta();return;}
  var d=comptaData;
  var rowsHtml=d.rows.slice().sort(function(a,b){return (a.date||'').localeCompare(b.date||'');}).map(function(t){
    return '<tr><td>'+((t.date||'').slice(0,10))+'</td><td>'+(t.type==='debit'?'Vente':'Encaissement')+'</td><td>'+(t.motif||'')+'</td><td>'+(t.mode_paiement||'')+'</td><td style="text-align:right">'+(t.type==='debit'?'+':'-')+parseFloat(t.montant_net||0).toFixed(2)+' EUR</td></tr>';
  }).join('');
  var html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Compta</title><style>body{font-family:Arial,sans-serif;font-size:12px;color:#111;padding:24px}h1{color:#c9a84c;font-size:20px;margin-bottom:6px}table{width:100%;border-collapse:collapse;margin-top:12px}th{background:#c9a84c;color:#fff;padding:6px 8px;text-align:left;font-size:11px}td{padding:6px 8px;border-bottom:1px solid #eee}.cards{display:flex;gap:12px;margin:14px 0}.card{flex:1;border:1px solid #ddd;border-radius:6px;padding:10px}.card .l{font-size:10px;color:#888;text-transform:uppercase}.card .v{font-size:17px;font-weight:bold}</style></head><body>'
    +'<h1>Comptabilite — Gestion Perso</h1>'
    +'<div>Periode : '+d.du+' au '+d.au+' &nbsp;&middot;&nbsp; Client : '+d.client+'</div>'
    +'<div class="cards"><div class="card"><div class="l">Ventes</div><div class="v" style="color:#16a34a">'+d.ventes.toFixed(2)+' EUR</div></div>'
    +'<div class="card"><div class="l">Encaisse</div><div class="v" style="color:#2563eb">'+d.encaisse.toFixed(2)+' EUR</div></div>'
    +'<div class="card"><div class="l">Benefice estime</div><div class="v" style="color:#c9a84c">'+d.benef.toFixed(2)+' EUR</div></div>'
    +'<div class="card"><div class="l">Dette totale</div><div class="v" style="color:#dc2626">'+d.detteTotale.toFixed(2)+' EUR</div></div></div>'
    +'<table><thead><tr><th>Date</th><th>Type</th><th>Motif</th><th>Mode</th><th style="text-align:right">Montant</th></tr></thead><tbody>'+rowsHtml+'</tbody></table>'
    +'<p style="margin-top:20px;font-size:10px;color:#999">Document genere le '+new Date().toLocaleString()+'</p></body></html>';
  var b=new Blob([html],{type:'text/html'});var u=URL.createObjectURL(b);
  var pf=document.getElementById('printFrame');
  if(pf){pf.src=u;document.getElementById('modalPrintPreview').classList.add('open');pf.onload=function(){try{pf.contentWindow.print();}catch(e){}pf.onload=null;};}
  else window.open(u,'_blank');
}
</script>
"""
    JS=JS.replace("\n",eol)
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+eol+JS+html[at:]
    print("5) JS Compta ajoute")
else:
    print("5) deja present")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
