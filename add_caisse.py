#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_caisse.py - Ajoute un ecran CAISSE (point de vente) :
  - Client obligatoire en haut
  - Catalogue cliquable a gauche -> ajoute au panier
  - Panier a droite, quantites ajustables, total live
  - Encaissement : comptant (paye) ou credit (ajout dette)
  - Chaque ligne -> POST /api/transactions (type debit)
Insertion sure (apres </script>). Idempotent.
Usage (dans le dossier projet): python add_caisse.py
"""
import io, re

p = "web/index.html"
with io.open(p, "r", encoding="utf-8") as f:
    html = f.read()
orig = len(html)

# ── 1) CSS caisse ──────────────────────────────────────────────────
CSS = """
/* ===== CAISSE ===== */
.pos-wrap{display:grid;grid-template-columns:1fr 380px;gap:18px;height:calc(100vh - 140px)}
.pos-left{display:flex;flex-direction:column;gap:12px;min-height:0}
.pos-topbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.pos-client{flex:1;min-width:200px;padding:12px 14px;border-radius:var(--radius2);border:1px solid var(--border2);background:var(--bg3);color:var(--text);font-size:15px;font-family:'Outfit',sans-serif}
.pos-search{padding:10px 14px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:'Outfit',sans-serif;width:220px}
.pos-grid{flex:1;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;align-content:start;padding-right:6px}
.pos-prod{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px;cursor:pointer;transition:all .15s;display:flex;flex-direction:column;gap:8px;min-height:96px;justify-content:space-between}
.pos-prod:hover{border-color:var(--gold);transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.25)}
.pos-prod:active{transform:scale(.97)}
.pos-prod .pname{font-size:14px;font-weight:600;color:var(--text);line-height:1.2}
.pos-prod .pprice{font-size:16px;font-weight:700;color:var(--green);font-family:'DM Mono',monospace}
.pos-prod .pcat{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:1px}
.pos-cart{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);display:flex;flex-direction:column;min-height:0}
.pos-cart-head{padding:14px 16px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--gold2)}
.pos-cart-body{flex:1;overflow-y:auto;padding:8px}
.pos-line{display:flex;align-items:center;gap:8px;padding:10px;border-radius:var(--radius2);transition:background .15s}
.pos-line:hover{background:var(--bg3)}
.pos-line .lname{flex:1;font-size:13px;color:var(--text)}
.pos-line .lqty{display:flex;align-items:center;gap:4px}
.pos-line .lqty button{width:26px;height:26px;border-radius:6px;border:1px solid var(--border);background:var(--bg3);color:var(--text);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center}
.pos-line .lqty input{width:42px;text-align:center;padding:4px;border-radius:6px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px}
.pos-line .lsub{width:64px;text-align:right;font-family:'DM Mono',monospace;font-size:13px;color:var(--green)}
.pos-line .ldel{width:24px;height:24px;border:none;background:none;color:var(--text3);cursor:pointer;font-size:16px}
.pos-line .ldel:hover{color:var(--red)}
.pos-cart-foot{border-top:1px solid var(--border);padding:14px 16px;display:flex;flex-direction:column;gap:12px}
.pos-total{display:flex;justify-content:space-between;align-items:center;font-size:22px;font-weight:700}
.pos-total .amt{color:var(--gold2);font-family:'DM Mono',monospace}
.pos-pay{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.pos-paybtn{padding:14px;border-radius:var(--radius2);border:1px solid var(--border2);background:var(--bg3);color:var(--text);font-size:14px;font-weight:600;cursor:pointer;transition:all .15s}
.pos-paybtn.active{border-color:var(--gold);background:linear-gradient(135deg,rgba(201,168,76,.2),rgba(201,168,76,.05));color:var(--gold2)}
.pos-mode{padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:'Outfit',sans-serif;width:100%}
.pos-cashout{padding:16px;border-radius:var(--radius2);border:none;background:linear-gradient(135deg,var(--green),#0f9d58);color:#fff;font-size:16px;font-weight:700;cursor:pointer;transition:all .15s}
.pos-cashout:hover{filter:brightness(1.1)}
.pos-cashout:disabled{opacity:.5;cursor:not-allowed}
.pos-empty{text-align:center;color:var(--text3);padding:40px 20px;font-size:13px}
"""
if "/* ===== CAISSE ===== */" not in html:
    html = html.replace("</style>", CSS + "\n</style>", 1)
    print("1) CSS caisse ajoute")
else:
    print("1) CSS caisse deja present")

# ── 2) Entree sidebar (en 1er, avant Tableau de bord) ──────────────
NAV = '    <div class="nav-item" onclick="goPage(\'caisse\',this)"><span class="nav-icon">CAISSE</span> Caisse</div>\n'
if "goPage('caisse'" not in html:
    m = re.search(r'(<div class="nav-item active" onclick="goPage\(\'dashboard\',this\)">)', html)
    if m:
        html = html.replace(m.group(1), NAV + "    " + m.group(1), 1)
        print("2) Entree Caisse ajoutee en haut de la sidebar")
    else:
        # fallback : avant 1er nav-item
        m2 = re.search(r'(<div class="nav-item[^"]*" onclick="goPage\()', html)
        if m2:
            html = html.replace(m2.group(1), NAV.strip() + "\n    " + m2.group(1), 1)
            print("2) Entree Caisse ajoutee (fallback)")
        else:
            print("2) ATTENTION ancre sidebar introuvable")
else:
    print("2) Entree Caisse deja presente")

# ── 3) TITLES ──────────────────────────────────────────────────────
if "caisse:'Caisse'" not in html:
    m = re.search(r"(const TITLES\s*=\s*\{)", html)
    if m:
        html = html.replace(m.group(1), m.group(1) + "caisse:'Caisse',", 1)
        print("3) TITLES : caisse ajoute")
    else:
        print("3) ATTENTION const TITLES introuvable")
else:
    print("3) TITLES deja a jour")

# ── 4) goPage -> initCaisse ────────────────────────────────────────
if "initCaisse()" not in html:
    # accrocher apres le if catalogue (deja ajoute par patch2) ou recap
    for anchor in ["if(name==='catalogue'){loadCatalogue();}", "if(name==='recap')initRecap();"]:
        if anchor in html:
            html = html.replace(anchor, anchor + "\n  if(name==='caisse'){initCaisse();}", 1)
            print("4) goPage initialise la caisse")
            break
    else:
        print("4) ATTENTION ancre goPage introuvable")
else:
    print("4) goPage caisse deja ok")

# ── 5) Page HTML caisse (inseree avant <!-- RAPPELS --> comme patch2) ─
PAGE = """
      <div class="page" id="pg-caisse">
        <div class="pos-wrap">
          <div class="pos-left">
            <div class="pos-topbar">
              <select class="pos-client" id="posClient"><option value="">-- Choisir un client (obligatoire) --</option></select>
              <input class="pos-search" id="posSearch" placeholder="Rechercher un article..." oninput="renderPosGrid(this.value)">
            </div>
            <div class="pos-grid" id="posGrid"></div>
          </div>
          <div class="pos-cart">
            <div class="pos-cart-head">Panier</div>
            <div class="pos-cart-body" id="posCartBody"><div class="pos-empty">Cliquez sur des articles pour les ajouter</div></div>
            <div class="pos-cart-foot">
              <div class="pos-total"><span style="font-size:14px;color:var(--text3);font-weight:500">TOTAL</span><span class="amt" id="posTotal">0.00 EUR</span></div>
              <div class="pos-pay">
                <button class="pos-paybtn active" id="posPayCash" onclick="setPosPay('cash')">Comptant (paye)</button>
                <button class="pos-paybtn" id="posPayCredit" onclick="setPosPay('credit')">A credit (dette)</button>
              </div>
              <select class="pos-mode" id="posMode">
                <option value="Liquide">Liquide</option>
                <option value="Virement">Virement</option>
                <option value="PCS">PCS</option>
                <option value="Paysafecard">Paysafecard</option>
                <option value="WesternUnion">Western Union</option>
              </select>
              <button class="pos-cashout" id="posCashout" onclick="posEncaisser()">Encaisser</button>
            </div>
          </div>
        </div>
      </div>
"""
if 'id="pg-caisse"' not in html:
    placed = False
    for anchor in ['<!-- RAPPELS -->', 'id="pg-catalogue"', 'id="pg-rappels"']:
        idx = html.find(anchor)
        if idx != -1:
            ds = html.rfind('<div class="page"', 0, idx)
            if ds == -1: ds = idx
            html = html[:ds] + PAGE + "\n      " + html[ds:]
            placed = True
            print("5) Page caisse inseree (ancre %s)" % anchor)
            break
    if not placed:
        print("5) ATTENTION ancre page introuvable")
else:
    print("5) Page caisse deja presente")

# ── 6) JS caisse (apres dernier </script>) ─────────────────────────
JS = r"""
<script>
// ===== CAISSE (POS) =====
var posCart = [];      // [{id,nom,prix,qty,unite}]
var posPayMode = 'cash';

function initCaisse(){
  // remplir clients
  var sel = document.getElementById('posClient');
  if(sel){
    var prev = sel.value;
    sel.innerHTML = '<option value="">-- Choisir un client (obligatoire) --</option>';
    (clientsCache||[]).forEach(function(c){
      var o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);
    });
    if(prev) sel.value=prev;
  }
  // s'assurer que le catalogue est charge
  if(!catalogueCache || !catalogueCache.length){ loadCatalogue().then(function(){renderPosGrid('');}); }
  else renderPosGrid('');
  renderPosCart();
  setPosPay('cash');
}

function renderPosGrid(filter){
  filter=(filter||'').toLowerCase();
  var grid=document.getElementById('posGrid');
  if(!grid)return;
  grid.innerHTML='';
  var list=(catalogueCache||[]).filter(function(it){
    return !filter || (it.nom+' '+it.categorie).toLowerCase().includes(filter);
  });
  if(!list.length){grid.innerHTML='<div class="pos-empty" style="grid-column:1/-1">Aucun article. Ajoutez-en dans le Catalogue.</div>';return;}
  list.forEach(function(it){
    var u=it.unite==='gramme'?'g':it.unite==='litre'?'L':'pcs';
    var card=document.createElement('div');
    card.className='pos-prod';
    card.onclick=function(){addToCart(it);};
    card.innerHTML='<div class="pcat">'+it.categorie+'</div><div class="pname">'+it.nom+'</div><div class="pprice">'+parseFloat(it.prix_vente).toFixed(2)+' EUR<span style="font-size:10px;color:var(--text3)"> /'+u+'</span></div>';
    grid.appendChild(card);
  });
}

function addToCart(it){
  var line=posCart.find(function(l){return l.id===it.id;});
  if(line){line.qty+=1;}
  else{posCart.push({id:it.id,nom:it.nom,prix:parseFloat(it.prix_vente)||0,qty:1,unite:it.unite||'piece'});}
  renderPosCart();
}

function posChangeQty(id,delta){
  var line=posCart.find(function(l){return l.id===id;});
  if(!line)return;
  line.qty=Math.max(0,Math.round((line.qty+delta)*100)/100);
  if(line.qty<=0){posCart=posCart.filter(function(l){return l.id!==id;});}
  renderPosCart();
}
function posSetQty(id,val){
  var line=posCart.find(function(l){return l.id===id;});
  if(!line)return;
  line.qty=Math.max(0,parseFloat(val)||0);
  renderPosCart();
}
function posRemove(id){posCart=posCart.filter(function(l){return l.id!==id;});renderPosCart();}

function renderPosCart(){
  var body=document.getElementById('posCartBody');
  if(!body)return;
  if(!posCart.length){
    body.innerHTML='<div class="pos-empty">Cliquez sur des articles pour les ajouter</div>';
    document.getElementById('posTotal').textContent='0.00 EUR';
    document.getElementById('posCashout').disabled=true;
    return;
  }
  body.innerHTML='';
  var total=0;
  posCart.forEach(function(l){
    var sub=l.prix*l.qty;total+=sub;
    var row=document.createElement('div');
    row.className='pos-line';
    row.innerHTML='<div class="lname">'+l.nom+'<br><span style="font-size:11px;color:var(--text3)">'+l.prix.toFixed(2)+' EUR</span></div>'
      +'<div class="lqty"><button onclick="posChangeQty('+l.id+',-1)">-</button>'
      +'<input type="number" value="'+l.qty+'" min="0" step="1" onchange="posSetQty('+l.id+',this.value)">'
      +'<button onclick="posChangeQty('+l.id+',1)">+</button></div>'
      +'<div class="lsub">'+sub.toFixed(2)+'</div>'
      +'<button class="ldel" onclick="posRemove('+l.id+')">x</button>';
    body.appendChild(row);
  });
  document.getElementById('posTotal').textContent=total.toFixed(2)+' EUR';
  document.getElementById('posCashout').disabled=false;
}

function setPosPay(mode){
  posPayMode=mode;
  document.getElementById('posPayCash').classList.toggle('active',mode==='cash');
  document.getElementById('posPayCredit').classList.toggle('active',mode==='credit');
}

async function posEncaisser(){
  var cid=parseInt(document.getElementById('posClient').value);
  if(!cid){notify('Choisis un client','error');return;}
  if(!posCart.length){notify('Panier vide','error');return;}
  var mode=document.getElementById('posMode').value;
  var btn=document.getElementById('posCashout');
  btn.disabled=true;btn.textContent='Encaissement...';
  var ok=0,fail=0;
  for(var i=0;i<posCart.length;i++){
    var l=posCart[i];
    var body={client_id:cid,type:'debit',motif:l.nom,quantite:l.qty,unite:l.unite,
      prix_unitaire:l.prix,mode_paiement:mode,
      notes:(posPayMode==='cash'?'[CAISSE PAYE] ':'[CAISSE CREDIT] ')+'Vente caisse',
      frais_deduits:0,compte:'euro'};
    try{var res=await api('/api/transactions',{method:'POST',body:body});if(res&&res.ok)ok++;else fail++;}
    catch(e){fail++;}
  }
  btn.disabled=false;btn.textContent='Encaisser';
  if(fail===0){
    notify(ok+' article(s) encaisse(s) - '+(posPayMode==='cash'?'paye comptant':'ajoute a la dette'));
    posCart=[];renderPosCart();
    if(typeof loadDashboard==='function')loadDashboard();
    if(typeof loadTransactions==='function')loadTransactions();
  }else{
    notify(ok+' ok, '+fail+' echec(s)','error');
  }
}
</script>
"""
if "function initCaisse" not in html:
    pos=html.rfind("</script>")
    if pos!=-1:
        at=pos+len("</script>")
        html=html[:at]+"\n"+JS+html[at:]
        print("6) JS caisse insere apres le dernier </script>")
    else:
        print("6) ERREUR </script> introuvable")
else:
    print("6) JS caisse deja present")

with io.open(p,"w",encoding="utf-8") as f:
    f.write(html)

print("")
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
print("Ecran Caisse pret : Caisse dans la sidebar.")
