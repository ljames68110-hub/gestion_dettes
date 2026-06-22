#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_photos_caisse.py
 - resizeImageFile : recadre la photo en CARRE (center-crop) -> rendu uniforme.
 - renderPosGrid   : affiche la photo de l'article dans la caisse (cadre cover).
A lancer dans le dossier projet : python patch_photos_caisse.py
"""
import os
def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)

OLD_RESIZE = r'''function resizeImageFile(file,maxDim){return new Promise(function(resolve){var reader=new FileReader();reader.onload=function(e){var img=new Image();img.onload=function(){var w=img.width,h=img.height;if(w>h){if(w>maxDim){h=Math.round(h*maxDim/w);w=maxDim;}}else{if(h>maxDim){w=Math.round(w*maxDim/h);h=maxDim;}}var c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(img,0,0,w,h);try{resolve(c.toDataURL('image/jpeg',0.7));}catch(err){resolve(null);}};img.onerror=function(){resolve(null);};img.src=e.target.result;};reader.onerror=function(){resolve(null);};reader.readAsDataURL(file);});}'''

NEW_RESIZE = r'''function resizeImageFile(file,maxDim){return new Promise(function(resolve){var reader=new FileReader();reader.onload=function(e){var img=new Image();img.onload=function(){var side=Math.min(img.width,img.height);var sx=Math.round((img.width-side)/2);var sy=Math.round((img.height-side)/2);var out=Math.min(maxDim,side);var c=document.createElement('canvas');c.width=out;c.height=out;c.getContext('2d').drawImage(img,sx,sy,side,side,0,0,out,out);try{resolve(c.toDataURL('image/jpeg',0.8));}catch(err){resolve(null);}};img.onerror=function(){resolve(null);};img.src=e.target.result;};reader.onerror=function(){resolve(null);};reader.readAsDataURL(file);});}'''

OLD_POS = r'''card.innerHTML='<div class="pcat">'+it.categorie+'</div><div class="pname">'+it.nom+'</div><div class="pprice">'+parseFloat(it.prix_vente).toFixed(2)+' EUR<span style="font-size:10px;color:var(--text3)"> /'+u+'</span></div>';'''

NEW_POS = r'''card.innerHTML=(it.photo?'<img src="'+it.photo+'" style="width:100%;height:80px;object-fit:cover;border-radius:8px;margin-bottom:6px">':'')+'<div class="pcat">'+it.categorie+'</div><div class="pname">'+it.nom+'</div><div class="pprice">'+parseFloat(it.prix_vente).toFixed(2)+' EUR<span style="font-size:10px;color:var(--text3)"> /'+u+'</span></div>';'''

def patch_web(path="web/index.html"):
    t=read(path)
    # 1) resize carre
    if "var side=Math.min(img.width,img.height)" in t:
        print("web : resizeImageFile deja en carre, saute")
    elif OLD_RESIZE in t:
        t=t.replace(OLD_RESIZE, NEW_RESIZE, 1)
        print("web : resizeImageFile -> recadrage carre OK")
    else:
        print("ATTENTION web : resizeImageFile introuvable (format inattendu)")
    # 2) photo dans la grille caisse (les 2 definitions identiques)
    if "object-fit:cover;border-radius:8px;margin-bottom:6px" in t:
        print("web : photo caisse deja presente, saute")
    elif OLD_POS in t:
        n=t.count(OLD_POS)
        t=t.replace(OLD_POS, NEW_POS)
        print("web : photo article ajoutee dans la caisse OK (%d occurrence(s))" % n)
    else:
        print("ATTENTION web : ligne renderPosGrid introuvable")
    write(path,t)

if __name__=="__main__":
    if os.path.exists("web/index.html"): patch_web()
    else: print("ATTENTION web/index.html introuvable")
    print("=== TERMINE ===")
