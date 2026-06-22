#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeI3_supprimer_photo.py  (CRLF-safe, web/index.html)
Bouton "Supprimer la photo" dans le formulaire d'article.
  - '' = effacer la photo, null = ne pas changer, base64 = nouvelle photo
A lancer dans le dossier projet : python etapeI3_supprimer_photo.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in html else "\n"

# 1) Bouton supprimer apres l'apercu
img_old='<img id="catPhotoPreview" style="display:none;max-width:140px;max-height:140px;margin-top:8px;border-radius:8px;border:1px solid var(--border)"></div>'
img_new='<img id="catPhotoPreview" style="display:none;max-width:140px;max-height:140px;margin-top:8px;border-radius:8px;border:1px solid var(--border)"><button type="button" class="btn" id="catPhotoRemoveBtn" onclick="clearCatPhoto()" style="display:none;margin-top:8px;font-size:12px;padding:6px 10px">🗑 Supprimer la photo</button></div>'
if 'id="catPhotoRemoveBtn"' not in html and img_old in html:
    html=html.replace(img_old,img_new,1)
    print("1) bouton Supprimer la photo ajoute")
elif 'id="catPhotoRemoveBtn"' in html:
    print("1) deja present")
else:
    print("1) ATTENTION apercu photo non trouve")

# 2) onCatPhotoPick : afficher le bouton supprimer
pick_old="var prev=document.getElementById('catPhotoPreview');if(prev&&b64){prev.src=b64;prev.style.display='block';}"
pick_new="var prev=document.getElementById('catPhotoPreview');if(prev&&b64){prev.src=b64;prev.style.display='block';}var rb=document.getElementById('catPhotoRemoveBtn');if(rb&&b64)rb.style.display='inline-flex';"
if pick_old in html and "catPhotoRemoveBtn')" not in html.split("function onCatPhotoPick")[1][:400] if "function onCatPhotoPick" in html else False:
    html=html.replace(pick_old,pick_new,1)
    print("2) onCatPhotoPick affiche le bouton")
elif "function onCatPhotoPick" in html and "catPhotoRemoveBtn" in html.split("function onCatPhotoPick")[1][:400]:
    print("2) deja present")
elif pick_old not in html:
    print("2) ATTENTION onCatPhotoPick non trouve")
else:
    print("2) deja present")

# 3) Observer : afficher/cacher le bouton selon la photo existante
obs_old="if(item&&item.photo){prev.src=item.photo;prev.style.display='block';}else{prev.removeAttribute('src');prev.style.display='none';}"
obs_new=obs_old+"var _rb=document.getElementById('catPhotoRemoveBtn');if(_rb)_rb.style.display=(item&&item.photo)?'inline-flex':'none';"
if obs_old in html and "_rb=document.getElementById('catPhotoRemoveBtn')" not in html:
    html=html.replace(obs_old,obs_new,1)
    print("3) observer gere le bouton")
elif "_rb=document.getElementById('catPhotoRemoveBtn')" in html:
    print("3) deja present")
else:
    print("3) ATTENTION observer non trouve")

# 4) saveCatalogueItem : uploader aussi si photo vide (= effacer)
save_old="if(_sid&&window._catPhotoData){"
save_new="if(_sid&&window._catPhotoData!==null&&typeof window._catPhotoData!=='undefined'){"
if save_old in html:
    html=html.replace(save_old,save_new,1)
    print("4) saveCatalogueItem gere l'effacement")
elif "window._catPhotoData!==null" in html:
    print("4) deja present")
else:
    print("4) ATTENTION condition photo dans saveCatalogueItem non trouvee")

# 5) Fonction clearCatPhoto
if "function clearCatPhoto" not in html:
    JS=r"""
<script>
function clearCatPhoto(){
  window._catPhotoData='';
  var prev=document.getElementById('catPhotoPreview');
  if(prev){prev.removeAttribute('src');prev.style.display='none';}
  var pf=document.getElementById('catPhotoFile');
  if(pf)pf.value='';
  var rb=document.getElementById('catPhotoRemoveBtn');
  if(rb)rb.style.display='none';
  if(typeof notify==='function')notify('Photo retiree — clique sur Enregistrer pour valider');
}
</script>
"""
    JS=JS.replace("\n",eol)
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+eol+JS+html[at:]
    print("5) fonction clearCatPhoto ajoutee")
else:
    print("5) deja presente")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
