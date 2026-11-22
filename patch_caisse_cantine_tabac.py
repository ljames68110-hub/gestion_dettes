#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_caisse_cantine_tabac.py
Ajoute dans la CAISSE un bloc "Comptes cantine & tabac" (sous l'encadre Dette) qui
affiche le vrai solde cantine (en euros) et le solde tabac (en paquets), avec pour
chacun un bouton "Encaisser" (le client paie / rend) et "+ Dette" (ajouter une
charge). Repond au cas ou les dettes tabac/cantine n'apparaissaient pas dans la
liste des dettes ouvertes (celle-ci est basee sur le restant en euros, alors qu'une
dette tabac se compte en paquets).
Sans node. 100% frontend. Idempotent, CRLF/LF preserves.
A lancer dans le dossier du projet : python patch_caisse_cantine_tabac.py
"""
import os, sys

F = "web/index.html"
MARK = "renderComptesCT"

CH = [
 ("bloc HTML dans la caisse",
  '<div id="posDettesList"></div>',
  '<div id="posDettesList"></div><div id="posCompteCT" style="margin-top:8px"></div>'),

 ("appel au changement de client",
  "renderAssoCards(posDette);posLoadDettesOuvertes(cid);",
  "renderAssoCards(posDette);posLoadDettesOuvertes(cid);renderComptesCT(cid);"),
]

JS = r"""
/* ===== CAISSE : comptes cantine & tabac ===== */
async function renderComptesCT(cid){
  var box=document.getElementById('posCompteCT'); if(!box) return;
  box.innerHTML='';
  if(!cid || (typeof posIsAssocie!=='undefined' && posIsAssocie)) return;
  var cantine=0, paquets=0;
  try{ var rc=await api('/api/clients/'+cid+'/stats-comptes'); if(rc&&rc.ok&&rc.data&&rc.data.cantine) cantine=parseFloat(rc.data.cantine.solde)||0; }catch(e){}
  try{ var rt=await api('/api/clients/'+cid+'/tabac-paquets'); if(rt&&rt.ok&&rt.data) paquets=parseFloat(rt.data.paquets)||0; }catch(e){}
  var types=(window.typesTabacCache||[]);
  var opts=types.map(function(t){return '<option value="'+t.id+'">'+t.nom+'</option>';}).join('');
  var cCol=cantine>0.009?'var(--green)':(cantine<-0.009?'var(--red)':'var(--text3)');
  var pCol=Math.abs(paquets)>0.009?'var(--gold2)':'var(--text3)';
  var _inp='padding:6px 8px;border-radius:8px;border:1px solid var(--border);background:var(--bg2);color:var(--text);font-size:13px';
  box.innerHTML=
      '<div style="margin-top:4px;border-top:1px dashed var(--border);padding-top:8px">'
    + '<div style="font-size:11px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:1px">Comptes cantine &amp; tabac</div>'
    + '<div style="display:flex;align-items:center;gap:5px;margin-bottom:6px;flex-wrap:wrap">'
    +   '<span style="flex:1;min-width:108px;font-size:12px">🍽 Cantine : <b style="color:'+cCol+'">'+fmt(cantine)+'</b></span>'
    +   '<input id="ctCantineM" type="number" step="0.5" min="0" placeholder="€" style="width:64px;'+_inp+'">'
    +   '<button type="button" class="btn" style="padding:5px 9px;font-size:11px" onclick="ctEncaisserCantine()">Encaisser</button>'
    +   '<button type="button" class="btn" style="padding:5px 9px;font-size:11px;background:var(--bg3)" onclick="ctDetteCantine()">+ Dette</button>'
    + '</div>'
    + '<div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap">'
    +   '<span style="flex:1;min-width:108px;font-size:12px">🚬 Tabac : <b style="color:'+pCol+'">'+_fmtQte(paquets)+' paquet(s)</b></span>'
    +   (opts?('<select id="ctTabacType" style="'+_inp+'">'+opts+'</select>'):'')
    +   '<input id="ctTabacQ" type="number" step="1" min="0" placeholder="paq." style="width:56px;'+_inp+'">'
    +   '<button type="button" class="btn" style="padding:5px 9px;font-size:11px" onclick="ctEncaisserTabacDette()">Rendu</button>'
    +   '<button type="button" class="btn" style="padding:5px 9px;font-size:11px;background:var(--bg3)" onclick="ctDetteTabac()">+ Dette</button>'
    + '</div></div>';
}

async function _ctPost(body, okMsg){
  var cid=parseInt((document.getElementById('posClient')||{}).value);
  if(!cid){ if(typeof notify==='function')notify('Choisis un client','error'); return false; }
  body.client_id=cid;
  var _d=(document.getElementById('posDate')||{}).value;
  var _t=(document.getElementById('posTime')||{}).value;
  if(_d) body.date=_d+(_t?(' '+_t):'');
  try{
    var r=await api('/api/transactions',{method:'POST',body:body});
    if(r&&r.ok){ if(typeof notify==='function')notify(okMsg,'success'); if(typeof onPosClientChange==='function')onPosClientChange(); return true; }
    if(typeof notify==='function')notify((r&&r.error)||'Echec','error'); return false;
  }catch(e){ if(typeof notify==='function')notify('Erreur','error'); return false; }
}

function _ctTabacSel(){
  var sel=document.getElementById('ctTabacType');
  var tid=sel?parseInt(sel.value):0;
  var t=(window.typesTabacCache||[]).find(function(x){return x.id===tid;});
  return {nom:(t?t.nom:'Tabac'), prix:(t?(parseFloat(t.prix)||0):0)};
}

async function ctEncaisserCantine(){
  var m=parseFloat(((document.getElementById('ctCantineM')||{}).value||'0').replace(',','.'))||0;
  if(m<=0){ if(typeof notify==='function')notify('Montant invalide','error'); return; }
  await _ctPost({type:'credit',motif:'Remboursement cantine',quantite:1,unite:'piece',prix_unitaire:m,
    mode_paiement:'Cantine',notes:'[CAISSE] Encaissement dette cantine',frais_deduits:0,compte:'cantine'},
    m.toFixed(2)+' € encaissé (cantine)');
}
async function ctDetteCantine(){
  var m=parseFloat(((document.getElementById('ctCantineM')||{}).value||'0').replace(',','.'))||0;
  if(m<=0){ if(typeof notify==='function')notify('Montant invalide','error'); return; }
  await _ctPost({type:'debit',motif:'Vente cantine',quantite:1,unite:'piece',prix_unitaire:m,
    mode_paiement:'Cantine',notes:'[CAISSE] Dette cantine',frais_deduits:0,compte:'cantine'},
    'Dette cantine ajoutée : '+m.toFixed(2)+' €');
}
async function ctEncaisserTabacDette(){
  var q=parseFloat(((document.getElementById('ctTabacQ')||{}).value||'0').replace(',','.'))||0;
  if(q<=0){ if(typeof notify==='function')notify('Nombre de paquets invalide','error'); return; }
  var ty=_ctTabacSel();
  await _ctPost({type:'credit',motif:'Rendu tabac',quantite:q,unite:'paquet',prix_unitaire:ty.prix,
    mode_paiement:ty.nom,notes:'[CAISSE] Rendu '+q+' x '+ty.nom,frais_deduits:0,compte:'tabac'},
    _fmtQte(q)+' paquet(s) rendu(s)');
}
async function ctDetteTabac(){
  var q=parseFloat(((document.getElementById('ctTabacQ')||{}).value||'0').replace(',','.'))||0;
  if(q<=0){ if(typeof notify==='function')notify('Nombre de paquets invalide','error'); return; }
  var ty=_ctTabacSel();
  await _ctPost({type:'debit',motif:'Tabac',quantite:q,unite:'paquet',prix_unitaire:ty.prix,
    mode_paiement:ty.nom,notes:'[CAISSE] Dette '+q+' x '+ty.nom,frais_deduits:0,compte:'tabac'},
    'Dette tabac ajoutée : '+_fmtQte(q)+' x '+ty.nom);
}
"""

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)

def main():
    if not os.path.exists(F):
        print("ERREUR : %s introuvable" % F); sys.exit(1)
    t = read(F); eol = "\r\n" if "\r\n" in t else "\n"
    if MARK in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)

    for label, old, new in CH:
        n = t.count(old)
        if n != 1:
            print("  [X] ancre '%s' trouvee %dx (attendu 1) -- rien modifie" % (label, n)); sys.exit(1)
    for label, old, new in CH:
        t = t.replace(old, new, 1)
        print("  [+] %s" % label)

    pos = t.rfind("</body>")
    if pos < 0:
        print("  [X] </body> introuvable"); sys.exit(1)
    block = "<script>" + eol + eol.join(JS.split("\n")) + eol + "</script>" + eol
    t = t[:pos] + block + t[pos:]
    write(F, t)
    print("  [+] module JavaScript injecte")

    if read(F).count(MARK) < 1:
        print("  [!] verification inattendue"); sys.exit(1)
    print("\nTermine (caisse : comptes cantine & tabac).")

if __name__ == "__main__":
    main()
