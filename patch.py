#!/usr/bin/env python3
"""
Script de patch automatique pour index.html
Usage: python3 patch.py chemin/vers/index.html
"""
import sys, os, re, shutil
from datetime import datetime

if len(sys.argv) < 2:
    print("Usage: python3 patch.py web/index.html")
    sys.exit(1)

src = sys.argv[1]
if not os.path.exists(src):
    print(f"Fichier introuvable : {src}")
    sys.exit(1)

# Backup
bak = src + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(src, bak)
print(f"Backup : {bak}")

with open(src, "r", encoding="utf-8") as f:
    html = f.read()

original_len = len(html)

# ── PATCH 1 : CSS ────────────────────────────────────────────────────────────
NEW_CSS = """
.catalogue-search{padding:8px 14px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:'Outfit',sans-serif;width:240px;transition:all .2s}
.catalogue-search:focus{outline:none;border-color:var(--gold);width:300px}
.cat-select-bar{background:var(--bg3);border:1px solid var(--border2);border-radius:var(--radius2);padding:8px 12px;width:100%;font-size:14px;font-family:'Outfit',sans-serif;color:var(--gold2);cursor:pointer;transition:all .2s;margin-bottom:6px}
.cat-select-bar:focus{outline:none;border-color:var(--gold);box-shadow:0 0 0 2px rgba(201,168,76,.12)}"""

MARKER_CSS = "@keyframes aiDot{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-8px)}}"
if NEW_CSS.strip()[:30] not in html:
    html = html.replace(MARKER_CSS, MARKER_CSS + NEW_CSS)
    print("✓ PATCH 1 : CSS ajouté")
else:
    print("⚠ PATCH 1 : CSS déjà présent")

# ── PATCH 2 : Nav items sidebar ──────────────────────────────────────────────
NAV_NEW = """    <div class="nav-item" onclick="goPage('catalogue',this)"><span class="nav-icon">📦</span> Catalogue</div>
    <div class="nav-item" onclick="goPage('factures',this)"><span class="nav-icon">🧾</span> Factures &amp; Bons</div>
"""
NAV_ANCHOR = 'onclick="goPage(\'recap\',this)"'
if "goPage('catalogue'" not in html:
    html = html.replace(
        f'<div class="nav-item" {NAV_ANCHOR}',
        NAV_NEW + f'<div class="nav-item" {NAV_ANCHOR}'
    )
    print("✓ PATCH 2 : Sidebar nav ajouté")
else:
    print("⚠ PATCH 2 : Nav déjà présent")

# ── PATCH 3 : TITLES objet ───────────────────────────────────────────────────
OLD_TITLES = "recap:'Recap mensuel'}"
NEW_TITLES = "recap:'Recap mensuel',catalogue:'Catalogue Produits',factures:'Factures & Bons'}"
if "'catalogue'" not in html:
    html = html.replace(OLD_TITLES, NEW_TITLES)
    print("✓ PATCH 3 : TITLES mis à jour")
else:
    print("⚠ PATCH 3 : TITLES déjà présent")

# ── PATCH 4 : goPage() appels ────────────────────────────────────────────────
OLD_RECAP_CALL = "if(name==='recap')initRecap();"
NEW_RECAP_CALL = """if(name==='recap')initRecap();
  if(name==='catalogue'){loadCatalogue();}
  if(name==='factures'){initFactures();}"""
if "loadCatalogue" not in html:
    html = html.replace(OLD_RECAP_CALL, NEW_RECAP_CALL)
    print("✓ PATCH 4 : goPage() mis à jour")
else:
    print("⚠ PATCH 4 : goPage() déjà mis à jour")

# ── PATCH 5 : Sélecteur catalogue dans modal transaction ─────────────────────
CAT_SELECT_BLOCK = """      <div class="form-group full" style="background:linear-gradient(135deg,rgba(201,168,76,.08),rgba(201,168,76,.02));border:1px solid rgba(201,168,76,.2);border-radius:var(--radius2);padding:12px;margin-bottom:4px">
        <label style="color:var(--gold2)">🏷 Choisir dans le catalogue (optionnel)</label>
        <select id="mCatalogueSelect" onchange="onCatalogueSelect()" class="cat-select-bar">
          <option value="">-- Sélectionner un article (auto-remplit motif/prix/unité) --</option>
        </select>
        <div style="font-size:11px;color:var(--text3);margin-top:4px">💡 La sélection remplit automatiquement les champs</div>
      </div>
"""
VENTE_ANCHOR = '<div class="form-group"><label>Motif</label><select id="mMotif"'
if "mCatalogueSelect" not in html:
    html = html.replace(VENTE_ANCHOR, CAT_SELECT_BLOCK + "      " + VENTE_ANCHOR.lstrip())
    print("✓ PATCH 5 : Sélecteur catalogue dans modal")
else:
    print("⚠ PATCH 5 : Sélecteur déjà présent")

# ── PATCH 6 : Pages Catalogue et Factures ────────────────────────────────────
CATALOGUE_PAGE = """
      <!-- CATALOGUE PRODUITS -->
      <div class="page" id="pg-catalogue">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:4px">
          <button class="btn primary" onclick="openAddCatalogue()">+ Nouvel article</button>
          <input class="catalogue-search" placeholder="🔍 Rechercher..." oninput="searchCatalogue(this.value)">
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px" id="catalogueGrid">
          <div class="loading"><div class="spinner"></div> Chargement...</div>
        </div>
      </div>

      <!-- FACTURES & BONS -->
      <div class="page" id="pg-factures">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <select id="facturesClientFilter" onchange="renderFactures(0)" style="padding:8px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:Outfit,sans-serif;min-width:180px">
            <option value="">Tous les clients</option>
          </select>
          <select id="facturesTypeFilter" onchange="renderFactures(0)" style="padding:8px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:Outfit,sans-serif">
            <option value="">Tous types</option>
            <option value="vente">🧾 Factures vente</option>
            <option value="remboursement">💳 Bons remboursement</option>
          </select>
          <div id="facturesStats" style="font-size:13px;color:var(--text3)"></div>
        </div>
        <div class="table-wrap">
          <div class="table-header"><span>Documents générés automatiquement</span></div>
          <table>
            <thead><tr>
              <th>N° Document</th><th>Date</th><th>Client</th><th>Type</th>
              <th style="text-align:right">Montant</th><th>Actions</th>
            </tr></thead>
            <tbody id="facturesTbody">
              <tr><td colspan="6"><div class="loading"><div class="spinner"></div></div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
"""

# Insérer avant la page RAPPELS (qui existe toujours)
RAPPELS_ANCHOR = "\n      <!-- RAPPELS -->"
if "pg-catalogue" not in html:
    html = html.replace(RAPPELS_ANCHOR, CATALOGUE_PAGE + RAPPELS_ANCHOR)
    print("✓ PATCH 6 : Pages catalogue et factures ajoutées")
else:
    print("⚠ PATCH 6 : Pages déjà présentes")

# ── PATCH 7 : Modal Catalogue ─────────────────────────────────────────────────
MODAL_CAT = """
<div class="modal-bg" id="modalCatalogue" onclick="if(event.target===this)this.classList.remove('open')">
  <div class="modal" style="max-width:520px">
    <input type="hidden" id="catId">
    <div class="modal-title" id="catModalTitle">Nouvel article</div>
    <div class="modal-sub">Ajouter au catalogue produits</div>
    <div class="form-grid">
      <div class="form-group full"><label>Nom de l'article *</label><input type="text" id="catNom" placeholder="Ex: Tabac x1, Bedo, Recharge..."></div>
      <div class="form-group"><label>Catégorie</label>
        <input type="text" id="catCategorie" placeholder="Tabac, Cannabis, Service..." list="catCategorieList" style="padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif;width:100%">
        <datalist id="catCategorieList"><option value="Tabac"><option value="Cannabis"><option value="Boisson"><option value="Service"><option value="Alimentation"><option value="Général"></datalist>
      </div>
      <div class="form-group"><label>Unité</label>
        <select id="catUnite" style="padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif">
          <option value="piece">Pièce(s)</option>
          <option value="gramme">Gramme(s)</option>
          <option value="litre">Litre(s)</option>
          <option value="paquet">Paquet(s)</option>
        </select>
      </div>
      <div class="form-group"><label>Prix de vente (€)</label><input type="number" id="catPrixVente" value="0" step="0.5" min="0" style="font-size:18px;font-weight:600;color:var(--green)"></div>
      <div class="form-group"><label>Prix d'achat (€)</label><input type="number" id="catPrixAchat" value="0" step="0.5" min="0" style="font-size:18px;font-weight:600;color:var(--red)"></div>
      <div class="form-group"><label>Stock minimum</label><input type="number" id="catStockMin" value="0" step="0.5" min="0"></div>
      <div class="form-group full"><label>Description (optionnel)</label><input type="text" id="catDescription" placeholder="Description courte..."></div>
    </div>
    <div class="modal-actions">
      <button class="btn danger" id="btnDeleteCat" style="margin-right:auto;display:none" onclick="deleteCatalogueItem(parseInt(document.getElementById('catId').value))">🗑 Supprimer</button>
      <button class="btn-cancel" onclick="document.getElementById('modalCatalogue').classList.remove('open')">Annuler</button>
      <button class="btn-save" onclick="saveCatalogueItem()">Enregistrer</button>
    </div>
  </div>
</div>
"""
BODY_END = "</body>"
if "modalCatalogue" not in html:
    html = html.replace(BODY_END, MODAL_CAT + "\n" + BODY_END)
    print("✓ PATCH 7 : Modal catalogue ajouté")
else:
    print("⚠ PATCH 7 : Modal déjà présent")

# ── PATCH 8 : Fonctions JS catalogue + factures ───────────────────────────────
JS_FUNCTIONS = r"""
// ══════════════════════════════════════════════════════
// CATALOGUE PRODUITS
// ══════════════════════════════════════════════════════
var catalogueCache = [];

async function loadCatalogue() {
  var res = await api('/api/catalogue');
  if (!res || !res.ok) return;
  catalogueCache = res.data;
  renderCatalogue();
  populateCatalogueSelect();
}

function renderCatalogue() {
  var grid = document.getElementById('catalogueGrid');
  if (!grid) return;
  grid.innerHTML = '';
  if (!catalogueCache.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text3);padding:40px">Aucun article. Cliquez sur <strong style="color:var(--gold2)">+ Nouvel article</strong> pour commencer.</div>';
    return;
  }
  var cats = {};
  catalogueCache.forEach(function(item) {
    var c = item.categorie || 'Général';
    if (!cats[c]) cats[c] = [];
    cats[c].push(item);
  });
  Object.keys(cats).sort().forEach(function(cat) {
    var catDiv = document.createElement('div');
    catDiv.style.cssText = 'grid-column:1/-1;margin-top:8px';
    catDiv.innerHTML = '<div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)">' + cat + '</div>';
    grid.appendChild(catDiv);
    cats[cat].forEach(function(item) {
      var card = document.createElement('div');
      card.className = 'catalogue-card fade';
      card.style.cssText = 'background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:18px;transition:all .2s;cursor:pointer';
      card.onmouseenter = function(){ card.style.borderColor='var(--gold)'; card.style.transform='translateY(-2px)'; };
      card.onmouseleave = function(){ card.style.borderColor='var(--border)'; card.style.transform=''; };
      var uniteL = item.unite==='gramme'?'g':item.unite==='litre'?'L':'pcs';
      var marge = parseFloat(item.prix_vente||0) - parseFloat(item.prix_achat||0);
      var margeCol = marge>=0?'var(--green)':'var(--red)';
      card.innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">'
        +'<div style="font-size:15px;font-weight:600;color:var(--text)">'+item.nom+'</div>'
        +'<span style="font-size:10px;background:var(--bg4);border:1px solid var(--border);border-radius:20px;padding:2px 8px;color:var(--text3)">'+item.categorie+'</span>'
        +'</div>'
        +(item.description?'<div style="font-size:12px;color:var(--text3);margin-bottom:10px">'+item.description+'</div>':'')
        +'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:12px">'
        +'<div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3);margin-bottom:2px">VENTE</div><div style="font-size:15px;font-weight:700;color:var(--green);font-family:DM Mono,monospace">'+parseFloat(item.prix_vente).toFixed(2)+' €</div><div style="font-size:10px;color:var(--text3)">/'+uniteL+'</div></div>'
        +'<div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3);margin-bottom:2px">ACHAT</div><div style="font-size:15px;font-weight:700;color:var(--red);font-family:DM Mono,monospace">'+parseFloat(item.prix_achat).toFixed(2)+' €</div><div style="font-size:10px;color:var(--text3)">/'+uniteL+'</div></div>'
        +'<div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3);margin-bottom:2px">MARGE</div><div style="font-size:15px;font-weight:700;color:'+margeCol+';font-family:DM Mono,monospace">'+marge.toFixed(2)+' €</div><div style="font-size:10px;color:var(--text3)">/'+uniteL+'</div></div>'
        +'</div>'
        +'<div style="display:flex;gap:8px">'
        +'<button class="btn primary" style="flex:1;font-size:12px;padding:7px" onclick="event.stopPropagation();selectArticleCatalogue('+item.id+')">➕ Vendre</button>'
        +'<button class="btn" style="font-size:12px;padding:7px 10px" onclick="event.stopPropagation();openEditCatalogue('+item.id+')">✏</button>'
        +'<button class="btn danger" style="font-size:12px;padding:7px 10px" onclick="event.stopPropagation();deleteCatalogueItem('+item.id+')">🗑</button>'
        +'</div>';
      grid.appendChild(card);
    });
  });
}

function populateCatalogueSelect() {
  var sel = document.getElementById('mCatalogueSelect');
  if (!sel) return;
  var prev = sel.value;
  sel.innerHTML = '<option value="">-- Sélectionner un article (auto-remplit les champs) --</option>';
  catalogueCache.forEach(function(item) {
    var o = document.createElement('option');
    o.value = item.id;
    o.dataset.prix = item.prix_vente;
    o.dataset.unite = item.unite;
    o.dataset.nom = item.nom;
    o.textContent = item.nom + ' — ' + parseFloat(item.prix_vente).toFixed(2) + '€/' + (item.unite==='gramme'?'g':'pcs') + ' [' + item.categorie + ']';
    sel.appendChild(o);
  });
  if (prev) sel.value = prev;
}

function onCatalogueSelect() {
  var sel = document.getElementById('mCatalogueSelect');
  if (!sel || !sel.value) return;
  var opt = sel.options[sel.selectedIndex];
  var prix = parseFloat(opt.dataset.prix) || 0;
  var unite = opt.dataset.unite || 'piece';
  var nom = opt.dataset.nom || '';
  var motifSel = document.getElementById('mMotif');
  if (motifSel) {
    var found = false;
    for (var i = 0; i < motifSel.options.length; i++) {
      if (motifSel.options[i].value === nom) { motifSel.selectedIndex = i; found = true; break; }
    }
    if (!found) { var o = document.createElement('option'); o.value = nom; o.textContent = nom; motifSel.appendChild(o); motifSel.value = nom; }
  }
  var prixInput = document.getElementById('mPrix');
  if (prixInput) prixInput.value = prix.toFixed(2);
  var uniteInput = document.getElementById('mUnite');
  if (uniteInput) uniteInput.value = unite;
  calcModal();
  notify('Article "' + nom + '" — ' + prix.toFixed(2) + ' €');
}

function selectArticleCatalogue(itemId) {
  var item = catalogueCache.find(function(i){ return i.id===itemId; });
  if (!item) return;
  if (!clientsCache.length) { notify('Créez d\'abord un client','error'); return; }
  populateClientSelects();
  populateStockSelect();
  document.getElementById('mType').value = 'debit';
  toggleTypeFields();
  var motifSel = document.getElementById('mMotif');
  if (motifSel) {
    var found = false;
    for (var i = 0; i < motifSel.options.length; i++) {
      if (motifSel.options[i].value === item.nom) { motifSel.selectedIndex = i; found = true; break; }
    }
    if (!found) { var o = document.createElement('option'); o.value = item.nom; o.textContent = item.nom; motifSel.appendChild(o); motifSel.value = item.nom; }
  }
  var prixInput = document.getElementById('mPrix');
  if (prixInput) prixInput.value = parseFloat(item.prix_vente).toFixed(2);
  var uniteInput = document.getElementById('mUnite');
  if (uniteInput) uniteInput.value = item.unite || 'piece';
  document.getElementById('mQty').value = '1';
  var catSel = document.getElementById('mCatalogueSelect');
  if (catSel) catSel.value = itemId;
  setStatutPaiement('recu');
  calcModal();
  document.getElementById('modalTrans').classList.add('open');
}

function openAddCatalogue() {
  document.getElementById('catId').value = '';
  document.getElementById('catNom').value = '';
  document.getElementById('catCategorie').value = 'Général';
  document.getElementById('catDescription').value = '';
  document.getElementById('catPrixVente').value = '0';
  document.getElementById('catPrixAchat').value = '0';
  document.getElementById('catUnite').value = 'piece';
  document.getElementById('catStockMin').value = '0';
  document.getElementById('catModalTitle').textContent = 'Nouvel article';
  document.getElementById('btnDeleteCat').style.display = 'none';
  document.getElementById('modalCatalogue').classList.add('open');
  setTimeout(function(){ document.getElementById('catNom').focus(); }, 100);
}

function openEditCatalogue(itemId) {
  var item = catalogueCache.find(function(i){ return i.id===itemId; });
  if (!item) return;
  document.getElementById('catId').value = itemId;
  document.getElementById('catNom').value = item.nom;
  document.getElementById('catCategorie').value = item.categorie || 'Général';
  document.getElementById('catDescription').value = item.description || '';
  document.getElementById('catPrixVente').value = parseFloat(item.prix_vente).toFixed(2);
  document.getElementById('catPrixAchat').value = parseFloat(item.prix_achat).toFixed(2);
  document.getElementById('catUnite').value = item.unite || 'piece';
  document.getElementById('catStockMin').value = parseFloat(item.stock_min||0).toFixed(1);
  document.getElementById('catModalTitle').textContent = 'Modifier l\'article';
  document.getElementById('btnDeleteCat').style.display = 'inline-flex';
  document.getElementById('modalCatalogue').classList.add('open');
}

async function saveCatalogueItem() {
  var nom = document.getElementById('catNom').value.trim();
  if (!nom) { notify('Nom requis','error'); return; }
  var itemId = document.getElementById('catId').value;
  var body = {
    nom: nom,
    categorie: document.getElementById('catCategorie').value || 'Général',
    description: document.getElementById('catDescription').value,
    prix_vente: parseFloat(document.getElementById('catPrixVente').value) || 0,
    prix_achat: parseFloat(document.getElementById('catPrixAchat').value) || 0,
    unite: document.getElementById('catUnite').value,
    stock_min: parseFloat(document.getElementById('catStockMin').value) || 0,
  };
  var res = itemId
    ? await api('/api/catalogue/'+itemId, {method:'PUT', body:body})
    : await api('/api/catalogue', {method:'POST', body:body});
  if (res && res.ok) {
    document.getElementById('modalCatalogue').classList.remove('open');
    notify(itemId ? 'Article modifié' : 'Article créé');
    await loadCatalogue();
  } else notify(res&&res.error?res.error:'Erreur','error');
}

async function deleteCatalogueItem(itemId) {
  var item = catalogueCache.find(function(i){ return i.id===itemId; });
  if (!confirm('Supprimer "' + (item?item.nom:'') + '" du catalogue ?')) return;
  document.getElementById('modalCatalogue').classList.remove('open');
  await api('/api/catalogue/'+itemId, {method:'DELETE'});
  notify('Article supprimé');
  await loadCatalogue();
}

function searchCatalogue(val) {
  val = (val||'').toLowerCase();
  document.querySelectorAll('.catalogue-card').forEach(function(c){
    c.style.display = c.textContent.toLowerCase().includes(val) ? '' : 'none';
  });
}

// ══════════════════════════════════════════════════════
// FACTURES & BONS
// ══════════════════════════════════════════════════════
var facturesCache = [];

async function loadFactures(clientId) {
  var url = '/api/factures' + (clientId ? '?client_id='+clientId : '') + '&limit=200';
  var res = await api(url);
  if (!res || !res.ok) return;
  facturesCache = res.data;
  renderFactures(clientId || 0);
}

function renderFactures(clientId) {
  var tbody = document.getElementById('facturesTbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  var cid = clientId || parseInt((document.getElementById('facturesClientFilter')||{}).value||0) || 0;
  var list = cid ? facturesCache.filter(function(f){ return f.client_id===cid; }) : facturesCache;
  var typeFilter = (document.getElementById('facturesTypeFilter')||{}).value || '';
  if (typeFilter) list = list.filter(function(f){ return f.type===typeFilter; });
  var nbVentes = list.filter(function(f){ return f.type==='vente'; }).length;
  var nbBons = list.filter(function(f){ return f.type==='remboursement'; }).length;
  var totalVentes = list.filter(function(f){ return f.type==='vente'; }).reduce(function(s,f){ return s+parseFloat(f.montant_net||0); }, 0);
  var el = document.getElementById('facturesStats');
  if (el) el.innerHTML = list.length + ' document(s) · <span style="color:var(--green)">' + nbVentes + ' FAC</span> · <span style="color:var(--gold2)">' + nbBons + ' BON</span> · Total ventes : <strong style="color:var(--gold2)">' + totalVentes.toFixed(2) + ' €</strong>';
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:24px">Aucun document — les factures sont générées automatiquement à chaque transaction</td></tr>';
    return;
  }
  list.forEach(function(f) {
    var isVente = f.type === 'vente';
    var col = isVente ? 'var(--green)' : 'var(--gold2)';
    var icone = isVente ? '🧾' : '💳';
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td style="font-family:DM Mono,monospace;font-size:12px;color:var(--gold2)">'+f.numero+'</td>'
      +'<td>'+fmtDate(f.date_creation)+'</td>'
      +'<td style="color:var(--text);font-weight:500">'+(f.client_nom||'—')+'</td>'
      +'<td><span class="badge '+(isVente?'debit':'credit')+'">'+icone+' '+(isVente?'Facture':'Bon remb.')+'</span></td>'
      +'<td class="mono" style="color:'+col+';font-weight:600;text-align:right">'+parseFloat(f.montant_net||0).toFixed(2)+' €</td>'
      +'<td style="display:flex;gap:6px">'
      +'<button class="btn primary" style="font-size:11px;padding:4px 10px" onclick="voirFacture('+f.id+')">👁 Voir</button>'
      +'<button class="btn" style="font-size:11px;padding:4px 10px" onclick="imprimerFacture('+f.id+')">🖨</button>'
      +'<button class="btn danger" style="font-size:11px;padding:4px 8px" onclick="supprimerFacture('+f.id+')">✕</button>'
      +'</td>';
    tbody.appendChild(tr);
  });
}

async function voirFacture(fid) {
  var res = await fetch('/api/factures/'+fid+'/html', {headers:{'X-Session-Token':TOKEN}});
  if (!res.ok) { notify('Introuvable','error'); return; }
  var html = await res.text();
  var blob = new Blob([html], {type:'text/html'});
  var url = URL.createObjectURL(blob);
  var pf = document.getElementById('printFrame');
  if (pf) { pf.src = url; document.getElementById('modalPrintPreview').classList.add('open'); }
  else window.open(url,'_blank');
}

async function imprimerFacture(fid) {
  var res = await fetch('/api/factures/'+fid+'/html', {headers:{'X-Session-Token':TOKEN}});
  if (!res.ok) { notify('Introuvable','error'); return; }
  var html = await res.text();
  var blob = new Blob([html], {type:'text/html'});
  var url = URL.createObjectURL(blob);
  var pf = document.getElementById('printFrame');
  if (pf) {
    pf.src = url;
    document.getElementById('modalPrintPreview').classList.add('open');
    pf.onload = function(){ pf.contentWindow.print(); pf.onload = null; };
  }
}

async function supprimerFacture(fid) {
  if (!confirm('Supprimer ce document ?')) return;
  await api('/api/factures/'+fid, {method:'DELETE'});
  notify('Document supprimé');
  facturesCache = facturesCache.filter(function(f){ return f.id!==fid; });
  renderFactures(0);
}

function initFactures() {
  var sel = document.getElementById('facturesClientFilter');
  if (sel) {
    var prev = sel.value;
    sel.innerHTML = '<option value="">Tous les clients</option>';
    clientsCache.forEach(function(c){
      var o = document.createElement('option');
      o.value = c.id; o.textContent = c.nom;
      sel.appendChild(o);
    });
    if (prev) sel.value = prev;
  }
  loadFactures(0);
}
"""

SCRIPT_END_MARKER = "\n</script>"
# Chercher le dernier </script> avant </body>
last_script_pos = html.rfind("</script>")
if "loadCatalogue" not in html and last_script_pos != -1:
    html = html[:last_script_pos] + JS_FUNCTIONS + html[last_script_pos:]
    print("✓ PATCH 8 : Fonctions JS catalogue+factures ajoutées")
else:
    print("⚠ PATCH 8 : Fonctions déjà présentes")

# ── PATCH 9 : initApp() — ajouter loadCatalogue() ────────────────────────────
OLD_INIT = "function initApp(){\n  loadDashboard();"
NEW_INIT = "function initApp(){\n  loadDashboard();loadCatalogue();"
if "loadCatalogue" in html and OLD_INIT in html:
    html = html.replace(OLD_INIT, NEW_INIT)
    print("✓ PATCH 9 : initApp() mis à jour")
elif NEW_INIT in html:
    print("⚠ PATCH 9 : initApp() déjà mis à jour")
else:
    print("⚠ PATCH 9 : initApp() non trouvé — vérifier manuellement")

# ── Écriture ──────────────────────────────────────────────────────────────────
with open(src, "w", encoding="utf-8") as f:
    f.write(html)

added = len(html) - original_len
print(f"\n✅ Patch appliqué ! {added:+} caractères ajoutés.")
print(f"   Fichier : {src}")
print(f"   Backup  : {bak}")
