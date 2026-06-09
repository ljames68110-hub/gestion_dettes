#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etape3_paiement_tabac.py
Paiement en tabac dans la caisse :
  - les 3 types de tabac (regles dans Parametres) dans le menu de paiement
  - champ "Nombre de paquets" qui apparait quand un tabac est choisi
  - comptant -> +stock tabac ; credit -> dette tabac (en paquets)
  - les articles du panier sortent de leur stock
A lancer dans le dossier projet : python etape3_paiement_tabac.py
"""
import io, re
p="web/index.html"
html=io.open(p,"r",encoding="utf-8").read()
orig=len(html)

# ── 1) Ajouter onchange au select posMode + champ quantite juste apres ──
old_sel='<select class="pos-mode" id="posMode">\n                <option value="Liquide">Liquide</option><option value="Virement">Virement</option><option value="PCS">PCS</option><option value="Paysafecard">Paysafecard</option><option value="WesternUnion">Western Union</option>\n              </select>'
new_sel='<select class="pos-mode" id="posMode" onchange="posModeChanged()">\n                <option value="Liquide">Liquide</option><option value="Virement">Virement</option><option value="PCS">PCS</option><option value="Paysafecard">Paysafecard</option><option value="WesternUnion">Western Union</option>\n              </select>\n              <div id="posTabacQtyWrap" style="display:none;align-items:center;gap:8px;margin-top:4px">\n                <span style="font-size:13px;color:var(--gold2);flex:1">Nombre de paquets</span>\n                <input type="number" id="posTabacQty" value="1" min="1" step="1" style="width:90px;text-align:right;padding:6px 8px;border-radius:8px;border:1px solid var(--gold);background:var(--bg3);color:var(--text);font-size:14px">\n              </div>'
if 'id="posTabacQty"' not in html and old_sel in html:
    html=html.replace(old_sel,new_sel,1)
    print("1) menu mode + champ quantite tabac ajoutes")
elif 'id="posTabacQty"' in html:
    print("1) deja present")
else:
    print("1) ATTENTION select posMode non trouve a l'identique")

# ── 2) Brancher le tabac au debut de posEncaisser (early return) ──
old_start='''async function posEncaisser(){
  var cid=parseInt(document.getElementById('posClient').value);
  if(!cid){notify('Choisis un client','error');return;}'''
new_start='''async function posEncaisser(){
  var cid=parseInt(document.getElementById('posClient').value);
  if(!cid){notify('Choisis un client','error');return;}
  var _tmode=document.getElementById('posMode').value;
  if(_tmode&&_tmode.indexOf('tabac:')===0){return posEncaisserTabac(cid,_tmode);}'''
if old_start in html and "posEncaisserTabac(cid,_tmode)" not in html:
    html=html.replace(old_start,new_start,1)
    print("2) branche tabac ajoutee dans posEncaisser")
elif "posEncaisserTabac(cid,_tmode)" in html:
    print("2) deja present")
else:
    print("2) ATTENTION debut posEncaisser non trouve")

# ── 3) JS : remplir le menu, gerer l'affichage du champ, encaisser le tabac ──
if "function posEncaisserTabac" not in html:
    JS=r"""
<script>
// ===== PAIEMENT EN TABAC (caisse) =====
function fillPosModeTabac(){
  var sel=document.getElementById('posMode');
  if(!sel)return;
  // retirer les anciennes options tabac
  Array.prototype.slice.call(sel.querySelectorAll('option[data-tabac="1"]')).forEach(function(o){o.remove();});
  (typesTabacCache||[]).forEach(function(t){
    var o=document.createElement('option');
    o.value='tabac:'+t.id;
    o.setAttribute('data-tabac','1');
    o.textContent='🚬 '+t.nom+(t.prix>0?(' ('+parseFloat(t.prix).toFixed(2)+' EUR)'):'');
    sel.appendChild(o);
  });
}
function posModeChanged(){
  var sel=document.getElementById('posMode');
  var wrap=document.getElementById('posTabacQtyWrap');
  if(!sel||!wrap)return;
  var isTabac=sel.value && sel.value.indexOf('tabac:')===0;
  wrap.style.display=isTabac?'flex':'none';
}
async function posEncaisserTabac(cid,mode){
  var tid=parseInt(mode.split(':')[1]);
  var t=(typesTabacCache||[]).find(function(x){return x.id===tid;});
  if(!t){notify('Type de tabac introuvable','error');return;}
  var packs=parseFloat(document.getElementById('posTabacQty').value)||0;
  if(packs<=0){notify('Indique le nombre de paquets','error');return;}
  var prix=parseFloat(t.prix)||0;
  var valeur=Math.round(packs*prix*100)/100;
  var _posDate=(document.getElementById('posDate')&&document.getElementById('posDate').value)?document.getElementById('posDate').value:undefined;
  var btn=document.getElementById('posCashout');btn.disabled=true;btn.textContent='Encaissement...';
  var motif=(posCart.length?posCart.map(function(l){return l.nom;}).join(', '):'Paiement tabac');
  var comptant=(posPayMode==='cash');
  var body={client_id:cid,type:'debit',motif:motif,quantite:packs,unite:'paquet',
    prix_unitaire:prix,mode_paiement:t.nom,
    notes:(comptant?'[CAISSE PAYE] ':'[CAISSE CREDIT] ')+'Tabac: '+packs+' x '+t.nom,
    frais_deduits:0,compte:'tabac',date:_posDate};
  var ok=true;
  try{var r=await api('/api/transactions',{method:'POST',body:body});if(!r||!r.ok)ok=false;}catch(e){ok=false;}
  // Les articles du panier sortent de leur stock
  posCart.forEach(function(l){api('/api/catalogue/'+l.id+'/adjust-stock',{method:'POST',body:{delta:-l.qty}}).catch(function(){});});
  // Comptant : le tabac rentre dans le stock
  if(comptant && ok){
    var nouveauStock=(parseFloat(t.stock)||0)+packs;
    try{await api('/api/types-tabac/'+tid,{method:'PUT',body:{stock:nouveauStock}});}catch(e){}
  }
  btn.disabled=false;btn.textContent='Encaisser';
  if(ok){
    notify(comptant
      ? (packs+' '+t.nom+' encaisse(s) -> stock (valeur ~'+valeur.toFixed(2)+' EUR)')
      : (packs+' '+t.nom+' ajoute(s) a la dette tabac du client'));
    posCart=[];var _pr=document.getElementById('posReduc');if(_pr)_pr.value='0';
    document.getElementById('posTabacQty').value='1';
    renderPosCart();
    if(typeof loadTypesTabac==='function')loadTypesTabac();
    if(typeof loadDashboard==='function')loadDashboard();
    if(typeof loadTransactions==='function')loadTransactions();
    onPosClientChange();
  }else{
    notify('Erreur encaissement tabac','error');
  }
}
</script>
"""
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+"\n"+JS+html[at:]
    print("3) JS paiement tabac injecte")
else:
    print("3) deja present")

# ── 4) initCaisse : charger les types tabac + remplir le menu ──
m=re.search(r"(function initCaisse\(\)\{)", html)
if m and "fillPosModeTabac()" not in html:
    inject=m.group(1)+"if(typeof loadTypesTabac==='function'){loadTypesTabac().then(function(){fillPosModeTabac();}).catch(function(){fillPosModeTabac();});}else{fillPosModeTabac();}posModeChanged();"
    html=html.replace(m.group(1),inject,1)
    print("4) initCaisse charge et remplit les modes tabac")
else:
    print("4) deja ok ou introuvable")

io.open(p,"w",encoding="utf-8").write(html)
print("")
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
