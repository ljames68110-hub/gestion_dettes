#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etape2_tabac.py
Types de tabac avec prix et stock reglables (dans Parametres).
  - DB : table types_tabac (nom, prix, stock) + 3 types par defaut
  - API : lister / ajouter / modifier / supprimer
  - WEB : carte "Tabac (types, prix, stock)" dans Parametres
A lancer dans le dossier projet : python etape2_tabac.py
"""
import io, re

def read(p): return io.open(p,"r",encoding="utf-8").read()
def write(p,c): io.open(p,"w",encoding="utf-8").write(c)

# ════════════════════════════════════════════════════════════════
# DB.PY
# ════════════════════════════════════════════════════════════════
db=read("db.py")
if "_ensure_types_tabac_table" not in db:
    block='''

# -- TYPES DE TABAC -----------------------------------------------------------
def _ensure_types_tabac_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS types_tabac (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            prix REAL DEFAULT 0,
            stock REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        n = conn.execute("SELECT COUNT(*) FROM types_tabac").fetchone()[0]
        if n == 0:
            for nom in ["Paquet de tabac","Paquet de blonde","Pot de tabac"]:
                try: conn.execute("INSERT INTO types_tabac (nom,prix,stock) VALUES (?,0,0)", (nom,))
                except: pass
        conn.commit()

def get_types_tabac():
    _ensure_types_tabac_table()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM types_tabac ORDER BY nom").fetchall()
    return [dict(r) for r in rows]

def add_type_tabac(nom, prix=0):
    _ensure_types_tabac_table()
    nom=(nom or "").strip()
    if not nom: raise ValueError("Nom requis")
    with get_conn() as conn:
        ex=conn.execute("SELECT COUNT(*) FROM types_tabac WHERE nom=?", (nom,)).fetchone()[0]
        if ex: raise ValueError("Type deja existant")
        cur=conn.execute("INSERT INTO types_tabac (nom,prix,stock) VALUES (?,?,0)", (nom, float(prix or 0)))
        conn.commit()
        return cur.lastrowid

def update_type_tabac(tid, nom=None, prix=None, stock=None):
    _ensure_types_tabac_table()
    with get_conn() as conn:
        cur=conn.execute("SELECT * FROM types_tabac WHERE id=?", (tid,)).fetchone()
        if not cur: return
        nom2 = (nom if nom is not None else cur["nom"])
        prix2 = (float(prix) if prix is not None else cur["prix"])
        stock2 = (float(stock) if stock is not None else cur["stock"])
        conn.execute("UPDATE types_tabac SET nom=?,prix=?,stock=? WHERE id=?", (nom2,prix2,stock2,tid))
        conn.commit()

def delete_type_tabac(tid):
    _ensure_types_tabac_table()
    with get_conn() as conn:
        conn.execute("DELETE FROM types_tabac WHERE id=?", (tid,))
        conn.commit()

def adjust_stock_tabac(tid, delta):
    """Ajoute (ou retire si negatif) une quantite au stock d'un type."""
    _ensure_types_tabac_table()
    with get_conn() as conn:
        conn.execute("UPDATE types_tabac SET stock = stock + ? WHERE id=?", (float(delta), tid))
        conn.commit()
'''
    db=db.rstrip()+"\n"+block
    write("db.py", db)
    print("DB) table types_tabac + fonctions ajoutees")
else:
    print("DB) types_tabac deja present")

# ════════════════════════════════════════════════════════════════
# API.PY
# ════════════════════════════════════════════════════════════════
api=read("api.py")
if "/api/types-tabac" not in api:
    routes='''
# -- TYPES DE TABAC -----------------------------------------------------------
@app.route("/api/types-tabac")
@require_auth
def types_tabac_list():
    return ok(db.get_types_tabac())

@app.route("/api/types-tabac", methods=["POST"])
@require_auth
def types_tabac_create():
    data=request.json or {}
    try:
        tid=db.add_type_tabac(data.get("nom",""), data.get("prix",0))
    except ValueError as e:
        return err(str(e))
    return ok({"id":tid}), 201

@app.route("/api/types-tabac/<int:tid>", methods=["PUT"])
@require_auth
def types_tabac_update(tid):
    data=request.json or {}
    db.update_type_tabac(tid,
        nom=data.get("nom"),
        prix=data.get("prix"),
        stock=data.get("stock"))
    return ok({"id":tid})

@app.route("/api/types-tabac/<int:tid>", methods=["DELETE"])
@require_auth
def types_tabac_delete(tid):
    db.delete_type_tabac(tid)
    return ok({"deleted":tid})

'''
    # inserer apres la derniere route categories (avant la route racine)
    idx=api.find('@app.route("/", defaults')
    if idx!=-1:
        api=api[:idx]+routes+api[idx:]
        print("API) routes types-tabac ajoutees")
    else:
        print("API) ATTENTION route racine introuvable")
    write("api.py", api)
else:
    print("API) routes types-tabac deja presentes")

# ════════════════════════════════════════════════════════════════
# WEB : carte dans Parametres + JS
# ════════════════════════════════════════════════════════════════
html=read("web/index.html")

# Inserer une carte AVANT la carte Categories
anchor='            <div class="card-title">Categories du catalogue</div>'
if 'id="typesTabacList"' not in html and anchor in html:
    idx=html.find(anchor)
    card_start=html.rfind('<div class="card"',0,idx)
    if card_start!=-1:
        CARD=('<div class="card">\n'
            '            <div class="card-title">🚬 Tabac (types, prix, stock)</div>\n'
            '            <div id="typesTabacList" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px"></div>\n'
            '            <div style="display:flex;gap:8px">\n'
            '              <input type="text" id="newTabacNom" placeholder="Nouveau type..." style="flex:1;padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif">\n'
            '              <input type="number" id="newTabacPrix" placeholder="Prix" step="0.5" min="0" style="width:90px;padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px">\n'
            '              <button class="btn primary" onclick="addTypeTabac()">+ Ajouter</button>\n'
            '            </div>\n'
            '          </div>\n          ')
        html=html[:card_start]+CARD+html[card_start:]
        print("WEB-1) carte Tabac ajoutee dans Parametres")
    else:
        print("WEB-1) ATTENTION conteneur carte Categories introuvable")
elif 'id="typesTabacList"' in html:
    print("WEB-1) carte Tabac deja presente")
else:
    print("WEB-1) ATTENTION ancre carte Categories introuvable")

# JS de gestion
if "function loadTypesTabac" not in html:
    JS=r"""
<script>
// ===== TYPES DE TABAC =====
var typesTabacCache=[];
async function loadTypesTabac(){
  var res=await api('/api/types-tabac');
  if(!res||!res.ok)return;
  typesTabacCache=res.data;
  renderTypesTabac();
}
function renderTypesTabac(){
  var box=document.getElementById('typesTabacList');
  if(!box)return;
  box.innerHTML='';
  if(!typesTabacCache.length){box.innerHTML='<div style="color:var(--text3);font-size:13px">Aucun type</div>';return;}
  typesTabacCache.forEach(function(t){
    var row=document.createElement('div');
    row.style.cssText='display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius2)';
    row.innerHTML='<span style="flex:1;font-size:14px;color:var(--text)">'+t.nom+'</span>'
      +'<span style="font-size:11px;color:var(--text3)">Prix</span>'
      +'<input type="number" value="'+parseFloat(t.prix).toFixed(2)+'" step="0.5" min="0" style="width:70px;text-align:right;padding:4px 6px;border-radius:6px;border:1px solid var(--border);background:var(--bg2);color:var(--text);font-size:13px" onchange="saveTypeTabac('+t.id+',this.value,null)">'
      +'<span style="font-size:11px;color:var(--text3)">Stock</span>'
      +'<input type="number" value="'+parseFloat(t.stock).toFixed(0)+'" step="1" style="width:60px;text-align:right;padding:4px 6px;border-radius:6px;border:1px solid var(--border);background:var(--bg2);color:var(--text);font-size:13px" onchange="saveTypeTabac('+t.id+',null,this.value)">'
      +'<button class="btn danger" style="font-size:11px;padding:4px 8px" onclick="deleteTypeTabac('+t.id+')">X</button>';
    box.appendChild(row);
  });
}
async function addTypeTabac(){
  var nom=(document.getElementById('newTabacNom').value||'').trim();
  var prix=parseFloat(document.getElementById('newTabacPrix').value)||0;
  if(!nom){notify('Nom requis','error');return;}
  var res=await api('/api/types-tabac',{method:'POST',body:{nom:nom,prix:prix}});
  if(res&&res.ok){document.getElementById('newTabacNom').value='';document.getElementById('newTabacPrix').value='';notify('Type ajoute');await loadTypesTabac();}
  else notify(res&&res.error?res.error:'Erreur','error');
}
async function saveTypeTabac(id,prix,stock){
  var body={};
  if(prix!==null)body.prix=parseFloat(prix)||0;
  if(stock!==null)body.stock=parseFloat(stock)||0;
  var res=await api('/api/types-tabac/'+id,{method:'PUT',body:body});
  if(res&&res.ok){notify('Tabac mis a jour');await loadTypesTabac();}
  else notify('Erreur','error');
}
async function deleteTypeTabac(id){
  if(!confirm('Supprimer ce type de tabac ?'))return;
  await api('/api/types-tabac/'+id,{method:'DELETE'});
  notify('Type supprime');await loadTypesTabac();
}
</script>
"""
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+"\n"+JS+html[at:]
    print("WEB-2) JS types tabac injecte")
else:
    print("WEB-2) JS types tabac deja present")

# Charger dans initSettings
m=re.search(r"(function initSettings\(\)\{)", html)
if m and "loadTypesTabac()" not in html:
    html=html.replace(m.group(1), m.group(1)+"loadTypesTabac();", 1)
    print("WEB-3) initSettings charge les types tabac")
else:
    print("WEB-3) deja ok ou introuvable")

write("web/index.html", html)
print("")
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
