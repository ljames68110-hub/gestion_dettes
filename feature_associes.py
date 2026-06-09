#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feature_associes.py
Associes : contacts vendus au prix d'achat, geres dans Parametres,
ranges a part des clients normaux, dette/credit suivie comme un client.
A lancer dans le dossier projet : python feature_associes.py
"""
import io, re
def read(p): return io.open(p,"r",encoding="utf-8").read()
def write(p,c): io.open(p,"w",encoding="utf-8").write(c)

# ════════════════════════════════════════════════════════════════
# DB.PY
# ════════════════════════════════════════════════════════════════
db=read("db.py")

# 1) add_client accepte associe
old_add='''def add_client(nom, email=None, tel=None, notes=None):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clients (nom,email,tel,notes) VALUES (?,?,?,?)",
            (nom, email or "", tel or "", notes or "")
        )
        conn.commit()
        return cur.lastrowid'''
new_add='''def add_client(nom, email=None, tel=None, notes=None, associe=0):
    _ensure_associe_column()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clients (nom,email,tel,notes,associe) VALUES (?,?,?,?,?)",
            (nom, email or "", tel or "", notes or "", int(associe or 0))
        )
        conn.commit()
        return cur.lastrowid'''
if old_add in db:
    db=db.replace(old_add,new_add,1)
    print("DB-1) add_client accepte associe")
elif "associe=0):" in db:
    print("DB-1) add_client deja modifie")
else:
    print("DB-1) ATTENTION add_client non trouve")

# 2) get_clients renvoie associe
old_get='''def get_clients():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, tel, notes FROM clients ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]'''
new_get='''def get_clients():
    _ensure_associe_column()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, tel, notes, COALESCE(associe,0) as associe FROM clients ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]'''
if old_get in db:
    db=db.replace(old_get,new_get,1)
    print("DB-2) get_clients renvoie associe")
elif "COALESCE(associe,0) as associe FROM clients ORDER BY nom" in db:
    print("DB-2) get_clients deja modifie")
else:
    print("DB-2) ATTENTION get_clients non trouve")

# 3) _ensure_associe_column + get_associes
if "_ensure_associe_column" not in db or "def get_associes" not in db:
    block='''

# -- ASSOCIES -----------------------------------------------------------------
def _ensure_associe_column():
    with get_conn() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(clients)").fetchall()}
        if "associe" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN associe INTEGER DEFAULT 0")
            conn.commit()

def get_associes():
    _ensure_associe_column()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, tel, notes, COALESCE(associe,0) as associe FROM clients WHERE associe=1 ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]
'''
    db=db.rstrip()+"\n"+block
    print("DB-3) _ensure_associe_column + get_associes ajoutes")
else:
    print("DB-3) deja present")

write("db.py", db)

# ════════════════════════════════════════════════════════════════
# API.PY
# ════════════════════════════════════════════════════════════════
api=read("api.py")
if "/api/associes" not in api:
    routes='''
# -- ASSOCIES -----------------------------------------------------------------
@app.route("/api/associes")
@require_auth
def associes_list():
    return ok(db.get_associes())

@app.route("/api/associes", methods=["POST"])
@require_auth
def associes_create():
    data = request.json or {}
    nom = (data.get("nom") or "").strip()
    if not nom:
        return err("Nom requis")
    cid = db.add_client(nom=nom, associe=1)
    return ok({"id": cid}), 201

'''
    idx=api.find('@app.route("/", defaults')
    if idx!=-1:
        api=api[:idx]+routes+api[idx:]
        print("API) routes associes ajoutees")
    else:
        print("API) ATTENTION route racine introuvable")
    write("api.py", api)
else:
    print("API) routes associes deja presentes")

# ════════════════════════════════════════════════════════════════
# WEB
# ════════════════════════════════════════════════════════════════
html=read("web/index.html")

# 1) Flag global posIsAssocie
old_g="var posCart=[];var posPayMode='cash';"
new_g="var posCart=[];var posPayMode='cash';var posIsAssocie=false;"
if old_g in html and "var posIsAssocie" not in html:
    html=html.replace(old_g,new_g,1)
    print("WEB-1) flag posIsAssocie ajoute")
elif "var posIsAssocie" in html:
    print("WEB-1) deja present")
else:
    print("WEB-1) ATTENTION declaration posCart non trouvee")

# 2) addToCart : stocker prixVente + prixAchat
old_atc="function addToCart(it){var line=posCart.find(function(l){return l.id===it.id;});if(line){line.qty+=1;}else{posCart.push({id:it.id,nom:it.nom,prix:parseFloat(it.prix_vente)||0,qty:1,unite:it.unite||'piece'});}renderPosCart();}"
new_atc="function addToCart(it){var line=posCart.find(function(l){return l.id===it.id;});if(line){line.qty+=1;}else{var pv=parseFloat(it.prix_vente)||0;var pa=parseFloat(it.prix_achat)||0;posCart.push({id:it.id,nom:it.nom,prixVente:pv,prixAchat:pa,prix:(posIsAssocie?pa:pv),qty:1,unite:it.unite||'piece'});}renderPosCart();}"
if old_atc in html:
    html=html.replace(old_atc,new_atc,1)
    print("WEB-2) addToCart stocke prix d'achat")
elif "prixVente:pv,prixAchat:pa" in html:
    print("WEB-2) deja present")
else:
    print("WEB-2) ATTENTION addToCart non trouve")

# 3) onPosClientChange : detecter associe + re-tarifer
old_opc='''function onPosClientChange(){
  var cid=parseInt(document.getElementById('posClient').value);
  var box=document.getElementById('posDetteBox');'''
new_opc='''function onPosClientChange(){
  var cid=parseInt(document.getElementById('posClient').value);
  posIsAssocie=false;var _selc=(clientsCache||[]).find(function(c){return c.id===cid;});if(_selc&&_selc.associe){posIsAssocie=true;}posCart.forEach(function(l){if(l.prixVente!=null)l.prix=(posIsAssocie&&l.prixAchat!=null)?l.prixAchat:l.prixVente;});
  var box=document.getElementById('posDetteBox');'''
if old_opc in html:
    html=html.replace(old_opc,new_opc,1)
    print("WEB-3) onPosClientChange re-tarife pour associe")
elif "posIsAssocie=true;}posCart.forEach" in html:
    print("WEB-3) deja present")
else:
    print("WEB-3) ATTENTION onPosClientChange non trouve")

# 4) initCaisse : libelle (associe) dans le menu client
old_fill="(clientsCache||[]).forEach(function(c){var o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);});"
new_fill="(clientsCache||[]).forEach(function(c){var o=document.createElement('option');o.value=c.id;o.textContent=c.nom+(c.associe?' (associe)':'');sel.appendChild(o);});"
if old_fill in html:
    html=html.replace(old_fill,new_fill,1)
    print("WEB-4) caisse: associes labellises dans le menu")
elif "(c.associe?' (associe)':'')" in html:
    print("WEB-4) deja present")
else:
    print("WEB-4) ATTENTION remplissage posClient non trouve")

# 5) renderClients : filtrer les associes
old_rc="function renderClients(list){"
new_rc="function renderClients(list){list=(list||[]).filter(function(c){return !c.associe;});"
if old_rc in html and "filter(function(c){return !c.associe;});" not in html.split("function renderClients(list){")[1][:80]:
    html=html.replace(old_rc,new_rc,1)
    print("WEB-5) renderClients filtre les associes")
else:
    print("WEB-5) deja present ou introuvable")

# 6) populateClientSelects : filtrer les associes
old_pcs="clientsCache.forEach(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);});"
new_pcs="clientsCache.filter(function(c){return !c.associe;}).forEach(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);});"
if old_pcs in html:
    html=html.replace(old_pcs,new_pcs,1)
    print("WEB-6) selecteurs clients filtrent les associes")
elif "filter(function(c){return !c.associe;}).forEach(c=>" in html:
    print("WEB-6) deja present")
else:
    print("WEB-6) ATTENTION populateClientSelects non trouve")

# 7) Carte Associes dans Parametres (avant la carte Categories)
anchor='            <div class="card-title">Categories du catalogue</div>'
if 'id="associesList"' not in html and anchor in html:
    idx=html.find(anchor)
    card_start=html.rfind('<div class="card"',0,idx)
    if card_start!=-1:
        CARD=('<div class="card">\n'
            '            <div class="card-title">🤝 Associes (vente au prix coutant)</div>\n'
            '            <div id="associesList" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px"></div>\n'
            '            <div style="display:flex;gap:8px">\n'
            '              <input type="text" id="newAssocieName" placeholder="Nom de l\'associe..." style="flex:1;padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif">\n'
            '              <button class="btn primary" onclick="addAssocieUI()">+ Ajouter</button>\n'
            '            </div>\n'
            '          </div>\n          ')
        html=html[:card_start]+CARD+html[card_start:]
        print("WEB-7) carte Associes ajoutee dans Parametres")
    else:
        print("WEB-7) ATTENTION conteneur carte Categories introuvable")
elif 'id="associesList"' in html:
    print("WEB-7) carte Associes deja presente")
else:
    print("WEB-7) ATTENTION ancre Categories introuvable")

# 8) JS associes
if "function loadAssocies" not in html:
    JS=r"""
<script>
// ===== ASSOCIES =====
var associesCache=[];
async function loadAssocies(){
  var res=await api('/api/associes');
  if(!res||!res.ok)return;
  associesCache=res.data;
  renderAssociesList();
}
function renderAssociesList(){
  var box=document.getElementById('associesList');
  if(!box)return;
  box.innerHTML='';
  if(!associesCache.length){box.innerHTML='<div style="color:var(--text3);font-size:13px">Aucun associe</div>';return;}
  associesCache.forEach(function(a){
    var row=document.createElement('div');
    row.style.cssText='display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius2)';
    row.innerHTML='<span style="font-size:14px;color:var(--text)">'+a.nom+'</span>'+'<button class="btn danger" style="font-size:11px;padding:4px 10px" onclick="deleteAssocieUI('+a.id+')">Supprimer</button>';
    box.appendChild(row);
  });
}
async function addAssocieUI(){
  var inp=document.getElementById('newAssocieName');var nom=(inp.value||'').trim();
  if(!nom){notify('Nom requis','error');return;}
  var res=await api('/api/associes',{method:'POST',body:{nom:nom}});
  if(res&&res.ok){inp.value='';notify('Associe ajoute');await loadAssocies();if(typeof loadClients==='function')await loadClients();}
  else notify(res&&res.error?res.error:'Erreur','error');
}
async function deleteAssocieUI(id){
  if(!confirm('Supprimer cet associe ?'))return;
  var res=await api('/api/clients/'+id,{method:'DELETE'});
  if(res&&res.ok){notify('Associe supprime');await loadAssocies();if(typeof loadClients==='function')await loadClients();}
  else notify('Erreur','error');
}
</script>
"""
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+"\n"+JS+html[at:]
    print("WEB-8) JS associes injecte")
else:
    print("WEB-8) deja present")

# 9) initSettings charge les associes
if "function initSettings(){loadAssocies();" not in html:
    html=html.replace("function initSettings(){","function initSettings(){loadAssocies();",1)
    print("WEB-9) initSettings charge les associes")
else:
    print("WEB-9) deja present")

write("web/index.html", html)
print("")
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
