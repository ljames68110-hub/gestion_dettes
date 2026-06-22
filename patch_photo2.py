t=open("web/index.html",encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in t else "\n"
SELECT='<select class="pos-client" id="posClient" onchange="onPosClientChange()"><option value="">-- Choisir un client (obligatoire) --</option></select>'
LB="function openPhotoLightbox(src){if(!src)return;var ov=document.getElementById('photoLightbox');if(!ov){ov=document.createElement('div');ov.id='photoLightbox';ov.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;z-index:99999;cursor:zoom-out';ov.onclick=function(){ov.style.display='none';};var im=document.createElement('img');im.id='photoLightboxImg';im.style.cssText='max-width:92vw;max-height:92vh;border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,0.6)';ov.appendChild(im);document.body.appendChild(ov);}var img=document.getElementById('photoLightboxImg');if(img)img.src=src;ov.style.display='flex';}"
E=[
("fiche img",
 '\'<img src="\'+clientData.photo+\'" style="width:56px;height:56px;object-fit:cover;border-radius:50%">\'',
 '\'<img src="\'+clientData.photo+\'" onclick="openPhotoLightbox(this.src)" style="width:72px;height:72px;object-fit:cover;border-radius:50%;cursor:pointer">\'',
 'openPhotoLightbox(this.src)" style="width:72px'),
("caisse html",
 SELECT,
 SELECT+'<div id="posClientPhotoWrap" style="display:none;margin-top:8px;text-align:center"><img id="posClientPhoto" src="" onclick="openPhotoLightbox(this.src)" style="max-width:110px;max-height:110px;border-radius:12px;border:2px solid var(--gold);object-fit:cover;cursor:pointer"></div>',
 'id="posClientPhotoWrap"'),
("onclient photo",
 "if(_selc&&_selc.associe){posIsAssocie=true;}",
 "if(_selc&&_selc.associe){posIsAssocie=true;}var _phw=document.getElementById('posClientPhotoWrap');if(_phw){if(_selc&&_selc.photo){var _phi=document.getElementById('posClientPhoto');if(_phi)_phi.src=_selc.photo;_phw.style.display='block';}else{_phw.style.display='none';}}",
 "var _phw=document.getElementById('posClientPhotoWrap')"),
("lightbox fn",
 "/* auto-verification des mises a jour (apres connexion seulement) */",
 LB+eol+"/* auto-verification des mises a jour (apres connexion seulement) */",
 "function openPhotoLightbox"),
]
for name,o,n,guard in E:
    if guard in t: print(name,": deja"); continue
    if t.count(o)==1: t=t.replace(o,n,1); print(name,": OK")
    else: print(name,": KO",t.count(o))
open("web/index.html","w",encoding="utf-8",newline="").write(t)
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.17"' in u: print("ver: deja")
elif u.count('APP_VERSION = "2.16"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.16"','APP_VERSION = "2.17"',1)); print("ver -> 2.17")
else: print("ver KO")
