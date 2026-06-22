#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeH_bons_cantine.py  (CRLF-safe)
Panneau "Bons de cantine" sur la fiche client : liste des operations cantine avec cases a cocher
+ bouton qui genere un recapitulatif PDF (selection) via la fenetre d'impression existante.
A lancer dans le dossier projet : python etapeH_bons_cantine.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in html else "\n"

# 1) Appeler loadCantineRecap apres loadFraisDus
old="  loadFraisDus(cid);"
new="  loadFraisDus(cid);"+eol+"  loadCantineRecap(cid);"
if "loadCantineRecap(cid);" not in html and old in html:
    html=html.replace(old,new,1)
    print("1) loadCantineRecap branche apres loadFraisDus")
elif "loadCantineRecap(cid);" in html:
    print("1) deja present")
else:
    print("1) ATTENTION appel loadFraisDus non trouve")

# 2) Definir loadCantineRecap + exportCantinePDF
if "function loadCantineRecap" not in html:
    JS=r"""
<script>
// ===== BONS DE CANTINE (fiche client) =====
async function loadCantineRecap(cid){
  if(!cid)return;
  var content=document.getElementById('soldeContent'); if(!content)return;
  var res=await api('/api/transactions?limit=5000');
  var all=(res&&res.ok)?res.data:[];
  var cant=all.filter(function(t){return String(t.client_id)===String(cid) && (t.compte==='cantine');});
  var box=document.getElementById('cantineRecapPanel');
  if(!box){box=document.createElement('div');box.id='cantineRecapPanel';box.className='card';box.style.gridColumn='1/-1';content.appendChild(box);}
  if(!cant.length){box.style.display='none';box.innerHTML='';return;}
  box.style.display='block';
  window._cantineRecapData=cant;
  var rows=cant.slice().sort(function(a,b){return (b.date||'').localeCompare(a.date||'');}).map(function(t){
    var net=parseFloat(t.montant_net||0);
    return '<label style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);cursor:pointer">'
      +'<input type="checkbox" class="cantineChk" value="'+t.id+'" checked style="width:auto;margin:0">'
      +'<span style="flex:1;color:var(--text)">'+((t.date||'').slice(0,10))+' &middot; '+(t.motif||'')+'</span>'
      +'<span class="mono" style="color:'+(t.type==='debit'?'var(--green)':'var(--red)')+'">'+(t.type==='debit'?'+':'-')+fmt(net)+'</span></label>';
  }).join('');
  box.innerHTML='<div class="card-title">🍽 Bons de cantine</div>'
    +'<div style="font-size:12px;color:var(--text3);margin-bottom:8px">Coche les operations a inclure, puis genere le recapitulatif.</div>'
    +'<div style="max-height:240px;overflow:auto;margin-bottom:12px">'+rows+'</div>'
    +'<button class="btn primary" onclick="exportCantinePDF('+cid+')">🧾 Recapitulatif PDF (selection)</button>';
}
function exportCantinePDF(cid){
  var data=window._cantineRecapData||[];
  var checked={};document.querySelectorAll('.cantineChk:checked').forEach(function(c){checked[c.value]=true;});
  var sel=data.filter(function(t){return checked[String(t.id)];});
  if(!sel.length){notify('Coche au moins une operation','error');return;}
  var client=(clientsCache||[]).find(function(c){return String(c.id)===String(cid);});
  var nom=client?client.nom:'';
  var total=0;
  var rowsHtml=sel.slice().sort(function(a,b){return (a.date||'').localeCompare(b.date||'');}).map(function(t){
    var net=parseFloat(t.montant_net||0);
    total+=(t.type==='debit'?net:-net);
    return '<tr><td>'+((t.date||'').slice(0,10))+'</td><td>'+(t.motif||'')+'</td><td>'+(t.type==='debit'?'Vente':'Remboursement')+'</td><td style="text-align:right">'+(t.type==='debit'?'+':'-')+net.toFixed(2)+' EUR</td></tr>';
  }).join('');
  var html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Bon de cantine</title><style>body{font-family:Arial,sans-serif;font-size:12px;color:#111;padding:24px}h1{color:#16a34a;font-size:20px;margin-bottom:4px}table{width:100%;border-collapse:collapse;margin-top:12px}th{background:#16a34a;color:#fff;padding:6px 8px;text-align:left;font-size:11px}td{padding:6px 8px;border-bottom:1px solid #eee}.tot{margin-top:14px;font-size:16px;font-weight:bold;text-align:right;color:#16a34a}.foot{margin-top:20px;font-size:10px;color:#999}</style></head><body>'
    +'<h1>Bon de cantine — '+nom+'</h1>'
    +'<div>Document genere le '+new Date().toLocaleString()+'</div>'
    +'<table><thead><tr><th>Date</th><th>Article</th><th>Type</th><th style="text-align:right">Montant</th></tr></thead><tbody>'+rowsHtml+'</tbody></table>'
    +'<div class="tot">Solde cantine (selection) : '+total.toFixed(2)+' EUR</div>'
    +'<div class="foot">Gestion Perso</div></body></html>';
  var b=new Blob([html],{type:'text/html'});var u=URL.createObjectURL(b);
  var pf=document.getElementById('printFrame');
  if(pf){pf.src=u;var mp=document.getElementById('modalPrintPreview');if(mp)mp.classList.add('open');pf.onload=function(){try{pf.contentWindow.print();}catch(e){}pf.onload=null;};}
  else window.open(u,'_blank');
}
</script>
"""
    JS=JS.replace("\n",eol)
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+eol+JS+html[at:]
    print("2) loadCantineRecap + exportCantinePDF ajoutes")
else:
    print("2) deja present")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
