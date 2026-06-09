#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_categories.py
  - Sidebar defilable (fix overflow qui cache Parametres)
  - Table 'categories' + CRUD (suppression bloquee si articles l'utilisent)
  - Section "Categories du catalogue" dans Parametres
  - Les selects categorie se remplissent depuis la table
Idempotent. Usage (dans le dossier projet): python add_categories.py
"""
import io, re

def read(p):
    with io.open(p,"r",encoding="utf-8") as f: return f.read()
def write(p,c):
    with io.open(p,"w",encoding="utf-8") as f: f.write(c)

# ══════════════════════════════════════════════════════════════════
# DB.PY : table categories + fonctions
# ══════════════════════════════════════════════════════════════════
db = read("db.py")
if "_ensure_categories_table" not in db:
    block = '''

# -- CATEGORIES DU CATALOGUE --------------------------------------------------
def _ensure_categories_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        n = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if n == 0:
            for c in ["General","Tabac","Cannabis","Boisson","Service","Alimentation"]:
                try: conn.execute("INSERT INTO categories (nom) VALUES (?)", (c,))
                except: pass
        conn.commit()

def get_categories():
    _ensure_categories_table()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY nom").fetchall()
    return [dict(r) for r in rows]

def add_category(nom):
    _ensure_categories_table()
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Nom requis")
    with get_conn() as conn:
        exists = conn.execute("SELECT COUNT(*) FROM categories WHERE nom=?", (nom,)).fetchone()[0]
        if exists:
            raise ValueError("Categorie deja existante")
        cur = conn.execute("INSERT INTO categories (nom) VALUES (?)", (nom,))
        conn.commit()
        return cur.lastrowid

def count_articles_in_category(nom):
    try:
        _ensure_catalogue_table()
    except Exception:
        pass
    with get_conn() as conn:
        try:
            return conn.execute("SELECT COUNT(*) FROM catalogue WHERE categorie=? AND actif=1", (nom,)).fetchone()[0]
        except Exception:
            return 0

def delete_category(cid):
    _ensure_categories_table()
    with get_conn() as conn:
        row = conn.execute("SELECT nom FROM categories WHERE id=?", (cid,)).fetchone()
        if not row:
            return
        nom = row[0]
    used = count_articles_in_category(nom)
    if used > 0:
        raise ValueError("%d article(s) utilisent cette categorie" % used)
    with get_conn() as conn:
        conn.execute("DELETE FROM categories WHERE id=?", (cid,))
        conn.commit()
'''
    db = db.rstrip() + "\n" + block
    write("db.py", db)
    print("DB) table categories + fonctions ajoutees")
else:
    print("DB) categories deja presentes")

# ══════════════════════════════════════════════════════════════════
# API.PY : routes categories (avant SERVE FRONTEND)
# ══════════════════════════════════════════════════════════════════
api = read("api.py")
if '/api/categories' not in api:
    routes = '''
# -- CATEGORIES ---------------------------------------------------------------
@app.route("/api/categories")
@require_auth
def categories_list():
    return ok(db.get_categories())

@app.route("/api/categories", methods=["POST"])
@require_auth
def categories_create():
    data = request.json or {}
    try:
        cid = db.add_category(data.get("nom",""))
    except ValueError as e:
        return err(str(e))
    return ok({"id": cid}), 201

@app.route("/api/categories/<int:cid>", methods=["DELETE"])
@require_auth
def categories_delete(cid):
    try:
        db.delete_category(cid)
    except ValueError as e:
        return err(str(e), 409)
    return ok({"deleted": cid})

'''
    marker = "# ── SERVE FRONTEND"
    if marker in api:
        api = api.replace(marker, routes + marker, 1)
        print("API) routes categories ajoutees")
    else:
        # fallback : avant le dernier @app.route("/")
        idx = api.rfind('@app.route("/", defaults')
        if idx != -1:
            api = api[:idx] + routes + api[idx:]
            print("API) routes categories ajoutees (fallback)")
        else:
            print("API) ATTENTION point d'insertion introuvable")
    write("api.py", api)
else:
    print("API) routes categories deja presentes")

# ══════════════════════════════════════════════════════════════════
# WEB : sidebar defilable
# ══════════════════════════════════════════════════════════════════
html = read("web/index.html")

old_sb = ".sidebar{width:224px;min-width:224px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:20px 0;position:relative;overflow:hidden}"
new_sb = ".sidebar{width:224px;min-width:224px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:20px 0;position:relative;overflow-y:auto;overflow-x:hidden}"
if old_sb in html:
    html = html.replace(old_sb, new_sb)
    print("WEB-1) sidebar defilable (overflow-y:auto)")
elif "overflow-y:auto;overflow-x:hidden}" in html:
    print("WEB-1) sidebar deja defilable")
else:
    print("WEB-1) ATTENTION regle .sidebar non trouvee a l'identique (verif manuelle)")

# ══════════════════════════════════════════════════════════════════
# WEB : carte Categories dans Parametres (apres la carte Taux de frais)
# On insere une carte juste avant la fermeture de la carte frais.
# Strategie : reperer le titre frais et inserer une nouvelle carte apres son </div> de carte.
# Plus simple : inserer juste avant '<div class="card-title">💸 Taux de frais'
# une nouvelle carte categories.
# ══════════════════════════════════════════════════════════════════
if 'id="catCategoriesList"' not in html:
    CARD = '''            <div class="card-title">Categories du catalogue</div>
            <div id="catCategoriesList" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px"></div>
            <div style="display:flex;gap:8px">
              <input type="text" id="newCategoryName" placeholder="Nouvelle categorie..." style="flex:1;padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif" onkeydown="if(event.key==='Enter')addCategoryUI()">
              <button class="btn primary" onclick="addCategoryUI()">+ Ajouter</button>
            </div>
          </div>
          <div class="card">
'''
    anchor = '<div class="card-title">💸 Taux de frais</div>'
    if anchor in html:
        # remonter au <div class="card"> qui contient ce titre, pour inserer une carte AVANT
        idx = html.find(anchor)
        card_start = html.rfind('<div class="card"', 0, idx)
        if card_start != -1:
            new_card = '<div class="card">\n' + CARD
            html = html[:card_start] + new_card + html[card_start:]
            print("WEB-2) carte Categories ajoutee dans Parametres")
        else:
            print("WEB-2) ATTENTION conteneur card frais introuvable")
    else:
        print("WEB-2) ATTENTION titre Taux de frais introuvable")
else:
    print("WEB-2) carte Categories deja presente")

# ══════════════════════════════════════════════════════════════════
# WEB : JS gestion categories + remplissage des selects
# ══════════════════════════════════════════════════════════════════
if "function loadCategories" not in html:
    JS = r"""
<script>
// ===== CATEGORIES =====
var categoriesCache = [];
async function loadCategories(){
  var res = await api('/api/categories');
  if(!res || !res.ok) return;
  categoriesCache = res.data;
  renderCategoriesList();
  fillCategorySelects();
}
function renderCategoriesList(){
  var box = document.getElementById('catCategoriesList');
  if(!box) return;
  box.innerHTML = '';
  if(!categoriesCache.length){ box.innerHTML='<div style="color:var(--text3);font-size:13px">Aucune categorie</div>'; return; }
  categoriesCache.forEach(function(c){
    var row=document.createElement('div');
    row.style.cssText='display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius2)';
    row.innerHTML='<span style="font-size:14px;color:var(--text)">'+c.nom+'</span><button class="btn danger" style="font-size:11px;padding:4px 10px" onclick="deleteCategoryUI('+c.id+",'"+c.nom.replace(/'/g,"\\'")+"'"+')">Supprimer</button>';
    box.appendChild(row);
  });
}
function fillCategorySelects(){
  // datalist du modal catalogue (catCategorieList) si present
  var dl=document.getElementById('catCategorieList');
  if(dl){ dl.innerHTML=''; categoriesCache.forEach(function(c){var o=document.createElement('option');o.value=c.nom;dl.appendChild(o);}); }
  // si tu as un <select id="catCategorie"> ailleurs, on le remplit aussi
  var sel=document.getElementById('catCategorieSelect');
  if(sel){ var prev=sel.value; sel.innerHTML=''; categoriesCache.forEach(function(c){var o=document.createElement('option');o.value=c.nom;o.textContent=c.nom;sel.appendChild(o);}); if(prev)sel.value=prev; }
}
async function addCategoryUI(){
  var inp=document.getElementById('newCategoryName');
  var nom=(inp.value||'').trim();
  if(!nom){ notify('Nom requis','error'); return; }
  var res=await api('/api/categories',{method:'POST',body:{nom:nom}});
  if(res&&res.ok){ inp.value=''; notify('Categorie ajoutee'); await loadCategories(); }
  else notify(res&&res.error?res.error:'Erreur','error');
}
async function deleteCategoryUI(id,nom){
  if(!confirm('Supprimer la categorie "'+nom+'" ?')) return;
  var res=await api('/api/categories/'+id,{method:'DELETE'});
  if(res&&res.ok){ notify('Categorie supprimee'); await loadCategories(); }
  else notify(res&&res.error?res.error:'Suppression impossible','error');
}
</script>
"""
    pos=html.rfind("</script>")
    if pos!=-1:
        at=pos+len("</script>")
        html=html[:at]+"\n"+JS+html[at:]
        print("WEB-3) JS categories ajoute")
    else:
        print("WEB-3) ERREUR </script> introuvable")
else:
    print("WEB-3) JS categories deja present")

# ══════════════════════════════════════════════════════════════════
# WEB : brancher loadCategories() dans initSettings et au demarrage
# ══════════════════════════════════════════════════════════════════
if "loadCategories();" not in html.split("function initSettings")[1][:300] if "function initSettings" in html else False:
    m=re.search(r"(function initSettings\(\)\s*\{)", html)
    if m:
        html=html.replace(m.group(1), m.group(1)+"loadCategories();", 1)
        print("WEB-4) initSettings charge les categories")
    else:
        print("WEB-4) initSettings introuvable")
else:
    print("WEB-4) initSettings deja ok ou loadCategories deja la")

# charger aussi au demarrage pour que le modal catalogue ait les categories
if "function initApp" in html:
    seg = html.split("function initApp")[1][:200]
    if "loadCategories();" not in seg:
        m=re.search(r"(function initApp\(\)\s*\{\s*)", html)
        if m:
            html=html.replace(m.group(1), m.group(1)+"loadCategories();", 1)
            print("WEB-5) initApp charge les categories au demarrage")
    else:
        print("WEB-5) initApp deja ok")

write("web/index.html", html)
print("")
print("=== TERMINE ===")
print("Sidebar defilable + gestion des categories dans Parametres.")
