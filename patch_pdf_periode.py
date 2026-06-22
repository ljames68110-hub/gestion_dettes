#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_pdf_periode.py
Ajoute un choix de periode au releve PDF associe :
  - boutons "Tout" / "Ce mois"
  - une case a cocher par mois present dans les transactions de l'associe
Remplace loadAssocieRecap + exportAssociePDF (et ajoute 2 helpers).
A lancer dans le dossier projet : python patch_pdf_periode.py
"""
import os
def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def to_eol(b,eol): return eol.join(b.split("\n"))

NEW_BLOCK = r'''async function loadAssocieRecap(cid){
  if(!cid)return;
  var content=document.getElementById('soldeContent'); if(!content)return;
  var client=(clientsCache||[]).find(function(c){return String(c.id)===String(cid);});
  var box=document.getElementById('associeRecapPanel');
  if(!client||!client.associe){ if(box){box.style.display='none';box.innerHTML='';} return; }
  var res=await api('/api/clients/'+cid+'/stats');
  var solde=(res&&res.ok&&res.data)?(parseFloat(res.data.solde)||0):0;
  var rt=await api('/api/clients/'+cid+'/transactions');
  var trans=(rt&&rt.ok)?rt.data:[];
  var moisSet={};
  trans.forEach(function(t){var m=(t.date||'').slice(0,7);if(m.length===7)moisSet[m]=1;});
  var mois=Object.keys(moisSet).sort().reverse();
  if(!box){box=document.createElement('div');box.id='associeRecapPanel';box.className='card';box.style.gridColumn='1/-1';content.appendChild(box);}
  box.style.display='block';
  var msg,col;
  if(solde>0.001){msg='Cet associé te doit <strong>'+fmt(solde)+'</strong>';col='var(--green)';}
  else if(solde<-0.001){msg='Tu dois <strong>'+fmt(-solde)+'</strong> à cet associé';col='var(--red)';}
  else{msg='Compte équilibré';col='var(--text3)';}
  var moisHtml=mois.map(function(m){
    var lbl=m.slice(5,7)+'/'+m.slice(0,4);
    return '<label style="display:inline-flex;align-items:center;gap:5px;padding:5px 9px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius2);cursor:pointer;font-size:12px"><input type="checkbox" class="associeMois" value="'+m+'" style="width:auto;margin:0"> '+lbl+'</label>';
  }).join('');
  box.innerHTML='<div class="card-title">🤝 Compte associé</div>'
    +'<div style="font-size:20px;font-weight:700;color:'+col+';margin-bottom:12px">'+msg+'</div>'
    +'<div style="font-size:12px;color:var(--text3);margin-bottom:6px">Période du relevé PDF :</div>'
    +'<div style="display:flex;gap:6px;margin-bottom:8px">'
      +'<button class="btn" style="font-size:12px" onclick="associePdfTout()">Tout</button>'
      +'<button class="btn" style="font-size:12px" onclick="associePdfMoisEnCours()">Ce mois</button>'
    +'</div>'
    +'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">'+(moisHtml||'<span style="color:var(--text3);font-size:12px">Aucune transaction</span>')+'</div>'
    +'<button class="btn primary" onclick="exportAssociePDF('+cid+')">🧾 Relevé PDF de l\'associé</button>';
}
function associePdfTout(){
  document.querySelectorAll('.associeMois').forEach(function(c){c.checked=true;});
}
function associePdfMoisEnCours(){
  var now=new Date();var m=now.getFullYear()+'-'+('0'+(now.getMonth()+1)).slice(-2);
  document.querySelectorAll('.associeMois').forEach(function(c){c.checked=(c.value===m);});
}
async function exportAssociePDF(cid){
  var client=(clientsCache||[]).find(function(c){return String(c.id)===String(cid);});
  var nom=client?client.nom:'';
  var moisSel=[];document.querySelectorAll('.associeMois:checked').forEach(function(c){moisSel.push(c.value);});
  var res=await api('/api/clients/'+cid+'/transactions');
  var trans=(res&&res.ok)?res.data.slice():[];
  if(moisSel.length){trans=trans.filter(function(t){return moisSel.indexOf((t.date||'').slice(0,7))>=0;});}
  var periodeTxt;
  if(!moisSel.length){periodeTxt='Toutes les transactions';}
  else if(moisSel.length===1){periodeTxt='Mois : '+moisSel[0].slice(5,7)+'/'+moisSel[0].slice(0,4);}
  else{periodeTxt='Mois : '+moisSel.slice().sort().map(function(m){return m.slice(5,7)+'/'+m.slice(0,4);}).join(', ');}
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
    +'<h1>Relevé associé — '+nom+'</h1><div>Édité le '+new Date().toLocaleString()+' — '+periodeTxt+'</div>'
    +'<div class="sum"><div>Ventes (prix coûtant) : <strong>'+totDeb.toFixed(2)+' EUR</strong></div><div>Paiements reçus : <strong>'+totCre.toFixed(2)+' EUR</strong></div><div>Frais : <strong>'+totFrais.toFixed(2)+' EUR</strong></div></div>'
    +'<table><thead><tr><th>Date / heure</th><th>Article</th><th>Type</th><th>Mode</th><th style="text-align:right">Qté</th><th style="text-align:right">P.U.</th><th style="text-align:right">Frais</th><th style="text-align:right">Montant</th></tr></thead><tbody>'+rows+'</tbody></table>'
    +'<div class="tot">'+soldeTxt+'</div><div class="foot">Gestion Perso</div></body></html>';
  var b=new Blob([html],{type:'text/html'});var u=URL.createObjectURL(b);
  var pf=document.getElementById('printFrame');
  if(pf){pf.src=u;var mp=document.getElementById('modalPrintPreview');if(mp)mp.classList.add('open');pf.onload=function(){try{pf.contentWindow.print();}catch(e){}pf.onload=null;};}
  else window.open(u,'_blank');
}
'''

def patch_web(path="web/index.html"):
    t=read(path); eol=eol_of(t)
    if "associePdfMoisEnCours" in t:
        print("web : selecteur de periode deja present, saute"); return
    start=t.find("async function loadAssocieRecap(cid){")
    if start==-1:
        print("ATTENTION web : loadAssocieRecap introuvable"); return
    exs=t.find("async function exportAssociePDF(cid){", start)
    if exs==-1:
        print("ATTENTION web : exportAssociePDF introuvable"); return
    end=t.find("</script>", exs)
    if end==-1:
        print("ATTENTION web : </script> de fin introuvable"); return
    newblock=to_eol(NEW_BLOCK, eol)
    t=t[:start]+newblock+t[end:]
    write(path,t)
    print("web : loadAssocieRecap + exportAssociePDF remplacees, selecteur de periode ajoute OK")

if __name__=="__main__":
    if os.path.exists("web/index.html"): patch_web()
    else: print("ATTENTION : web/index.html introuvable ici")
    print("=== TERMINE ===")
