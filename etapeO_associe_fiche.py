#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeO_associe_fiche.py  (CRLF-safe, web/index.html)
Sur la fiche d'un associe uniquement :
  - panneau "Compte associe" : combien tu lui dois / il te doit
  - bouton "Releve PDF" : releve complet (dates+heures, ventes a prix coutant, paiements, frais, solde)
A lancer dans le dossier projet : python etapeO_associe_fiche.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in html else "\n"

# 1) Brancher loadAssocieRecap apres loadCantineRecap
hook="  loadCantineRecap(cid);"
hook_new="  loadCantineRecap(cid);"+eol+"  loadAssocieRecap(cid);"
if "loadAssocieRecap(cid);" not in html and hook in html:
    html=html.replace(hook,hook_new,1)
    print("1) loadAssocieRecap branche")
elif "loadAssocieRecap(cid);" in html:
    print("1) deja present")
else:
    print("1) ATTENTION appel loadCantineRecap non trouve")

# 2) Definir loadAssocieRecap + exportAssociePDF
if "function loadAssocieRecap" not in html:
    JS=r"""
<script>
// ===== FICHE ASSOCIE : solde + releve PDF =====
async function loadAssocieRecap(cid){
  if(!cid)return;
  var content=document.getElementById('soldeContent'); if(!content)return;
  var client=(clientsCache||[]).find(function(c){return String(c.id)===String(cid);});
  var box=document.getElementById('associeRecapPanel');
  if(!client||!client.associe){ if(box){box.style.display='none';box.innerHTML='';} return; }
  var res=await api('/api/clients/'+cid+'/stats');
  var solde=(res&&res.ok&&res.data)?(parseFloat(res.data.solde)||0):0;
  if(!box){box=document.createElement('div');box.id='associeRecapPanel';box.className='card';box.style.gridColumn='1/-1';content.appendChild(box);}
  box.style.display='block';
  var msg,col;
  if(solde>0.001){msg='Cet associé te doit <strong>'+fmt(solde)+'</strong>';col='var(--green)';}
  else if(solde<-0.001){msg='Tu dois <strong>'+fmt(-solde)+'</strong> à cet associé';col='var(--red)';}
  else{msg='Compte équilibré';col='var(--text3)';}
  box.innerHTML='<div class="card-title">🤝 Compte associé</div>'
    +'<div style="font-size:20px;font-weight:700;color:'+col+';margin-bottom:12px">'+msg+'</div>'
    +'<button class="btn primary" onclick="exportAssociePDF('+cid+')">🧾 Relevé PDF de l\'associé</button>';
}
async function exportAssociePDF(cid){
  var client=(clientsCache||[]).find(function(c){return String(c.id)===String(cid);});
  var nom=client?client.nom:'';
  var res=await api('/api/clients/'+cid+'/transactions');
  var trans=(res&&res.ok)?res.data.slice():[];
  trans.sort(function(a,b){return (a.date||'').localeCompare(b.date||'');});
  var totDeb=0,totCre=0,totFrais=0;
  var rows=trans.map(function(t){
    var net=parseFloat(t.montant_net||0);var fr=parseFloat(t.frais||0);
    if(t.type==='debit')totDeb+=net;else totCre+=net;
    totFrais+=fr;
    var dt=(t.date||'');var d=dt.slice(0,10).split('-').reverse().join('/');var h=(dt.length>10)?dt.slice(11,16):'';
    return '<tr><td>'+d+(h?' '+h:'')+'</td><td>'+(t.motif||'')+'</td><td>'+(t.type==='debit'?'Vente':'Paiement')+'</td><td>'+(t.mode_paiement||'')+'</td><td style="text-align:right">'+(t.quantite||1)+'</td><td style="text-align:right">'+parseFloat(t.prix_unitaire||0).toFixed(2)+'</td><td style="text-align:right">'+fr.toFixed(2)+'</td><td style="text-align:right">'+(t.type==='debit'?'+':'-')+net.toFixed(2)+'</td></tr>';
  }).join('');
  var solde=totDeb-totCre;
  var soldeTxt=solde>0.001?('Cet associe te doit '+solde.toFixed(2)+' EUR'):(solde<-0.001?('Tu dois '+(-solde).toFixed(2)+' EUR a cet associe'):'Compte equilibre');
  var html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Releve associe</title><style>body{font-family:Arial,sans-serif;font-size:11px;color:#111;padding:24px}h1{color:#8b5cf6;font-size:20px;margin-bottom:4px}table{width:100%;border-collapse:collapse;margin-top:12px}th{background:#8b5cf6;color:#fff;padding:5px 6px;text-align:left;font-size:10px}td{padding:5px 6px;border-bottom:1px solid #eee}.sum{display:flex;gap:14px;margin:14px 0;flex-wrap:wrap}.sum div{border:1px solid #ddd;border-radius:6px;padding:8px 12px}.tot{margin-top:14px;font-size:15px;font-weight:bold;color:#8b5cf6}.foot{margin-top:18px;font-size:9px;color:#999}</style></head><body>'
    +'<h1>Relevé associé — '+nom+'</h1><div>Édité le '+new Date().toLocaleString()+'</div>'
    +'<div class="sum"><div>Ventes (prix coûtant) : <strong>'+totDeb.toFixed(2)+' EUR</strong></div><div>Paiements reçus : <strong>'+totCre.toFixed(2)+' EUR</strong></div><div>Frais : <strong>'+totFrais.toFixed(2)+' EUR</strong></div></div>'
    +'<table><thead><tr><th>Date / heure</th><th>Article</th><th>Type</th><th>Mode</th><th style="text-align:right">Qté</th><th style="text-align:right">P.U.</th><th style="text-align:right">Frais</th><th style="text-align:right">Montant</th></tr></thead><tbody>'+rows+'</tbody></table>'
    +'<div class="tot">'+soldeTxt+'</div><div class="foot">Gestion Perso</div></body></html>';
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
    print("2) loadAssocieRecap + exportAssociePDF ajoutes")
else:
    print("2) deja present")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
