#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etape_stock_catalogue.py
Stock reel sur les articles du catalogue :
  - DB : colonne 'stock' + parametres dans add/update + fonction adjust_stock_catalogue
  - API : stock dans create/update + route adjust-stock
  - WEB : champ "Stock disponible" dans le modal, affichage sur les cartes (alerte si bas),
          decrement automatique a chaque vente en caisse
A lancer dans le dossier projet : python etape_stock_catalogue.py
"""
import io, re
def read(p): return io.open(p,"r",encoding="utf-8").read()
def write(p,c): io.open(p,"w",encoding="utf-8").write(c)

# ════════════════════════════════════════════════════════════════
# DB.PY
# ════════════════════════════════════════════════════════════════
db=read("db.py")

# 1) Ajouter la colonne stock via _ensure_catalogue_table (migration douce)
if "ADD COLUMN stock " not in db and "stock         REAL" not in db:
    # injecter une migration apres la creation de la table catalogue
    anchor='conn.execute("""CREATE TABLE IF NOT EXISTS catalogue ('
    if anchor in db:
        # ajouter, juste apres le commit de _ensure_catalogue_table, une migration ALTER
        m=re.search(r"(def _ensure_catalogue_table\(\):.*?conn\.commit\(\))", db, re.DOTALL)
        if m:
            block=m.group(1)+'''
    # migration : colonne stock (quantite disponible)
    with get_conn() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(catalogue)").fetchall()}
        if "stock" not in cols:
            conn.execute("ALTER TABLE catalogue ADD COLUMN stock REAL DEFAULT 0")
            conn.commit()'''
            db=db.replace(m.group(1), block, 1)
            print("DB-1) migration colonne stock ajoutee")
        else:
            print("DB-1) ATTENTION _ensure_catalogue_table introuvable")
    else:
        print("DB-1) ATTENTION table catalogue introuvable")
else:
    print("DB-1) colonne stock deja prevue")

# 2) add_catalogue_item : accepter stock
old_add='def add_catalogue_item(nom, categorie, description, prix_vente, prix_achat, unite, stock_min):'
new_add='def add_catalogue_item(nom, categorie, description, prix_vente, prix_achat, unite, stock_min, stock=0):'
if old_add in db:
    db=db.replace(old_add,new_add,1)
    # adapter l'INSERT
    db=db.replace(
        '"""INSERT INTO catalogue (nom,categorie,description,prix_vente,prix_achat,unite,stock_min)\n               VALUES (?,?,?,?,?,?,?)""",\n            (nom.strip(), categorie, description, prix_vente, prix_achat, unite, stock_min)',
        '"""INSERT INTO catalogue (nom,categorie,description,prix_vente,prix_achat,unite,stock_min,stock)\n               VALUES (?,?,?,?,?,?,?,?)""",\n            (nom.strip(), categorie, description, prix_vente, prix_achat, unite, stock_min, stock)'
    )
    print("DB-2) add_catalogue_item accepte stock")
elif "stock=0):" in db:
    print("DB-2) add_catalogue_item deja modifie")
else:
    print("DB-2) ATTENTION add_catalogue_item introuvable")

# 3) update_catalogue_item : accepter stock
old_upd='def update_catalogue_item(item_id, nom, categorie, description, prix_vente, prix_achat, unite, stock_min):'
new_upd='def update_catalogue_item(item_id, nom, categorie, description, prix_vente, prix_achat, unite, stock_min, stock=None):'
if old_upd in db:
    db=db.replace(old_upd,new_upd,1)
    # adapter l'UPDATE pour inclure stock si fourni
    old_sql='''            """UPDATE catalogue SET nom=?,categorie=?,description=?,prix_vente=?,
               prix_achat=?,unite=?,stock_min=? WHERE id=?""",
            (nom.strip(), categorie, description, prix_vente, prix_achat, unite, stock_min, item_id)'''
    new_sql='''            """UPDATE catalogue SET nom=?,categorie=?,description=?,prix_vente=?,
               prix_achat=?,unite=?,stock_min=?, stock=COALESCE(?,stock) WHERE id=?""",
            (nom.strip(), categorie, description, prix_vente, prix_achat, unite, stock_min, stock, item_id)'''
    if old_sql in db:
        db=db.replace(old_sql,new_sql,1)
        print("DB-3) update_catalogue_item accepte stock")
    else:
        print("DB-3) ATTENTION UPDATE catalogue non trouve a l'identique")
elif "stock=None):" in db:
    print("DB-3) update_catalogue_item deja modifie")
else:
    print("DB-3) ATTENTION update_catalogue_item introuvable")

# 4) fonction adjust_stock_catalogue
if "def adjust_stock_catalogue" not in db:
    db=db.rstrip()+'''

def adjust_stock_catalogue(item_id, delta):
    """Ajoute (ou retire si negatif) une quantite au stock d'un article."""
    _ensure_catalogue_table()
    with get_conn() as conn:
        conn.execute("UPDATE catalogue SET stock = COALESCE(stock,0) + ? WHERE id=?", (float(delta), item_id))
        conn.commit()
'''
    print("DB-4) fonction adjust_stock_catalogue ajoutee")
else:
    print("DB-4) adjust_stock_catalogue deja presente")

write("db.py", db)

# ════════════════════════════════════════════════════════════════
# API.PY
# ════════════════════════════════════════════════════════════════
api=read("api.py")

# create : ajouter stock
if "stock_min    = float(data.get(\"stock_min\", 0))," in api and "stock        = float(data.get(\"stock\", 0))," not in api:
    api=api.replace(
        'stock_min    = float(data.get("stock_min", 0)),\n    )\n    return ok(db.get_catalogue_item(iid)), 201',
        'stock_min    = float(data.get("stock_min", 0)),\n        stock        = float(data.get("stock", 0)),\n    )\n    return ok(db.get_catalogue_item(iid)), 201'
    )
    print("API-1) create catalogue: stock ajoute")
else:
    print("API-1) create deja ok ou structure differente")

# update : ajouter stock (avec None si absent pour ne pas ecraser)
if "stock_min    = float(data.get(\"stock_min\", 0)),\n    )\n    return ok(db.get_catalogue_item(iid))" in api and "stock        = (float(data[\"stock\"])" not in api:
    api=api.replace(
        'stock_min    = float(data.get("stock_min", 0)),\n    )\n    return ok(db.get_catalogue_item(iid))',
        'stock_min    = float(data.get("stock_min", 0)),\n        stock        = (float(data["stock"]) if "stock" in data and data["stock"] is not None else None),\n    )\n    return ok(db.get_catalogue_item(iid))'
    )
    print("API-2) update catalogue: stock ajoute")
else:
    print("API-2) update deja ok ou structure differente")

# route adjust-stock
if "/api/catalogue/<int:iid>/adjust-stock" not in api:
    routes='''
@app.route("/api/catalogue/<int:iid>/adjust-stock", methods=["POST"])
@require_auth
def catalogue_adjust_stock(iid):
    data = request.json or {}
    delta = float(data.get("delta", 0))
    db.adjust_stock_catalogue(iid, delta)
    return ok(db.get_catalogue_item(iid))

'''
    idx=api.find('@app.route("/", defaults')
    if idx!=-1:
        api=api[:idx]+routes+api[idx:]
        print("API-3) route adjust-stock ajoutee")
    else:
        print("API-3) ATTENTION route racine introuvable")
else:
    print("API-3) route adjust-stock deja presente")

write("api.py", api)

# ════════════════════════════════════════════════════════════════
# WEB
# ════════════════════════════════════════════════════════════════
html=read("web/index.html")

# 1) Champ "Stock disponible" dans le modal, apres Stock minimum
old_smin='<div class="form-group"><label>Stock minimum</label><input type="number" id="catStockMin" value="0" step="0.5" min="0"></div>'
new_smin=old_smin+'\n      <div class="form-group"><label>Stock disponible</label><input type="number" id="catStock" value="0" step="0.5" min="0"></div>'
if 'id="catStock"' not in html and old_smin in html:
    html=html.replace(old_smin,new_smin,1)
    print("WEB-1) champ Stock disponible ajoute au modal")
elif 'id="catStock"' in html:
    print("WEB-1) champ stock deja present")
else:
    print("WEB-1) ATTENTION champ stock minimum introuvable")

# 2) saveCatalogueItem : envoyer stock
old_body="stock_min:parseFloat(document.getElementById('catStockMin').value)||0};"
new_body="stock_min:parseFloat(document.getElementById('catStockMin').value)||0,stock:parseFloat(document.getElementById('catStock').value)||0};"
if old_body in html:
    html=html.replace(old_body,new_body,1)
    print("WEB-2) saveCatalogueItem envoie stock")
elif "stock:parseFloat(document.getElementById('catStock')" in html:
    print("WEB-2) deja ok")
else:
    print("WEB-2) ATTENTION body saveCatalogueItem introuvable")

# 3) openEditCatalogue : pre-remplir le stock
old_edit="document.getElementById('catStockMin').value=parseFloat(it.stock_min||0).toFixed(1);"
new_edit=old_edit+"document.getElementById('catStock').value=parseFloat(it.stock||0).toFixed(1);"
if old_edit in html and "catStock').value=parseFloat(it.stock" not in html:
    html=html.replace(old_edit,new_edit,1)
    print("WEB-3) openEditCatalogue pre-remplit le stock")
else:
    print("WEB-3) deja ok ou ancre absente")

# 4) openAddCatalogue : remettre stock a 0
old_add0="document.getElementById('catStockMin').value='0';"
new_add0=old_add0+"if(document.getElementById('catStock'))document.getElementById('catStock').value='0';"
if old_add0 in html and "catStock')).value='0'" not in html and "catStock')).value=\"0\"" not in html:
    html=html.replace(old_add0,new_add0,1)
    print("WEB-4) openAddCatalogue remet stock a 0")
else:
    print("WEB-4) deja ok ou ancre absente")

# 5) Affichage du stock sur les cartes : on injecte un badge dans renderCatalogue
#    On remplace le bloc qui affiche la categorie en haut de carte pour y ajouter le stock.
#    Plus simple : ajouter le stock juste apres le nom dans card.innerHTML.
old_card="+'<span style=\"font-size:10px;background:var(--bg4);border:1px solid var(--border);border-radius:20px;padding:2px 8px;color:var(--text3)\">'+it.categorie+'</span></div>'"
new_card="+'<span style=\"font-size:10px;background:var(--bg4);border:1px solid var(--border);border-radius:20px;padding:2px 8px;color:var(--text3)\">'+it.categorie+'</span></div>'+'<div style=\"font-size:11px;margin-bottom:8px;color:'+((parseFloat(it.stock||0)<=parseFloat(it.stock_min||0))?'var(--red)':'var(--text3)')+'\">Stock : '+parseFloat(it.stock||0).toFixed(0)+' '+(it.unite==='gramme'?'g':it.unite==='litre'?'L':'pcs')+((parseFloat(it.stock||0)<=parseFloat(it.stock_min||0))?' (bas)':'')+'</div>'"
if old_card in html:
    html=html.replace(old_card,new_card,1)
    print("WEB-5) stock affiche sur les cartes catalogue")
elif "Stock : '+parseFloat(it.stock||0)" in html:
    print("WEB-5) deja ok")
else:
    print("WEB-5) ATTENTION structure carte catalogue introuvable")

# 6) Caisse : decrement du stock apres encaissement reussi
#    Dans posEncaisser, juste apres "posCart=[]" reset, on decrémente AVANT de vider.
#    On accroche au succes : "notify('Encaisse : '" puis on decrémente la liste avant reset.
hook="notify('Encaisse : '+msg.join(' + '));"
dec="notify('Encaisse : '+msg.join(' + '));\n    posCart.forEach(function(l){api('/api/catalogue/'+l.id+'/adjust-stock',{method:'POST',body:{delta:-l.qty}}).catch(function(){});});"
if hook in html and "adjust-stock" not in html.split("posEncaisser")[1][:4000] if "posEncaisser" in html else False:
    html=html.replace(hook,dec,1)
    print("WEB-6) decrement stock apres vente en caisse")
elif "adjust-stock" in html:
    print("WEB-6) decrement deja present")
else:
    # fallback : remplacer quand meme si hook present
    if hook in html:
        html=html.replace(hook,dec,1)
        print("WEB-6) decrement stock apres vente en caisse (fallback)")
    else:
        print("WEB-6) ATTENTION hook succes caisse introuvable")

write("web/index.html", html)
print("")
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
