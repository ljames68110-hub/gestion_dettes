#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeI_photos.py  (CRLF-safe)
Photos sur les articles du catalogue :
  - db.py  : migration colonne photo
  - api.py : endpoint POST /api/catalogue/<id>/photo
  - web    : champ photo (redimensionnee dans le navigateur), miniature sur les cartes,
             pre-affichage en edition, conservation si pas de nouvelle photo
A lancer dans le dossier projet : python etapeI_photos.py
"""
import io, re

# ───────────────────────── db.py : migration colonne photo ─────────────────────────
dp="db.py"
db=io.open(dp,encoding="utf-8",newline="").read()
eol_db="\r\n" if "\r\n" in db else "\n"
if 'ADD COLUMN photo' in db:
    print("DB) colonne photo deja prevue")
else:
    pat=re.compile(r'(conn\.execute\("ALTER TABLE catalogue ADD COLUMN stock REAL DEFAULT 0"\))(\r?\n\s*conn\.commit\(\))')
    m=pat.search(db)
    if m:
        add=(eol_db+'        if "photo" not in cols:'+eol_db
             +'            conn.execute("ALTER TABLE catalogue ADD COLUMN photo TEXT DEFAULT \'\'")'+eol_db
             +'            conn.commit()')
        db=db[:m.end()]+add+db[m.end():]
        io.open(dp,"w",encoding="utf-8",newline="").write(db)
        print("DB) migration colonne photo ajoutee")
    else:
        print("DB) ATTENTION bloc migration stock non trouve")

# ───────────────────────── api.py : endpoint photo ─────────────────────────
ap="api.py"
api=io.open(ap,encoding="utf-8",newline="").read()
eol_api="\r\n" if "\r\n" in api else "\n"
if "/api/catalogue/<int:iid>/photo" in api:
    print("API) endpoint photo deja present")
else:
    route=('@app.route("/api/catalogue/<int:iid>/photo", methods=["POST"])'+eol_api
           +'@require_auth'+eol_api
           +'def catalogue_set_photo(iid):'+eol_api
           +'    data = request.json or {}'+eol_api
           +'    photo = data.get("photo", "")'+eol_api
           +'    db._ensure_catalogue_table()'+eol_api
           +'    with db.get_conn() as conn:'+eol_api
           +'        conn.execute("UPDATE catalogue SET photo=? WHERE id=?", (photo, iid))'+eol_api
           +'        conn.commit()'+eol_api
           +'    return ok(db.get_catalogue_item(iid))'+eol_api+eol_api)
    needle='@app.route("/", defaults'
    i=api.find(needle)
    if i!=-1:
        api=api[:i]+route+api[i:]
        io.open(ap,"w",encoding="utf-8",newline="").write(api)
        print("API) endpoint /api/catalogue/<id>/photo ajoute")
    else:
        print("API) ATTENTION route racine non trouvee")

# ───────────────────────── web : formulaire + cartes + JS ─────────────────────────
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in html else "\n"

# 1) champ photo dans le formulaire (apres "Stock disponible")
stock_field='<div class="form-group"><label>Stock disponible</label><input type="number" id="catStock" value="0" step="0.5" min="0"></div>'
photo_field=stock_field+'<div class="form-group full"><label>Photo (optionnel)</label><input type="file" id="catPhotoFile" accept="image/*" onchange="onCatPhotoPick(this)" style="padding:8px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px;width:100%"><img id="catPhotoPreview" style="display:none;max-width:140px;max-height:140px;margin-top:8px;border-radius:8px;border:1px solid var(--border)"></div>'
if 'id="catPhotoFile"' not in html and stock_field in html:
    html=html.replace(stock_field,photo_field,1)
    print("WEB-1) champ photo ajoute au formulaire")
elif 'id="catPhotoFile"' in html:
    print("WEB-1) deja present")
else:
    print("WEB-1) ATTENTION champ Stock disponible non trouve")

# 2) miniature sur les cartes
card_anchor="card.innerHTML='<div style=\"display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px\">"
card_new="card.innerHTML=(it.photo?'<img src=\"'+it.photo+'\" style=\"width:100%;height:90px;object-fit:cover;border-radius:8px;margin-bottom:10px\">':'')+'<div style=\"display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px\">"
if "it.photo?'<img" not in html and card_anchor in html:
    html=html.replace(card_anchor,card_new,1)
    print("WEB-2) miniature ajoutee sur les cartes")
elif "it.photo?'<img" in html:
    print("WEB-2) deja present")
else:
    print("WEB-2) ATTENTION debut de carte catalogue non trouve")

# 3) saveCatalogueItem : upload photo apres succes
save_anchor="if(res&&res.ok){document.getElementById('modalCatalogue').classList.remove('open');notify(id?'Article modifie':'Article cree');await loadCatalogue();}"
save_new="if(res&&res.ok){var _sid=id||(res.data&&res.data.id);if(_sid&&window._catPhotoData){try{await api('/api/catalogue/'+_sid+'/photo',{method:'POST',body:{photo:window._catPhotoData}});}catch(e){}}window._catPhotoData=null;document.getElementById('modalCatalogue').classList.remove('open');notify(id?'Article modifie':'Article cree');await loadCatalogue();}"
if "window._catPhotoData" not in html and save_anchor in html:
    html=html.replace(save_anchor,save_new,1)
    print("WEB-3) saveCatalogueItem envoie la photo")
elif "window._catPhotoData" in html.split("async function saveCatalogueItem")[1][:600] if "async function saveCatalogueItem" in html else False:
    print("WEB-3) deja present")
elif save_anchor not in html:
    print("WEB-3) ATTENTION bloc succes saveCatalogueItem non trouve")
else:
    print("WEB-3) deja present")

# 4) JS : resize + pick + observer de pre-affichage
if "function resizeImageFile" not in html:
    JS=r"""
<script>
// ===== PHOTOS ARTICLES =====
function resizeImageFile(file,maxDim){return new Promise(function(resolve){var reader=new FileReader();reader.onload=function(e){var img=new Image();img.onload=function(){var w=img.width,h=img.height;if(w>h){if(w>maxDim){h=Math.round(h*maxDim/w);w=maxDim;}}else{if(h>maxDim){w=Math.round(w*maxDim/h);h=maxDim;}}var c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(img,0,0,w,h);try{resolve(c.toDataURL('image/jpeg',0.7));}catch(err){resolve(null);}};img.onerror=function(){resolve(null);};img.src=e.target.result;};reader.onerror=function(){resolve(null);};reader.readAsDataURL(file);});}
function onCatPhotoPick(input){if(!input.files||!input.files[0]){window._catPhotoData=null;return;}resizeImageFile(input.files[0],420).then(function(b64){window._catPhotoData=b64;var prev=document.getElementById('catPhotoPreview');if(prev&&b64){prev.src=b64;prev.style.display='block';}});}
(function(){var modal=document.getElementById('modalCatalogue');if(!modal)return;new MutationObserver(function(){if(modal.classList.contains('open')){window._catPhotoData=null;var pf=document.getElementById('catPhotoFile');if(pf)pf.value='';var prev=document.getElementById('catPhotoPreview');var id=(document.getElementById('catId')||{}).value;var item=id?(catalogueCache||[]).find(function(c){return String(c.id)===String(id);}):null;if(prev){if(item&&item.photo){prev.src=item.photo;prev.style.display='block';}else{prev.removeAttribute('src');prev.style.display='none';}}}}).observe(modal,{attributes:true,attributeFilter:['class']});})();
</script>
"""
    JS=JS.replace("\n",eol)
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+eol+JS+html[at:]
    print("WEB-4) JS photo (resize + apercu) ajoute")
else:
    print("WEB-4) deja present")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
