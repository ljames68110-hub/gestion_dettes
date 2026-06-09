#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch2.py - Ajoute Catalogue + Factures a index.html SANS casser les fonctions
d'impression. Insere le modal et le JS aux bons endroits (hors chaines JS).
Idempotent : on peut le relancer sans dupliquer.
Usage: python patch2.py web/index.html
"""
import sys, io, re

path = sys.argv[1] if len(sys.argv) > 1 else "web/index.html"
with io.open(path, "r", encoding="utf-8") as f:
    html = f.read()
orig_len = len(html)

def already(marker):
    return marker in html

# ── 1) CSS ────────────────────────────────────────────────────────────────
CSS = """
.catalogue-search{padding:8px 14px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:'Outfit',sans-serif;width:240px;transition:all .2s}
.catalogue-search:focus{outline:none;border-color:var(--gold);width:300px}
.cat-select-bar{background:var(--bg3);border:1px solid var(--border2);border-radius:var(--radius2);padding:8px 12px;width:100%;font-size:14px;font-family:'Outfit',sans-serif;color:var(--gold2);cursor:pointer;margin-bottom:6px}
.cat-select-bar:focus{outline:none;border-color:var(--gold)}
.catalogue-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:18px;transition:all .2s;cursor:pointer}
.catalogue-card:hover{border-color:var(--gold);transform:translateY(-2px)}
"""
if not already(".catalogue-search{"):
    html = html.replace("</style>", CSS + "\n</style>", 1)
    print("1) CSS ajoute")
else:
    print("1) CSS deja present")

# ── 2) Nav sidebar ─────────────────────────────────────────────────────────
NAV = """    <div class="nav-item" onclick="goPage('catalogue',this)"><span class="nav-icon">CAT</span> Catalogue</div>
    <div class="nav-item" onclick="goPage('factures',this)"><span class="nav-icon">FAC</span> Factures &amp; Bons</div>
"""
if not already("goPage('catalogue'"):
    # inserer avant le 1er nav-item recap si present, sinon avant settings
    anchor = None
    for a in ["goPage('recap'", "goPage('settings'", "goPage('soldes'"]:
        idx = html.find(a)
        if idx != -1:
            # remonter au debut de la balise div
            div_start = html.rfind('<div class="nav-item"', 0, idx)
            if div_start != -1:
                anchor = div_start
                break
    if anchor is not None:
        html = html[:anchor] + NAV + html[anchor:]
        print("2) Nav sidebar ajoutee")
    else:
        print("2) ATTENTION : ancre nav introuvable")
else:
    print("2) Nav deja presente")

# ── 3) TITLES ──────────────────────────────────────────────────────────────
if "catalogue:'Catalogue" not in html:
    m = re.search(r"(recap:'[^']*')\s*\}", html)
    if m:
        html = html.replace(m.group(0), m.group(1) + ",catalogue:'Catalogue Produits',factures:'Factures & Bons'}")
        print("3) TITLES mis a jour")
    else:
        print("3) ATTENTION : objet TITLES introuvable")
else:
    print("3) TITLES deja a jour")

# ── 4) goPage() ────────────────────────────────────────────────────────────
if "loadCatalogue()" not in html:
    m = re.search(r"if\s*\(\s*name\s*===\s*'recap'\s*\)\s*initRecap\(\);", html)
    if m:
        add = m.group(0) + "\n  if(name==='catalogue'){loadCatalogue();}\n  if(name==='factures'){initFactures();}"
        html = html.replace(m.group(0), add)
        print("4) goPage() mis a jour")
    else:
        print("4) ATTENTION : if(name==='recap') introuvable - a verifier")
else:
    print("4) goPage() deja a jour")

# ── 5) Pages catalogue + factures (inserer avant un commentaire de page sur) ─
PAGES = """
      <div class="page" id="pg-catalogue">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:4px">
          <button class="btn primary" onclick="openAddCatalogue()">+ Nouvel article</button>
          <input class="catalogue-search" placeholder="Rechercher..." oninput="searchCatalogue(this.value)">
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px" id="catalogueGrid">
          <div class="loading"><div class="spinner"></div> Chargement...</div>
        </div>
      </div>

      <div class="page" id="pg-factures">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <select id="facturesClientFilter" onchange="renderFactures(0)" style="padding:8px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:Outfit,sans-serif;min-width:180px"><option value="">Tous les clients</option></select>
          <select id="facturesTypeFilter" onchange="renderFactures(0)" style="padding:8px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;font-family:Outfit,sans-serif"><option value="">Tous types</option><option value="vente">Factures vente</option><option value="remboursement">Bons remboursement</option></select>
          <div id="facturesStats" style="font-size:13px;color:var(--text3)"></div>
        </div>
        <div class="table-wrap">
          <div class="table-header"><span>Documents generes automatiquement</span></div>
          <table>
            <thead><tr><th>N Document</th><th>Date</th><th>Client</th><th>Type</th><th style="text-align:right">Montant</th><th>Actions</th></tr></thead>
            <tbody id="facturesTbody"><tr><td colspan="6"><div class="loading"><div class="spinner"></div></div></td></tr></tbody>
          </table>
        </div>
      </div>
"""
if 'id="pg-catalogue"' not in html:
    # Inserer juste avant la fermeture du conteneur .content : reperer le dernier <div class="page"
    # On insere apres la fin de la derniere page existante. Strategie sure :
    # trouver le marqueur "<!-- RAPPELS -->" ou la 1ere page, sinon avant </div> du content.
    placed = False
    for anchor in ['<!-- RAPPELS -->', 'id="pg-rappels"', 'id="pg-settings"']:
        idx = html.find(anchor)
        if idx != -1:
            # remonter au debut de sa balise <div class="page"
            ds = html.rfind('<div class="page"', 0, idx)
            if ds == -1:
                ds = idx
            html = html[:ds] + PAGES + "\n      " + html[ds:]
            placed = True
            print("5) Pages catalogue+factures inserees (ancre %s)" % anchor)
            break
    if not placed:
        print("5) ATTENTION : ancre pages introuvable - insertion manuelle requise")
else:
    print("5) Pages deja presentes")

# ── 6) Modal catalogue : APRES le dernier </script> (zone HTML sure) ────────
MODAL = """
<div class="modal-bg" id="modalCatalogue" onclick="if(event.target===this)this.classList.remove('open')">
  <div class="modal" style="max-width:520px">
    <input type="hidden" id="catId">
    <div class="modal-title" id="catModalTitle">Nouvel article</div>
    <div class="modal-sub">Ajouter au catalogue produits</div>
    <div class="form-grid">
      <div class="form-group full"><label>Nom de l'article *</label><input type="text" id="catNom" placeholder="Ex: Tabac x1, Bedo..."></div>
      <div class="form-group"><label>Categorie</label><input type="text" id="catCategorie" placeholder="Tabac, Cannabis..." list="catCategorieList" style="padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif;width:100%"><datalist id="catCategorieList"><option value="Tabac"><option value="Cannabis"><option value="Boisson"><option value="Service"><option value="Alimentation"><option value="General"></datalist></div>
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
async function loadCatalogue(){var res=await api('/api/catalogue');if(!res||!res.ok)return;catalogueCache=res.data;renderCatalogue();populateCatalogueSelect();}
function renderCatalogue(){var grid=document.getElementById('catalogueGrid');if(!grid)return;grid.innerHTML='';if(!catalogueCache.length){grid.innerHTML='<div style="grid-column:1/-1;text-align:center;color:var(--text3);padding:40px">Aucun article. Cliquez sur <strong style="color:var(--gold2)">+ Nouvel article</strong>.</div>';return;}
var cats={};catalogueCache.forEach(function(it){var c=it.categorie||'General';if(!cats[c])cats[c]=[];cats[c].push(it);});
Object.keys(cats).sort().forEach(function(cat){var d=document.createElement('div');d.style.cssText='grid-column:1/-1;margin-top:8px';d.innerHTML='<div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)">'+cat+'</div>';grid.appendChild(d);
cats[cat].forEach(function(it){var card=document.createElement('div');card.className='catalogue-card';var u=it.unite==='gramme'?'g':it.unite==='litre'?'L':'pcs';var marge=(parseFloat(it.prix_vente||0)-parseFloat(it.prix_achat||0));var mc=marge>=0?'var(--green)':'var(--red)';
card.innerHTML='<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px"><div style="font-size:15px;font-weight:600;color:var(--text)">'+it.nom+'</div><span style="font-size:10px;background:var(--bg4);border:1px solid var(--border);border-radius:20px;padding:2px 8px;color:var(--text3)">'+it.categorie+'</span></div>'+(it.description?'<div style="font-size:12px;color:var(--text3);margin-bottom:10px">'+it.description+'</div>':'')+'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:12px"><div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3)">VENTE</div><div style="font-size:15px;font-weight:700;color:var(--green);font-family:DM Mono,monospace">'+parseFloat(it.prix_vente).toFixed(2)+'</div><div style="font-size:10px;color:var(--text3)">/'+u+'</div></div><div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3)">ACHAT</div><div style="font-size:15px;font-weight:700;color:var(--red);font-family:DM Mono,monospace">'+parseFloat(it.prix_achat).toFixed(2)+'</div><div style="font-size:10px;color:var(--text3)">/'+u+'</div></div><div style="background:var(--bg3);border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:var(--text3)">MARGE</div><div style="font-size:15px;font-weight:700;color:'+mc+';font-family:DM Mono,monospace">'+marge.toFixed(2)+'</div><div style="font-size:10px;color:var(--text3)">/'+u+'</div></div></div><div style="display:flex;gap:8px"><button class="btn primary" style="flex:1;font-size:12px;padding:7px" onclick="selectArticleCatalogue('+it.id+')">+ Vendre</button><button class="btn" style="font-size:12px;padding:7px 10px" onclick="openEditCatalogue('+it.id+')">Edit</button><button class="btn danger" style="font-size:12px;padding:7px 10px" onclick="deleteCatalogueItem('+it.id+')">X</button></div>';
grid.appendChild(card);});});}
function populateCatalogueSelect(){var sel=document.getElementById('mCatalogueSelect');if(!sel)return;var prev=sel.value;sel.innerHTML='<option value="">-- Choisir un article --</option>';catalogueCache.forEach(function(it){var o=document.createElement('option');o.value=it.id;o.dataset.prix=it.prix_vente;o.dataset.unite=it.unite;o.dataset.nom=it.nom;o.textContent=it.nom+' - '+parseFloat(it.prix_vente).toFixed(2)+'/'+(it.unite==='gramme'?'g':'pcs');sel.appendChild(o);});if(prev)sel.value=prev;}
function onCatalogueSelect(){var sel=document.getElementById('mCatalogueSelect');if(!sel||!sel.value)return;var opt=sel.options[sel.selectedIndex];var prix=parseFloat(opt.dataset.prix)||0;var unite=opt.dataset.unite||'piece';var nom=opt.dataset.nom||'';var ms=document.getElementById('mMotif');if(ms){var f=false;for(var i=0;i<ms.options.length;i++){if(ms.options[i].value===nom){ms.selectedIndex=i;f=true;break;}}if(!f){var o=document.createElement('option');o.value=nom;o.textContent=nom;ms.appendChild(o);ms.value=nom;}}var pi=document.getElementById('mPrix');if(pi)pi.value=prix.toFixed(2);var ui=document.getElementById('mUnite');if(ui)ui.value=unite;if(typeof calcModal==='function')calcModal();}
function selectArticleCatalogue(id){var it=catalogueCache.find(function(i){return i.id===id;});if(!it)return;if(!clientsCache.length){notify('Creez d abord un client','error');return;}populateClientSelects();if(typeof populateStockSelect==='function')populateStockSelect();document.getElementById('mType').value='debit';if(typeof toggleTypeFields==='function')toggleTypeFields();var ms=document.getElementById('mMotif');if(ms){var f=false;for(var i=0;i<ms.options.length;i++){if(ms.options[i].value===it.nom){ms.selectedIndex=i;f=true;break;}}if(!f){var o=document.createElement('option');o.value=it.nom;o.textContent=it.nom;ms.appendChild(o);ms.value=it.nom;}}var pi=document.getElementById('mPrix');if(pi)pi.value=parseFloat(it.prix_vente).toFixed(2);var ui=document.getElementById('mUnite');if(ui)ui.value=it.unite||'piece';var q=document.getElementById('mQty');if(q)q.value='1';if(typeof setStatutPaiement==='function')setStatutPaiement('recu');if(typeof calcModal==='function')calcModal();document.getElementById('modalTrans').classList.add('open');}
function openAddCatalogue(){document.getElementById('catId').value='';document.getElementById('catNom').value='';document.getElementById('catCategorie').value='General';document.getElementById('catDescription').value='';document.getElementById('catPrixVente').value='0';document.getElementById('catPrixAchat').value='0';document.getElementById('catUnite').value='piece';document.getElementById('catStockMin').value='0';document.getElementById('catModalTitle').textContent='Nouvel article';document.getElementById('btnDeleteCat').style.display='none';document.getElementById('modalCatalogue').classList.add('open');}
function openEditCatalogue(id){var it=catalogueCache.find(function(i){return i.id===id;});if(!it)return;document.getElementById('catId').value=id;document.getElementById('catNom').value=it.nom;document.getElementById('catCategorie').value=it.categorie||'General';document.getElementById('catDescription').value=it.description||'';document.getElementById('catPrixVente').value=parseFloat(it.prix_vente).toFixed(2);document.getElementById('catPrixAchat').value=parseFloat(it.prix_achat).toFixed(2);document.getElementById('catUnite').value=it.unite||'piece';document.getElementById('catStockMin').value=parseFloat(it.stock_min||0).toFixed(1);document.getElementById('catModalTitle').textContent='Modifier l article';document.getElementById('btnDeleteCat').style.display='inline-flex';document.getElementById('modalCatalogue').classList.add('open');}
async function saveCatalogueItem(){var nom=document.getElementById('catNom').value.trim();if(!nom){notify('Nom requis','error');return;}var id=document.getElementById('catId').value;var body={nom:nom,categorie:document.getElementById('catCategorie').value||'General',description:document.getElementById('catDescription').value,prix_vente:parseFloat(document.getElementById('catPrixVente').value)||0,prix_achat:parseFloat(document.getElementById('catPrixAchat').value)||0,unite:document.getElementById('catUnite').value,stock_min:parseFloat(document.getElementById('catStockMin').value)||0};var res=id?await api('/api/catalogue/'+id,{method:'PUT',body:body}):await api('/api/catalogue',{method:'POST',body:body});if(res&&res.ok){document.getElementById('modalCatalogue').classList.remove('open');notify(id?'Article modifie':'Article cree');await loadCatalogue();}else notify(res&&res.error?res.error:'Erreur','error');}
async function deleteCatalogueItem(id){var it=catalogueCache.find(function(i){return i.id===id;});if(!confirm('Supprimer "'+(it?it.nom:'')+'" ?'))return;document.getElementById('modalCatalogue').classList.remove('open');await api('/api/catalogue/'+id,{method:'DELETE'});notify('Article supprime');await loadCatalogue();}
function searchCatalogue(v){v=(v||'').toLowerCase();document.querySelectorAll('.catalogue-card').forEach(function(c){c.style.display=c.textContent.toLowerCase().includes(v)?'':'none';});}
// ===== FACTURES =====
var facturesCache=[];
async function loadFactures(cid){var url='/api/factures'+(cid?'?client_id='+cid:'')+'&limit=200';var res=await api(url);if(!res||!res.ok)return;facturesCache=res.data;renderFactures(cid||0);}
function renderFactures(cid){var tb=document.getElementById('facturesTbody');if(!tb)return;tb.innerHTML='';cid=cid||parseInt((document.getElementById('facturesClientFilter')||{}).value||0)||0;var list=cid?facturesCache.filter(function(f){return f.client_id===cid;}):facturesCache;var tf=(document.getElementById('facturesTypeFilter')||{}).value||'';if(tf)list=list.filter(function(f){return f.type===tf;});var nv=list.filter(function(f){return f.type==='vente';}).length;var nb=list.filter(function(f){return f.type==='remboursement';}).length;var tv=list.filter(function(f){return f.type==='vente';}).reduce(function(s,f){return s+parseFloat(f.montant_net||0);},0);var el=document.getElementById('facturesStats');if(el)el.innerHTML=list.length+' document(s) - <span style="color:var(--green)">'+nv+' FAC</span> - <span style="color:var(--gold2)">'+nb+' BON</span> - Total ventes: <strong style="color:var(--gold2)">'+tv.toFixed(2)+'</strong>';
if(!list.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:24px">Aucun document - generes automatiquement a chaque transaction</td></tr>';return;}
list.forEach(function(f){var iv=f.type==='vente';var col=iv?'var(--green)':'var(--gold2)';var tr=document.createElement('tr');tr.innerHTML='<td style="font-family:DM Mono,monospace;font-size:12px;color:var(--gold2)">'+f.numero+'</td><td>'+fmtDate(f.date_creation)+'</td><td style="color:var(--text);font-weight:500">'+(f.client_nom||'-')+'</td><td><span class="badge '+(iv?'debit':'credit')+'">'+(iv?'Facture':'Bon remb.')+'</span></td><td class="mono" style="color:'+col+';font-weight:600;text-align:right">'+parseFloat(f.montant_net||0).toFixed(2)+'</td><td style="display:flex;gap:6px"><button class="btn primary" style="font-size:11px;padding:4px 10px" onclick="voirFacture('+f.id+')">Voir</button><button class="btn" style="font-size:11px;padding:4px 10px" onclick="imprimerFacture('+f.id+')">Imp</button><button class="btn danger" style="font-size:11px;padding:4px 8px" onclick="supprimerFacture('+f.id+')">X</button></td>';tb.appendChild(tr);});}
async function voirFacture(fid){var res=await fetch('/api/factures/'+fid+'/html',{headers:{'X-Session-Token':TOKEN}});if(!res.ok){notify('Introuvable','error');return;}var h=await res.text();var b=new Blob([h],{type:'text/html'});var u=URL.createObjectURL(b);var pf=document.getElementById('printFrame');if(pf){pf.src=u;document.getElementById('modalPrintPreview').classList.add('open');}else window.open(u,'_blank');}
async function imprimerFacture(fid){var res=await fetch('/api/factures/'+fid+'/html',{headers:{'X-Session-Token':TOKEN}});if(!res.ok){notify('Introuvable','error');return;}var h=await res.text();var b=new Blob([h],{type:'text/html'});var u=URL.createObjectURL(b);var pf=document.getElementById('printFrame');if(pf){pf.src=u;document.getElementById('modalPrintPreview').classList.add('open');pf.onload=function(){try{pf.contentWindow.print();}catch(e){}pf.onload=null;};}}
async function supprimerFacture(fid){if(!confirm('Supprimer ce document ?'))return;await api('/api/factures/'+fid,{method:'DELETE'});notify('Document supprime');facturesCache=facturesCache.filter(function(f){return f.id!==fid;});renderFactures(0);}
function initFactures(){var sel=document.getElementById('facturesClientFilter');if(sel){var prev=sel.value;sel.innerHTML='<option value="">Tous les clients</option>';clientsCache.forEach(function(c){var o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);});if(prev)sel.value=prev;}loadFactures(0);}
</script>
"""

if 'function loadCatalogue' not in html:
    pos = html.rfind("</script>")
    if pos != -1:
        insert_at = pos + len("</script>")
        html = html[:insert_at] + "\n" + MODAL + "\n" + JS + html[insert_at:]
        print("6) Modal + JS catalogue/factures inseres apres le dernier </script>")
    else:
        print("6) ERREUR : </script> introuvable")
else:
    print("6) Modal/JS deja presents")

# ── 7) Selecteur catalogue dans le modal transaction ────────────────────────
CATSEL = """      <div class="form-group full" style="background:linear-gradient(135deg,rgba(201,168,76,.08),rgba(201,168,76,.02));border:1px solid rgba(201,168,76,.2);border-radius:var(--radius2);padding:12px;margin-bottom:4px">
        <label style="color:var(--gold2)">Choisir dans le catalogue (optionnel)</label>
        <select id="mCatalogueSelect" onchange="onCatalogueSelect()" class="cat-select-bar"><option value="">-- Selectionner un article --</option></select>
      </div>
"""
if 'id="mCatalogueSelect"' not in html:
    # Inserer juste avant le champ Motif du modal transaction
    m = re.search(r'(<div class="form-group"><label>Motif</label><select id="mMotif")', html)
    if m:
        html = html.replace(m.group(1), CATSEL + "      " + m.group(1), 1)
        print("7) Selecteur catalogue ajoute dans le modal transaction")
    else:
        print("7) ATTENTION : champ Motif introuvable - selecteur non ajoute (non bloquant)")
else:
    print("7) Selecteur deja present")

# ── 8) initApp : loadCatalogue() ────────────────────────────────────────────
if "function initApp" in html and "loadCatalogue();" not in html.split("function initApp")[1][:200]:
    m = re.search(r"(function initApp\(\)\s*\{\s*)", html)
    if m:
        html = html.replace(m.group(1), m.group(1) + "loadCatalogue();", 1)
        print("8) initApp() appelle loadCatalogue()")
    else:
        print("8) initApp introuvable (non bloquant)")
else:
    print("8) initApp deja ok ou loadCatalogue deja appele")

with io.open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("")
print("TERMINE. %+d caracteres. Modals catalogue: %d (doit etre 1)" % (len(html)-orig_len, html.count('id="modalCatalogue"')))
