#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_facture_frais_caisse.py
Ajoute dans la caisse un bouton "Facture de frais" : genere un document
imprimable listant les frais en attente du client selectionne (PCS/Paysafecard),
SANS rien ajouter a la dette (les frais sont deja comptes dans le solde).
A lancer dans le dossier projet : python patch_facture_frais_caisse.py
"""
import os
def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def to_eol(b,eol): return eol.join(b.split("\n"))

JS_FUNC = r'''async function factureFraisCaisse(){
  var cid=parseInt(document.getElementById('posClient').value);
  if(!cid){notify('Choisis un client d\'abord','error');return;}
  var client=(clientsCache||[]).find(function(c){return c.id===cid;});
  var nom=client?client.nom:'';
  var res=await api('/api/clients/'+cid+'/frais-dus');
  var frais=(res&&res.ok&&res.data&&res.data.frais)?res.data.frais:[];
  if(!frais.length){notify('Aucun frais en attente pour ce client');return;}
  var total=0;
  var rows=frais.map(function(f){
    var m=parseFloat(f.montant||0);total+=m;
    var d=(f.date||'').slice(0,10).split('-').reverse().join('/');
    return '<tr><td>'+d+'</td><td>Frais de service</td><td style="text-align:right">'+m.toFixed(2)+' EUR</td></tr>';
  }).join('');
  var dateEd=new Date().toLocaleString();
  var html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Facture de frais</title><style>body{font-family:Arial,sans-serif;font-size:12px;color:#111;padding:24px}h1{color:#b8860b;font-size:20px;margin-bottom:4px}table{width:100%;border-collapse:collapse;margin-top:14px}th{background:#b8860b;color:#fff;padding:6px 8px;text-align:left;font-size:11px}td{padding:6px 8px;border-bottom:1px solid #eee}.tot{margin-top:16px;font-size:16px;font-weight:bold;color:#b8860b;text-align:right}.foot{margin-top:20px;font-size:9px;color:#999}</style></head><body>'
    +'<h1>Facture de frais</h1><div>Client : <strong>'+nom+'</strong></div><div>Éditée le '+dateEd+'</div>'
    +'<table><thead><tr><th>Date</th><th>Désignation</th><th style="text-align:right">Montant</th></tr></thead><tbody>'+rows+'</tbody></table>'
    +'<div class="tot">Total des frais : '+total.toFixed(2)+' EUR</div>'
    +'<div class="foot">Gestion Perso — justificatif de frais (deja inclus dans le solde du client).</div></body></html>';
  var b=new Blob([html],{type:'text/html'});var u=URL.createObjectURL(b);
  var pf=document.getElementById('printFrame');
  if(pf){pf.src=u;var mp=document.getElementById('modalPrintPreview');if(mp)mp.classList.add('open');pf.onload=function(){try{pf.contentWindow.print();}catch(e){}pf.onload=null;};}
  else window.open(u,'_blank');
}
'''

def patch_web(path="web/index.html"):
    t=read(path); eol=eol_of(t)
    if "factureFraisCaisse" in t:
        print("web : facture de frais caisse deja presente, saute"); return
    # 1) bouton sous "Encaisser"
    parts=t.split(eol); inserted=False
    for i,l in enumerate(parts):
        if 'id="posCashout"' in l and 'pos-cashout' in l:
            indent=l[:len(l)-len(l.lstrip())]
            newbtn=indent+'<button class="btn" id="posFraisFacture" style="width:100%;margin-top:8px;font-size:13px" onclick="factureFraisCaisse()">🧾 Facture de frais</button>'
            parts.insert(i+1,newbtn); inserted=True; break
    if inserted:
        t=eol.join(parts); print("web : bouton 'Facture de frais' insere sous Encaisser OK")
    else:
        print("ATTENTION web : bouton posCashout introuvable")
    # 2) fonction JS avant initCaisse
    anchor="function initCaisse(){"
    i=t.find(anchor)
    if i==-1:
        print("ATTENTION web : initCaisse introuvable")
    else:
        t=t[:i]+to_eol(JS_FUNC,eol)+eol+t[i:]
        print("web : fonction factureFraisCaisse ajoutee OK")
    write(path,t)

if __name__=="__main__":
    if os.path.exists("web/index.html"): patch_web()
    else: print("ATTENTION web/index.html introuvable")
    print("=== TERMINE ===")
