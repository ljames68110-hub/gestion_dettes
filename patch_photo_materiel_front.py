#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_photo_materiel_front.py  (Point 4 - interface)
Ajoute une photo dans le modal "entree materiel" (choix + apercu + agrandir) et
affiche une vignette dans la liste des entrees. Sans node. Idempotent, CRLF/LF OK.
A lancer dans le dossier du projet : python patch_photo_materiel_front.py
"""
import os, sys

F = "web/index.html"
MARK = "previewEntreePhoto"

PHOTO_FIELD = (
 '<div class="form-group full"><label>Photo du matériel</label>'
 '<div style="display:flex;align-items:center;gap:10px">'
 '<div id="entreePhotoPreview" style="width:60px;height:60px;border-radius:10px;background:var(--bg4);border:2px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:24px;overflow:hidden;cursor:pointer" onclick="_entreePhotoClick()">\U0001F4E6</div>'
 '<input type="file" id="entreePhoto" accept="image/*" onchange="previewEntreePhoto(this)" style="display:none">'
 '<button type="button" class="btn" style="font-size:12px" onclick="document.getElementById(\'entreePhoto\').click()">\U0001F4F7 Choisir</button>'
 '<button type="button" class="btn" style="font-size:12px;background:var(--bg3);color:var(--red)" onclick="removeEntreePhoto()">Retirer</button>'
 '</div></div>'
)

CH = [
 ("champ photo modal",
  '<div class="form-group full"><label>Notes</label><input type="text" id="entreeNotes" placeholder="Facultatif..."></div>',
  '<div class="form-group full"><label>Notes</label><input type="text" id="entreeNotes" placeholder="Facultatif..."></div>' + PHOTO_FIELD),

 ("reset nouveau materiel",
  "document.getElementById('entreeNotes').value = '';",
  "document.getElementById('entreeNotes').value = '';_entreePhotoData=null;_setEntreePhotoPreview('');"),

 ("remplissage edition",
  "document.getElementById('entreeNotes').value = e.notes || '';",
  "document.getElementById('entreeNotes').value = e.notes || '';_entreePhotoData=e.photo||null;_setEntreePhotoPreview(e.photo||'');"),

 ("corps saveEntree",
  "    notes: document.getElementById('entreeNotes').value,",
  "    notes: document.getElementById('entreeNotes').value,photo:(_entreePhotoData!==null?_entreePhotoData:undefined),"),

 ("vignette liste",
  '+ \'<td style="color:var(--text);font-weight:500">\'+e.description+(estSolde?\' <span style="color:var(--green);font-size:10px">✓ SOLDE</span>\':\'\')+\'</td>\'',
  '+ \'<td style="color:var(--text);font-weight:500">\'+(e.photo?\'<img src="\'+e.photo+\'" onclick="showImageFull(this.src)" style="width:34px;height:34px;object-fit:cover;border-radius:6px;vertical-align:middle;margin-right:8px;cursor:pointer;border:1px solid var(--border)">\':\'\')+e.description+(estSolde?\' <span style="color:var(--green);font-size:10px">✓ SOLDE</span>\':\'\')+\'</td>\''),
]

JS = r"""
/* ===== PHOTO MATERIEL ===== */
var _entreePhotoData = null;
function _setEntreePhotoPreview(src){
  var p=document.getElementById('entreePhotoPreview'); if(!p)return;
  if(src){ p.innerHTML='<img src="'+src+'" style="width:100%;height:100%;object-fit:cover;border-radius:8px">'; }
  else { p.textContent='\U0001F4E6'; }
}
function previewEntreePhoto(input){
  if(!input.files||!input.files[0])return;
  var r=new FileReader();
  r.onload=function(e){ _entreePhotoData=e.target.result; _setEntreePhotoPreview(_entreePhotoData); };
  r.readAsDataURL(input.files[0]);
}
function removeEntreePhoto(){
  _entreePhotoData=''; _setEntreePhotoPreview(''); var i=document.getElementById('entreePhoto'); if(i)i.value='';
}
function _entreePhotoClick(){ if(_entreePhotoData) showImageFull(_entreePhotoData); }
function showImageFull(src){
  if(!src)return;
  var ov=document.getElementById('tkViewer');
  if(!ov){
    ov=document.createElement('div'); ov.id='tkViewer';
    ov.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;z-index:99999;cursor:zoom-out;padding:20px';
    ov.onclick=function(){ov.style.display='none';};
    ov.innerHTML='<img id="tkViewerImg" style="max-width:95%;max-height:95%;object-fit:contain;border-radius:8px">';
    document.body.appendChild(ov);
  }
  document.getElementById('tkViewerImg').src=src; ov.style.display='flex';
}
"""

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)

def main():
    if not os.path.exists(F):
        print("ERREUR : %s introuvable" % F); sys.exit(1)
    t = read(F); eol = "\r\n" if "\r\n" in t else "\n"
    if MARK in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)

    for label, old, new in CH:
        n = t.count(old)
        if n != 1:
            print("  [X] ancre '%s' trouvee %dx (attendu 1) -- rien modifie" % (label, n)); sys.exit(1)
    for label, old, new in CH:
        t = t.replace(old, new, 1)
        print("  [+] %s" % label)

    pos = t.rfind("</body>")
    if pos < 0:
        print("  [X] </body> introuvable"); sys.exit(1)
    block = "<script>" + eol + eol.join(JS.split("\n")) + eol + "</script>" + eol
    t = t[:pos] + block + t[pos:]
    write(F, t)
    print("  [+] module JavaScript injecte")

    if read(F).count(MARK) < 1:
        print("  [!] verification inattendue"); sys.exit(1)
    print("\nTermine (interface photo materiel).")

if __name__ == "__main__":
    main()
