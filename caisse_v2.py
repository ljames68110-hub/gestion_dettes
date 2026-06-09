#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
caisse_v2.py - Caisse complete :
  - clients charges au demarrage
  - dette du client affichee a la selection
  - panier d'articles (vente) + zone remboursement (encaisser dette)
  - case "j'absorbe les frais" sur le remboursement (PCS/Paysafe...)
  - mode de paiement grise si pas de remboursement
  - un seul bouton Encaisser : traite ventes + remboursement
  - retire les boutons "Nouvelle transaction" (sidebar + dashboard)
Idempotent. Usage (dossier projet): python caisse_v2.py
"""
import io, re
p="web/index.html"
with io.open(p,"r",encoding="utf-8") as f:
    html=f.read()
orig=len(html)

# ════════════════════════════════════════════════════════════════
# 1) Charger clients au demarrage (hook initApp pose par setup_all)
# ════════════════════════════════════════════════════════════════
hook="try{loadCatalogue();}catch(e){}try{loadCategories();}catch(e){}"
if hook in html and "loadClients()" not in hook:
    html=html.replace(hook,"try{loadClients();}catch(e){}"+hook,1)
    print("1) clients charges au demarrage")
elif "try{loadClients();}catch(e){}try{loadCatalogue();}" in html:
    print("1) deja: clients au demarrage")
else:
    m=re.search(r"(function initApp\(\)\s*\{\s*)",html)
    if m:
        html=html.replace(m.group(1),m.group(1)+"loadClients();",1)
        print("1) clients au demarrage (initApp direct)")
    else:
        print("1) ATTENTION hook/initApp introuvable")

# ════════════════════════════════════════════════════════════════
# 2) Retirer les boutons "Nouvelle transaction"
# ════════════════════════════════════════════════════════════════
nav_btn='<div class="nav-item" onclick="openModal(\'transaction\')"><span class="nav-icon">＋</span> Nouvelle transaction</div>'
if nav_btn in html:
    html=html.replace(nav_btn,'',1)
    print("2a) bouton sidebar 'Nouvelle transaction' retire")
else:
    print("2a) bouton sidebar deja absent")
dash_btn='<button class="btn primary" onclick="openModal(\'transaction\')">+ Nouvelle transaction</button>'
if dash_btn in html:
    html=html.replace(dash_btn,'',1)
    print("2b) bouton dashboard 'Nouvelle transaction' retire")
else:
    print("2b) bouton dashboard deja absent")

# ════════════════════════════════════════════════════════════════
# 3) Remplacer le pied de caisse pour ajouter la zone remboursement
#    On reconstruit la cart-foot complete.
# ════════════════════════════════════════════════════════════════
# Ancien pied (depuis setup_all)
old_foot_re = re.compile(
    r'<div class="pos-cart-foot">.*?<button class="pos-cashout" id="posCashout" onclick="posEncaisser\(\)">Encaisser</button>\s*</div>',
    re.DOTALL)
new_foot = '''<div class="pos-cart-foot">
              <div id="posDetteBox" style="display:none;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius2);padding:10px 12px;font-size:13px">
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <span style="color:var(--text3)">Dette actuelle</span>
                  <span id="posDetteVal" style="font-family:DM Mono,monospace;font-weight:700;color:var(--green)">0.00 EUR</span>
                </div>
                <div style="margin-top:8px;display:flex;gap:6px;align-items:center">
                  <input type="number" id="posRemb" value="0" step="0.5" min="0" placeholder="Montant rembourse" style="flex:1;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg2);color:var(--text);font-size:14px" oninput="updatePosTotals()">
                  <button class="btn" style="font-size:11px;padding:6px 10px" onclick="posRembAll()">Tout</button>
                </div>
                <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text2);margin-top:6px;cursor:pointer">
                  <input type="checkbox" id="posRembFrais" checked onchange="updatePosTotals()" style="width:auto;margin:0"> J'absorbe les frais sur le remboursement
                </label>
              </div>
              <div class="pos-total"><span style="font-size:14px;color:var(--text3);font-weight:500">VENTE</span><span class="amt" id="posTotal">0.00 EUR</span></div>
              <div class="pos-pay">
                <button class="pos-paybtn active" id="posPayCash" onclick="setPosPay('cash')">Comptant (paye)</button>
                <button class="pos-paybtn" id="posPayCredit" onclick="setPosPay('credit')">A credit (dette)</button>
              </div>
              <select class="pos-mode" id="posMode">
                <option value="Liquide">Liquide</option><option value="Virement">Virement</option><option value="PCS">PCS</option><option value="Paysafecard">Paysafecard</option><option value="WesternUnion">Western Union</option>
              </select>
              <button class="pos-cashout" id="posCashout" onclick="posEncaisser()">Encaisser</button>
            </div>'''
if old_foot_re.search(html):
    html = old_foot_re.sub(new_foot, html, count=1)
    print("3) pied de caisse enrichi (zone remboursement + dette)")
else:
    print("3) ATTENTION pied de caisse non trouve - structure differente")

# Ajouter onchange sur le select client pour charger la dette
old_client_sel = '<select class="pos-client" id="posClient"><option value="">-- Choisir un client (obligatoire) --</option></select>'
new_client_sel = '<select class="pos-client" id="posClient" onchange="onPosClientChange()"><option value="">-- Choisir un client (obligatoire) --</option></select>'
if old_client_sel in html:
    html=html.replace(old_client_sel,new_client_sel,1)
    print("3b) select client: onchange charge la dette")
else:
    print("3b) select client deja avec onchange ou structure differente")

# ════════════════════════════════════════════════════════════════
# 4) Remplacer le JS caisse (setPosPay, encaisser) + ajouter dette/remb
#    On retire l'ancien setPosPay et posEncaisser, on injecte un bloc neuf.
# ════════════════════════════════════════════════════════════════
# Retirer ancien setPosPay
html = re.sub(r"function setPosPay\(mode\)\{[^}]*\}", "", html, count=1)
# Retirer ancien posEncaisser (async, peut contenir des accolades -> regex gourmande bornee)
html = re.sub(r"async function posEncaisser\(\)\{.*?\}\}", "", html, count=1, flags=re.DOTALL)

NEWJS = r"""
<script>
// ===== CAISSE v2 : dette + remboursement =====
var posDette = 0;
function onPosClientChange(){
  var cid=parseInt(document.getElementById('posClient').value);
  var box=document.getElementById('posDetteBox');
  if(!cid){ if(box)box.style.display='none'; posDette=0; updatePosTotals(); return; }
  api('/api/clients/'+cid+'/stats').then(function(res){
    posDette = (res&&res.ok&&res.data)?(parseFloat(res.data.solde)||0):0;
    if(box)box.style.display='block';
    var dv=document.getElementById('posDetteVal');
    if(dv){ dv.textContent=posDette.toFixed(2)+' EUR'; dv.style.color=posDette>0?'var(--green)':'var(--text3)'; }
    var ri=document.getElementById('posRemb'); if(ri) ri.value='0';
    updatePosTotals();
  });
}
function posRembAll(){ var ri=document.getElementById('posRemb'); if(ri){ ri.value=(posDette>0?posDette:0).toFixed(2); updatePosTotals(); } }
function setPosPay(mode){
  posPayMode=mode;
  document.getElementById('posPayCash').classList.toggle('active',mode==='cash');
  document.getElementById('posPayCredit').classList.toggle('active',mode==='credit');
  updatePosTotals();
}
function getCartTotal(){ var t=0; posCart.forEach(function(l){t+=l.prix*l.qty;}); return t; }
function getRemb(){ var ri=document.getElementById('posRemb'); return ri?(parseFloat(ri.value)||0):0; }
function updatePosTotals(){
  var venteTotal=getCartTotal();
  var el=document.getElementById('posTotal'); if(el)el.textContent=venteTotal.toFixed(2)+' EUR';
  // mode de paiement : utile seulement si vente comptant OU remboursement>0
  var remb=getRemb();
  var pm=document.getElementById('posMode');
  if(pm){
    var needMode = (venteTotal>0 && posPayMode==='cash') || remb>0;
    pm.disabled=!needMode; pm.style.opacity=needMode?'1':'0.4'; pm.style.pointerEvents=needMode?'auto':'none';
  }
  var btn=document.getElementById('posCashout');
  if(btn) btn.disabled=(venteTotal<=0 && remb<=0);
}
// surcharger renderPosCart pour recalculer les totaux ensuite
var _oldRenderCart = (typeof renderPosCart==='function')?renderPosCart:null;
renderPosCart=function(){
  var body=document.getElementById('posCartBody');
  if(!body)return;
  if(!posCart.length){ body.innerHTML='<div class="pos-empty">Cliquez sur des articles pour les ajouter</div>'; }
  else{
    body.innerHTML='';
    posCart.forEach(function(l){
      var sub=l.prix*l.qty;
      var row=document.createElement('div');row.className='pos-line';
      row.innerHTML='<div class="lname">'+l.nom+'<br><span style="font-size:11px;color:var(--text3)">'+l.prix.toFixed(2)+' EUR</span></div><div class="lqty"><button onclick="posChangeQty('+l.id+',-1)">-</button><input type="number" value="'+l.qty+'" min="0" step="1" onchange="posSetQty('+l.id+',this.value)"><button onclick="posChangeQty('+l.id+',1)">+</button></div><div class="lsub">'+sub.toFixed(2)+'</div><button class="ldel" onclick="posRemove('+l.id+')">x</button>';
      body.appendChild(row);
    });
  }
  updatePosTotals();
};
async function posEncaisser(){
  var cid=parseInt(document.getElementById('posClient').value);
  if(!cid){notify('Choisis un client','error');return;}
  var venteTotal=getCartTotal();
  var remb=getRemb();
  if(venteTotal<=0 && remb<=0){notify('Rien a encaisser','error');return;}
  var mode=document.getElementById('posMode').value;
  var btn=document.getElementById('posCashout');btn.disabled=true;btn.textContent='Encaissement...';
  var ok=0,fail=0;
  // 1) Ventes (articles du panier)
  for(var i=0;i<posCart.length;i++){
    var l=posCart[i];
    var modeVente=(posPayMode==='credit')?'Liquide':mode;
    var body={client_id:cid,type:'debit',motif:l.nom,quantite:l.qty,unite:l.unite,prix_unitaire:l.prix,mode_paiement:modeVente,notes:(posPayMode==='cash'?'[CAISSE PAYE] ':'[CAISSE CREDIT] ')+'Vente caisse',frais_deduits:0,compte:'euro'};
    try{var r=await api('/api/transactions',{method:'POST',body:body});if(r&&r.ok)ok++;else fail++;}catch(e){fail++;}
  }
  // 2) Remboursement de dette (credit)
  if(remb>0){
    var absorbe=document.getElementById('posRembFrais')?(document.getElementById('posRembFrais').checked?1:0):1;
    var bodyR={client_id:cid,type:'credit',motif:'Remboursement',quantite:1,unite:'piece',prix_unitaire:remb,mode_paiement:mode,notes:'[CAISSE] Remboursement dette',frais_deduits:absorbe,compte:'euro'};
    try{var r2=await api('/api/transactions',{method:'POST',body:bodyR});if(r2&&r2.ok)ok++;else fail++;}catch(e){fail++;}
  }
  btn.disabled=false;btn.textContent='Encaisser';
  if(fail===0){
    var msg=[];
    if(venteTotal>0)msg.push('vente '+venteTotal.toFixed(2)+' EUR');
    if(remb>0)msg.push('remboursement '+remb.toFixed(2)+' EUR');
    notify('Encaisse : '+msg.join(' + '));
    posCart=[];renderPosCart();
    var ri=document.getElementById('posRemb');if(ri)ri.value='0';
    onPosClientChange(); // recharge la dette a jour
    if(typeof loadDashboard==='function')loadDashboard();
    if(typeof loadTransactions==='function')loadTransactions();
  }else{
    notify(ok+' ok, '+fail+' echec(s)','error');
  }
}
</script>
"""
pos=html.rfind("</script>")
at=pos+len("</script>")
html=html[:at]+"\n"+NEWJS+html[at:]
print("4) JS caisse v2 injecte (dette + remboursement + encaissement combine)")

no=html.count("<script>");nc=html.count("</script>")
print("Balises script: %d / %d" % (no,nc))

with io.open(p,"w",encoding="utf-8") as f:
    f.write(html)
print("")
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
