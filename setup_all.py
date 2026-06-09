#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_all.py - Reapplique TOUT proprement depuis le backup vierge.
A lancer dans le dossier du projet : python setup_all.py

Restaure web/index.html depuis le backup vierge, puis applique dans l'ordre :
  1. Catalogue + Factures (pages, JS, nav, modal)
  2. Caisse (POS)
  3. Categories (table + Parametres)
  4. Sidebar defilable
Le selecteur catalogue dans le modal transaction + date creation sont gardes
cote backend (db.py/api.py deja patches lors des etapes precedentes).

IMPORTANT : ce script ne touche QUE web/index.html (le frontend).
db.py et api.py gardent leurs corrections deja faites (frais, date, catalogue,
factures, categories). On ne les retouche pas ici.
"""
import io, os, re, glob, sys

PATH = "web/index.html"

# 1) Trouver le backup vierge le plus ancien (bak_...)
baks = sorted(glob.glob("web/index.html.bak_*"))
if not baks:
    print("ERREUR : aucun backup web/index.html.bak_* trouve.")
    sys.exit(1)
backup = baks[0]  # le plus ancien = le vierge
print("Backup vierge utilise : %s" % backup)

# Sauvegarde de securite de l'etat actuel (au cas ou)
if os.path.exists(PATH):
    import shutil
    shutil.copy2(PATH, PATH + ".avant_setup_all")
    print("Etat actuel sauve : %s" % (PATH + ".avant_setup_all"))

# Restaurer le vierge
with io.open(backup, "r", encoding="utf-8") as f:
    html = f.read()
print("Repart du HTML vierge (%d caracteres)" % len(html))

orig = len(html)

# ════════════════════════════════════════════════════════════════
# CSS global (catalogue + caisse + categories)
# ════════════════════════════════════════════════════════════════
CSS = """
.catalogue-search{padding:8px 14px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:'Outfit',sans-serif;width:240px;transition:all .2s}
.catalogue-search:focus{outline:none;border-color:var(--gold);width:300px}
.cat-select-bar{background:var(--bg3);border:1px solid var(--border2);border-radius:var(--radius2);padding:8px 12px;width:100%;font-size:14px;font-family:'Outfit',sans-serif;color:var(--gold2);cursor:pointer;margin-bottom:6px}
.cat-select-bar:focus{outline:none;border-color:var(--gold)}
.catalogue-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:18px;transition:all .2s;cursor:pointer}
.catalogue-card:hover{border-color:var(--gold);transform:translateY(-2px)}
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
.pos-line{display:flex;align-items:center;gap:8px;padding:10px;border-radius:var(--radius2)}
.pos-line:hover{background:var(--bg3)}
.pos-line .lname{flex:1;font-size:13px;color:var(--text)}
.pos-line .lqty{display:flex;align-items:center;gap:4px}
.pos-line .lqty button{width:26px;height:26px;border-radius:6px;border:1px solid var(--border);background:var(--bg3);color:var(--text);cursor:pointer;font-size:15px}
.pos-line .lqty input{width:42px;text-align:center;padding:4px;border-radius:6px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px}
.pos-line .lsub{width:64px;text-align:right;font-family:'DM Mono',monospace;font-size:13px;color:var(--green)}
.pos-line .ldel{width:24px;height:24px;border:none;background:none;color:var(--text3);cursor:pointer;font-size:16px}
.pos-line .ldel:hover{color:var(--red)}
.pos-cart-foot{border-top:1px solid var(--border);padding:14px 16px;display:flex;flex-direction:column;gap:12px}
.pos-total{display:flex;justify-content:space-between;align-items:center;font-size:22px;font-weight:700}
.pos-total .amt{color:var(--gold2);font-family:'DM Mono',monospace}
.pos-pay{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.pos-paybtn{padding:14px;border-radius:var(--radius2);border:1px solid var(--border2);background:var(--bg3);color:var(--text);font-size:14px;font-weight:600;cursor:pointer}
.pos-paybtn.active{border-color:var(--gold);background:linear-gradient(135deg,rgba(201,168,76,.2),rgba(201,168,76,.05));color:var(--gold2)}
.pos-mode{padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:'Outfit',sans-serif;width:100%}
.pos-cashout{padding:16px;border-radius:var(--radius2);border:none;background:linear-gradient(135deg,var(--green),#0f9d58);color:#fff;font-size:16px;font-weight:700;cursor:pointer}
.pos-cashout:hover{filter:brightness(1.1)}
.pos-cashout:disabled{opacity:.5;cursor:not-allowed}
.pos-empty{text-align:center;color:var(--text3);padding:40px 20px;font-size:13px}
"""
html = html.replace("</style>", CSS + "\n</style>", 1)
print("CSS ajoute")

# ════════════════════════════════════════════════════════════════
# SIDEBAR defilable
# ════════════════════════════════════════════════════════════════
html = html.replace(
  ".sidebar{width:224px;min-width:224px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:20px 0;position:relative;overflow:hidden}",
  ".sidebar{width:224px;min-width:224px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:20px 0;position:relative;overflow-y:auto;overflow-x:hidden}"
)
print("Sidebar defilable")

# ════════════════════════════════════════════════════════════════
# NAV sidebar : Caisse (haut), Catalogue, Factures
# ════════════════════════════════════════════════════════════════
m = re.search(r'(<div class="nav-item active" onclick="goPage\(\'dashboard\',this\)">)', html)
if m:
    NAV_TOP = '<div class="nav-item" onclick="goPage(\'caisse\',this)"><span class="nav-icon">🛒</span> Caisse</div>\n    '
    html = html.replace(m.group(1), NAV_TOP + m.group(1), 1)
# Catalogue + Factures avant un nav existant (settings/recap/soldes)
NAV2 = '    <div class="nav-item" onclick="goPage(\'catalogue\',this)"><span class="nav-icon">📦</span> Catalogue</div>\n    <div class="nav-item" onclick="goPage(\'factures\',this)"><span class="nav-icon">🧾</span> Factures &amp; Bons</div>\n'
for a in ["goPage('settings'","goPage('recap'","goPage('soldes'"]:
    idx = html.find(a)
    if idx != -1:
        ds = html.rfind('<div class="nav-item"', 0, idx)
        if ds != -1:
            html = html[:ds] + NAV2 + html[ds:]
            break
print("Nav sidebar (Caisse + Catalogue + Factures)")

# ════════════════════════════════════════════════════════════════
# TITLES
# ════════════════════════════════════════════════════════════════
m = re.search(r"(const TITLES\s*=\s*\{)", html)
if m:
    html = html.replace(m.group(1), m.group(1) + "caisse:'Caisse',catalogue:'Catalogue Produits',factures:'Factures & Bons',", 1)
print("TITLES")

# ════════════════════════════════════════════════════════════════
# goPage : ajouter les cas
# ════════════════════════════════════════════════════════════════
m = re.search(r"(if\s*\(\s*name\s*===\s*'recap'\s*\)\s*initRecap\(\);)", html)
if m:
    add = m.group(1) + "\n  if(name==='catalogue'){loadCatalogue();}\n  if(name==='caisse'){initCaisse();}\n  if(name==='factures'){initFactures();}"
    html = html.replace(m.group(1), add, 1)
print("goPage cas ajoutes")

# ════════════════════════════════════════════════════════════════
# PAGES HTML (catalogue, factures, caisse) avant <!-- RAPPELS -->
# ════════════════════════════════════════════════════════════════
PAGES = """
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
                <option value="Liquide">Liquide</option><option value="Virement">Virement</option><option value="PCS">PCS</option><option value="Paysafecard">Paysafecard</option><option value="WesternUnion">Western Union</option>
              </select>
              <button class="pos-cashout" id="posCashout" onclick="posEncaisser()">Encaisser</button>
            </div>
          </div>
        </div>
      </div>

      <div class="page" id="pg-catalogue">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:4px">
          <button class="btn primary" onclick="openAddCatalogue()">+ Nouvel article</button>
          <input class="catalogue-search" placeholder="Rechercher..." oninput="searchCatalogue(this.value)">
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px" id="catalogueGrid"><div class="loading"><div class="spinner"></div> Chargement...</div></div>
      </div>

      <div class="page" id="pg-factures">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <select id="facturesClientFilter" onchange="renderFactures(0)" style="padding:8px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:Outfit,sans-serif;min-width:180px"><option value="">Tous les clients</option></select>
          <select id="facturesTypeFilter" onchange="renderFactures(0)" style="padding:8px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:Outfit,sans-serif"><option value="">Tous types</option><option value="vente">Factures vente</option><option value="remboursement">Bons remboursement</option></select>
          <div id="facturesStats" style="font-size:13px;color:var(--text3)"></div>
        </div>
        <div class="table-wrap"><div class="table-header"><span>Documents generes automatiquement</span></div>
          <table><thead><tr><th>N Document</th><th>Date</th><th>Client</th><th>Type</th><th style="text-align:right">Montant</th><th>Actions</th></tr></thead>
          <tbody id="facturesTbody"><tr><td colspan="6"><div class="loading"><div class="spinner"></div></div></td></tr></tbody></table>
        </div>
      </div>
"""
placed=False
for anchor in ['<!-- RAPPELS -->','id="pg-rappels"','id="pg-settings"']:
    idx=html.find(anchor)
    if idx!=-1:
        ds=html.rfind('<div class="page"',0,idx)
        if ds==-1: ds=idx
        html=html[:ds]+PAGES+"\n      "+html[ds:]
        placed=True
        break
print("Pages HTML inserees (%s)" % ("ok" if placed else "ATTENTION ancre absente"))

# ════════════════════════════════════════════════════════════════
# Categories dans Parametres (carte avant Taux de frais)
# ════════════════════════════════════════════════════════════════
anchor = '<div class="card-title">💸 Taux de frais</div>'
if anchor in html:
    idx=html.find(anchor)
    card_start=html.rfind('<div class="card"',0,idx)
    if card_start!=-1:
        CARD = ('<div class="card">\n'
            '            <div class="card-title">Categories du catalogue</div>\n'
            '            <div id="catCategoriesList" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px"></div>\n'
            '            <div style="display:flex;gap:8px">\n'
            '              <input type="text" id="newCategoryName" placeholder="Nouvelle categorie..." style="flex:1;padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif" onkeydown="if(event.key===\'Enter\')addCategoryUI()">\n'
            '              <button class="btn primary" onclick="addCategoryUI()">+ Ajouter</button>\n'
            '            </div>\n'
            '          </div>\n          ')
        html=html[:card_start]+CARD+html[card_start:]
        print("Carte Categories ajoutee dans Parametres")
    else:
        print("ATTENTION conteneur carte frais introuvable")
else:
    print("ATTENTION titre Taux de frais introuvable")

# Datalist categorie pour le modal catalogue (sera rempli par JS)
# (le modal lui-meme est ajoute plus bas)

# ════════════════════════════════════════════════════════════════
# MODAL catalogue (apres dernier </script>) + JS complet
# ════════════════════════════════════════════════════════════════
MODAL = """
<div class="modal-bg" id="modalCatalogue" onclick="if(event.target===this)this.classList.remove('open')">
  <div class="modal" style="max-width:520px">
    <input type="hidden" id="catId">
    <div class="modal-title" id="catModalTitle">Nouvel article</div>
    <div class="modal-sub">Ajouter au catalogue produits</div>
    <div class="form-grid">
      <div class="form-group full"><label>Nom de l'article *</label><input type="text" id="catNom" placeholder="Ex: Tabac x1..."></div>
      <div class="form-group"><label>Categorie</label><input type="text" id="catCategorie" list="catCategorieList" placeholder="Categorie..." style="padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif;width:100%"><datalist id="catCategorieList"></datalist></div>
      <div class="form-group"><label>Unite</label><select id="catUnite" style="padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif"><option value="piece">Piece(s)</option><option value="gramme">Gramme(s)</option><option value="litre">Litre(s)</option><option value="paquet">Paquet(s)</option></select></div>
      <div class="form-group"><label>Prix de vente</label><input type="number" id="catPrixVente" value="0" step="0.5" min="0" style="font-size:18px;font-weight:600;color:var(--green)"></div>
      <div class="form-group"><label>Prix d'achat</label><input type="number" id="catPrixAchat" value="0" step="0.5" min="0" style="font-size:18px;font-weight:600;color:var(--red)"></div>
      <div class="form-group"><label>Stock minimum</label><input type="number" id="catStockMin" value="0" step="0.5" min="0"></div>
      <div class="form-group full"><label>Description</label><input type="text" id="catDescription" placeholder="Description courte..."></div>
    </div>
    <div class="modal-actions">
      <button class="btn danger" id="btnDeleteCat" style="margin-right:auto;display:none" onclick="deleteCatalogueItem(parseInt(document.getElementById('catId').value))">Supprimer</button>
      <button class="btn-cancel" onclick="document.getElementById('modalCatalogue').classList.remove('open')">Annuler</button>
      <button class="btn-save" onclick="saveCatalogueItem()">Enregistrer</button>
    </div>
  </div>
</div>
"""

JS = r"""
<script>
// ===== CATALOGUE =====
var catalogueCache = [];
async function loadCatalogue(){var res=await api('/api/catalogue');if(!res||!res.ok)return;catalogueCache=res.data;renderCatalogue();}
function renderCatalogue(){var grid=document.getElementById('catalogueGrid');if(!grid)return;grid.innerHTML='';if(!catalogueCache.length){grid.innerHTML='<div style="grid-column:1/-1;text-align:center;color:var(--text3);padding:40px">Aucun article. Cliquez sur <strong style="color:var(--gold2)">+ Nouvel article</strong>.</div>';return;}
var cats={};catalogueCache.forEach(function(it){var c=it.categorie||'General';if(!cats[c])cats[c]=[];cats[c].push(it);});
Object.keys(cats).sort().forEach(function(cat){var d=document.createElement('div');d.style.cssText='grid-column:1/-1;margin-top:8px';d.innerHTML='<div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)">'+cat+'</div>';grid.appendChild(d);
cats[cat].forEach(function(it){var card=document.createElement('div');card.className='catalogue-card';var u=it.unite==='gramme'?'g':it.unite==='litre'?'L':'pcs';var marge=(parseFloat(it.prix_vente||0)-parseFloat(it.prix_achat||0));var mc=marge>=0?'var(--green)':'var(--red)';
card.innerHTML='<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px"><div style="font-size:15px;font-weight:600;color:var(--text)">'+it.nom+'</div><span style="font-size:10px;background:var(--bg4);border:1px solid var(--border);border-radius:20px;padding:2px 8px;color:var(--text3)">'+it.categorie+'</span></div>'+(it.description?'<div style="font-size:12px;color:var(--text3);margin-bottom:10px">'+it.description+'</div>':'')+'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:12px"><div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3)">VENTE</div><div style="font-size:15px;font-weight:700;color:var(--green);font-family:DM Mono,monospace">'+parseFloat(it.prix_vente).toFixed(2)+'</div><div style="font-size:10px;color:var(--text3)">/'+u+'</div></div><div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3)">ACHAT</div><div style="font-size:15px;font-weight:700;color:var(--red);font-family:DM Mono,monospace">'+parseFloat(it.prix_achat).toFixed(2)+'</div><div style="font-size:10px;color:var(--text3)">/'+u+'</div></div><div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3)">MARGE</div><div style="font-size:15px;font-weight:700;color:'+mc+';font-family:DM Mono,monospace">'+marge.toFixed(2)+'</div><div style="font-size:10px;color:var(--text3)">/'+u+'</div></div></div><div style="display:flex;gap:8px"><button class="btn primary" style="flex:1;font-size:12px;padding:7px" onclick="selectArticleCatalogue('+it.id+')">+ Vendre</button><button class="btn" style="font-size:12px;padding:7px 10px" onclick="openEditCatalogue('+it.id+')">Edit</button><button class="btn danger" style="font-size:12px;padding:7px 10px" onclick="deleteCatalogueItem('+it.id+')">X</button></div>';
grid.appendChild(card);});});}
function selectArticleCatalogue(id){var it=catalogueCache.find(function(i){return i.id===id;});if(!it)return;goPage('caisse',document.querySelector('[onclick*="goPage(\'caisse\'"]'));setTimeout(function(){addToCart(it);},150);}
function openAddCatalogue(){document.getElementById('catId').value='';document.getElementById('catNom').value='';document.getElementById('catCategorie').value='General';document.getElementById('catDescription').value='';document.getElementById('catPrixVente').value='0';document.getElementById('catPrixAchat').value='0';document.getElementById('catUnite').value='piece';document.getElementById('catStockMin').value='0';document.getElementById('catModalTitle').textContent='Nouvel article';document.getElementById('btnDeleteCat').style.display='none';document.getElementById('modalCatalogue').classList.add('open');}
function openEditCatalogue(id){var it=catalogueCache.find(function(i){return i.id===id;});if(!it)return;document.getElementById('catId').value=id;document.getElementById('catNom').value=it.nom;document.getElementById('catCategorie').value=it.categorie||'General';document.getElementById('catDescription').value=it.description||'';document.getElementById('catPrixVente').value=parseFloat(it.prix_vente).toFixed(2);document.getElementById('catPrixAchat').value=parseFloat(it.prix_achat).toFixed(2);document.getElementById('catUnite').value=it.unite||'piece';document.getElementById('catStockMin').value=parseFloat(it.stock_min||0).toFixed(1);document.getElementById('catModalTitle').textContent='Modifier l article';document.getElementById('btnDeleteCat').style.display='inline-flex';document.getElementById('modalCatalogue').classList.add('open');}
async function saveCatalogueItem(){var nom=document.getElementById('catNom').value.trim();if(!nom){notify('Nom requis','error');return;}var id=document.getElementById('catId').value;var body={nom:nom,categorie:document.getElementById('catCategorie').value||'General',description:document.getElementById('catDescription').value,prix_vente:parseFloat(document.getElementById('catPrixVente').value)||0,prix_achat:parseFloat(document.getElementById('catPrixAchat').value)||0,unite:document.getElementById('catUnite').value,stock_min:parseFloat(document.getElementById('catStockMin').value)||0};var res=id?await api('/api/catalogue/'+id,{method:'PUT',body:body}):await api('/api/catalogue',{method:'POST',body:body});if(res&&res.ok){document.getElementById('modalCatalogue').classList.remove('open');notify(id?'Article modifie':'Article cree');await loadCatalogue();}else notify(res&&res.error?res.error:'Erreur','error');}
async function deleteCatalogueItem(id){var it=catalogueCache.find(function(i){return i.id===id;});if(!confirm('Supprimer cet article ?'))return;document.getElementById('modalCatalogue').classList.remove('open');await api('/api/catalogue/'+id,{method:'DELETE'});notify('Article supprime');await loadCatalogue();}
function searchCatalogue(v){v=(v||'').toLowerCase();document.querySelectorAll('.catalogue-card').forEach(function(c){c.style.display=c.textContent.toLowerCase().includes(v)?'':'none';});}
// ===== FACTURES =====
var facturesCache=[];
async function loadFactures(cid){var url='/api/factures'+(cid?('?client_id='+cid+'&limit=200'):'?limit=200');var res=await api(url);if(!res||!res.ok)return;facturesCache=res.data;renderFactures(cid||0);}
function renderFactures(cid){var tb=document.getElementById('facturesTbody');if(!tb)return;tb.innerHTML='';cid=cid||parseInt((document.getElementById('facturesClientFilter')||{}).value||0)||0;var list=cid?facturesCache.filter(function(f){return f.client_id===cid;}):facturesCache;var tf=(document.getElementById('facturesTypeFilter')||{}).value||'';if(tf)list=list.filter(function(f){return f.type===tf;});var nv=list.filter(function(f){return f.type==='vente';}).length;var nb=list.filter(function(f){return f.type==='remboursement';}).length;var tv=list.filter(function(f){return f.type==='vente';}).reduce(function(s,f){return s+parseFloat(f.montant_net||0);},0);var el=document.getElementById('facturesStats');if(el)el.innerHTML=list.length+' document(s) - <span style="color:var(--green)">'+nv+' FAC</span> - <span style="color:var(--gold2)">'+nb+' BON</span> - Total ventes: <strong style="color:var(--gold2)">'+tv.toFixed(2)+'</strong>';
if(!list.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:24px">Aucun document</td></tr>';return;}
list.forEach(function(f){var iv=f.type==='vente';var col=iv?'var(--green)':'var(--gold2)';var tr=document.createElement('tr');tr.innerHTML='<td style="font-family:DM Mono,monospace;font-size:12px;color:var(--gold2)">'+f.numero+'</td><td>'+fmtDate(f.date_creation)+'</td><td style="color:var(--text);font-weight:500">'+(f.client_nom||'-')+'</td><td><span class="badge '+(iv?'debit':'credit')+'">'+(iv?'Facture':'Bon remb.')+'</span></td><td class="mono" style="color:'+col+';font-weight:600;text-align:right">'+parseFloat(f.montant_net||0).toFixed(2)+'</td><td style="display:flex;gap:6px"><button class="btn primary" style="font-size:11px;padding:4px 10px" onclick="voirFacture('+f.id+')">Voir</button><button class="btn" style="font-size:11px;padding:4px 10px" onclick="imprimerFacture('+f.id+')">Imp</button><button class="btn danger" style="font-size:11px;padding:4px 8px" onclick="supprimerFacture('+f.id+')">X</button></td>';tb.appendChild(tr);});}
async function voirFacture(fid){var res=await fetch('/api/factures/'+fid+'/html',{headers:{'X-Session-Token':TOKEN}});if(!res.ok){notify('Introuvable','error');return;}var h=await res.text();var b=new Blob([h],{type:'text/html'});var u=URL.createObjectURL(b);var pf=document.getElementById('printFrame');if(pf){pf.src=u;document.getElementById('modalPrintPreview').classList.add('open');}else window.open(u,'_blank');}
async function imprimerFacture(fid){var res=await fetch('/api/factures/'+fid+'/html',{headers:{'X-Session-Token':TOKEN}});if(!res.ok){notify('Introuvable','error');return;}var h=await res.text();var b=new Blob([h],{type:'text/html'});var u=URL.createObjectURL(b);var pf=document.getElementById('printFrame');if(pf){pf.src=u;document.getElementById('modalPrintPreview').classList.add('open');pf.onload=function(){try{pf.contentWindow.print();}catch(e){}pf.onload=null;};}}
async function supprimerFacture(fid){if(!confirm('Supprimer ce document ?'))return;await api('/api/factures/'+fid,{method:'DELETE'});notify('Document supprime');facturesCache=facturesCache.filter(function(f){return f.id!==fid;});renderFactures(0);}
function initFactures(){var sel=document.getElementById('facturesClientFilter');if(sel){var prev=sel.value;sel.innerHTML='<option value="">Tous les clients</option>';clientsCache.forEach(function(c){var o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);});if(prev)sel.value=prev;}loadFactures(0);}
// ===== CAISSE =====
var posCart=[];var posPayMode='cash';
function initCaisse(){var sel=document.getElementById('posClient');if(sel){var prev=sel.value;sel.innerHTML='<option value="">-- Choisir un client (obligatoire) --</option>';(clientsCache||[]).forEach(function(c){var o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);});if(prev)sel.value=prev;}if(!catalogueCache||!catalogueCache.length){loadCatalogue().then(function(){renderPosGrid('');});}else renderPosGrid('');renderPosCart();setPosPay('cash');}
function renderPosGrid(filter){filter=(filter||'').toLowerCase();var grid=document.getElementById('posGrid');if(!grid)return;grid.innerHTML='';var list=(catalogueCache||[]).filter(function(it){return !filter||(it.nom+' '+it.categorie).toLowerCase().includes(filter);});if(!list.length){grid.innerHTML='<div class="pos-empty" style="grid-column:1/-1">Aucun article. Ajoutez-en dans le Catalogue.</div>';return;}list.forEach(function(it){var u=it.unite==='gramme'?'g':it.unite==='litre'?'L':'pcs';var card=document.createElement('div');card.className='pos-prod';card.onclick=function(){addToCart(it);};card.innerHTML='<div class="pcat">'+it.categorie+'</div><div class="pname">'+it.nom+'</div><div class="pprice">'+parseFloat(it.prix_vente).toFixed(2)+' EUR<span style="font-size:10px;color:var(--text3)"> /'+u+'</span></div>';grid.appendChild(card);});}
function addToCart(it){var line=posCart.find(function(l){return l.id===it.id;});if(line){line.qty+=1;}else{posCart.push({id:it.id,nom:it.nom,prix:parseFloat(it.prix_vente)||0,qty:1,unite:it.unite||'piece'});}renderPosCart();}
function posChangeQty(id,delta){var line=posCart.find(function(l){return l.id===id;});if(!line)return;line.qty=Math.max(0,Math.round((line.qty+delta)*100)/100);if(line.qty<=0){posCart=posCart.filter(function(l){return l.id!==id;});}renderPosCart();}
function posSetQty(id,val){var line=posCart.find(function(l){return l.id===id;});if(!line)return;line.qty=Math.max(0,parseFloat(val)||0);renderPosCart();}
function posRemove(id){posCart=posCart.filter(function(l){return l.id!==id;});renderPosCart();}
function renderPosCart(){var body=document.getElementById('posCartBody');if(!body)return;if(!posCart.length){body.innerHTML='<div class="pos-empty">Cliquez sur des articles pour les ajouter</div>';document.getElementById('posTotal').textContent='0.00 EUR';document.getElementById('posCashout').disabled=true;return;}body.innerHTML='';var total=0;posCart.forEach(function(l){var sub=l.prix*l.qty;total+=sub;var row=document.createElement('div');row.className='pos-line';row.innerHTML='<div class="lname">'+l.nom+'<br><span style="font-size:11px;color:var(--text3)">'+l.prix.toFixed(2)+' EUR</span></div><div class="lqty"><button onclick="posChangeQty('+l.id+',-1)">-</button><input type="number" value="'+l.qty+'" min="0" step="1" onchange="posSetQty('+l.id+',this.value)"><button onclick="posChangeQty('+l.id+',1)">+</button></div><div class="lsub">'+sub.toFixed(2)+'</div><button class="ldel" onclick="posRemove('+l.id+')">x</button>';body.appendChild(row);});document.getElementById('posTotal').textContent=total.toFixed(2)+' EUR';document.getElementById('posCashout').disabled=false;}
function setPosPay(mode){posPayMode=mode;document.getElementById('posPayCash').classList.toggle('active',mode==='cash');document.getElementById('posPayCredit').classList.toggle('active',mode==='credit');}
async function posEncaisser(){var cid=parseInt(document.getElementById('posClient').value);if(!cid){notify('Choisis un client','error');return;}if(!posCart.length){notify('Panier vide','error');return;}var mode=document.getElementById('posMode').value;var btn=document.getElementById('posCashout');btn.disabled=true;btn.textContent='Encaissement...';var ok=0,fail=0;for(var i=0;i<posCart.length;i++){var l=posCart[i];var body={client_id:cid,type:'debit',motif:l.nom,quantite:l.qty,unite:l.unite,prix_unitaire:l.prix,mode_paiement:mode,notes:(posPayMode==='cash'?'[CAISSE PAYE] ':'[CAISSE CREDIT] ')+'Vente caisse',frais_deduits:0,compte:'euro'};try{var res=await api('/api/transactions',{method:'POST',body:body});if(res&&res.ok)ok++;else fail++;}catch(e){fail++;}}btn.disabled=false;btn.textContent='Encaisser';if(fail===0){notify(ok+' article(s) encaisse(s) - '+(posPayMode==='cash'?'paye comptant':'ajoute a la dette'));posCart=[];renderPosCart();if(typeof loadDashboard==='function')loadDashboard();if(typeof loadTransactions==='function')loadTransactions();}else{notify(ok+' ok, '+fail+' echec(s)','error');}}
// ===== CATEGORIES =====
var categoriesCache=[];
async function loadCategories(){var res=await api('/api/categories');if(!res||!res.ok)return;categoriesCache=res.data;renderCategoriesList();fillCategorySelects();}
function renderCategoriesList(){var box=document.getElementById('catCategoriesList');if(!box)return;box.innerHTML='';if(!categoriesCache.length){box.innerHTML='<div style="color:var(--text3);font-size:13px">Aucune categorie</div>';return;}categoriesCache.forEach(function(c){var row=document.createElement('div');row.style.cssText='display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius2)';row.innerHTML='<span style="font-size:14px;color:var(--text)">'+c.nom+'</span>'+'<button class="btn danger" style="font-size:11px;padding:4px 10px" data-catid="'+c.id+'" data-catnom="'+c.nom+'" onclick="deleteCategoryUI(this.dataset.catid,this.dataset.catnom)">Supprimer</button>';box.appendChild(row);});}
function fillCategorySelects(){var dl=document.getElementById('catCategorieList');if(dl){dl.innerHTML='';categoriesCache.forEach(function(c){var o=document.createElement('option');o.value=c.nom;dl.appendChild(o);});}}
async function addCategoryUI(){var inp=document.getElementById('newCategoryName');var nom=(inp.value||'').trim();if(!nom){notify('Nom requis','error');return;}var res=await api('/api/categories',{method:'POST',body:{nom:nom}});if(res&&res.ok){inp.value='';notify('Categorie ajoutee');await loadCategories();}else notify(res&&res.error?res.error:'Erreur','error');}
async function deleteCategoryUI(id,nom){if(!confirm('Supprimer la categorie "'+nom+'" ?'))return;var res=await api('/api/categories/'+id,{method:'DELETE'});if(res&&res.ok){notify('Categorie supprimee');await loadCategories();}else notify(res&&res.error?res.error:'Suppression impossible','error');}
// hook init
(function(){var _oldInit=typeof initApp==='function'?initApp:null;window.initApp=function(){if(_oldInit)_oldInit();try{loadCatalogue();}catch(e){}try{loadCategories();}catch(e){}};})();
</script>
"""

pos = html.rfind("</script>")
at = pos + len("</script>")
html = html[:at] + "\n" + MODAL + "\n" + JS + html[at:]
print("Modal catalogue + JS complet ajoutes")

# verif equilibre script
no = html.count("<script>"); nc = html.count("</script>")
print("Balises script : %d ouvrantes / %d fermantes" % (no, nc))

with io.open(PATH,"w",encoding="utf-8") as f:
    f.write(html)
print("")
print("=== TERMINE === (%+d caracteres vs vierge)" % (len(html)-orig))
