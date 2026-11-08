#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fiche_client_front.py
Ajoute Batiment / Etage / Type (Exterieur ou CD) dans le formulaire client et
dans l'affichage de la fiche. Sans node. Idempotent (ancres mono-ligne).
A lancer dans le dossier projet : python patch_fiche_client_front.py
"""
import os, sys

F = "web/index.html"
MARK = "cBatiment"

CH = [
 # (label, old, new)
 ("formulaire",
  '<div class="form-group"><label>Téléphone</label><input type="tel" id="cTel" placeholder="06 12 34 56 78"></div>',
  '<div class="form-group"><label>Téléphone</label><input type="tel" id="cTel" placeholder="06 12 34 56 78"></div>'
  '<div class="form-group"><label>Bâtiment</label><input type="text" id="cBatiment" placeholder="Ex : A, B, 3..."></div>'
  '<div class="form-group"><label>Étage</label><input type="text" id="cEtage" placeholder="Ex : 2"></div>'
  '<div class="form-group"><label>Type</label><select id="cType" style="width:100%;padding:10px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px"><option value="exterieur">Extérieur</option><option value="cd">CD</option></select></div>'),

 ("reset nouveau client",
  "document.getElementById('cId').value='';['cNom','cEmail','cTel','cNotes'].forEach(id=>document.getElementById(id).value='');",
  "document.getElementById('cId').value='';['cNom','cEmail','cTel','cNotes','cBatiment','cEtage'].forEach(id=>{var _e=document.getElementById(id);if(_e)_e.value='';});if(document.getElementById('cType'))document.getElementById('cType').value='exterieur';"),

 ("remplissage edition",
  "document.getElementById('cTel').value=c.tel||'';document.getElementById('cNotes').value=c.notes||'';",
  "document.getElementById('cTel').value=c.tel||'';document.getElementById('cNotes').value=c.notes||'';if(document.getElementById('cBatiment'))document.getElementById('cBatiment').value=c.batiment||'';if(document.getElementById('cEtage'))document.getElementById('cEtage').value=c.etage||'';if(document.getElementById('cType'))document.getElementById('cType').value=c.type_client||'exterieur';"),

 ("corps saveClient",
  "const body={nom,email:document.getElementById('cEmail').value,tel:document.getElementById('cTel').value,notes:document.getElementById('cNotes').value,photo:_photoData||undefined};",
  "const body={nom,email:document.getElementById('cEmail').value,tel:document.getElementById('cTel').value,notes:document.getElementById('cNotes').value,batiment:(document.getElementById('cBatiment')||{}).value||'',etage:(document.getElementById('cEtage')||{}).value||'',type_client:(document.getElementById('cType')||{}).value||'exterieur',photo:_photoData||undefined};"),

 ("affichage fiche",
  "+ '<div style=\"font-size:12px;color:var(--text3);margin-top:2px\">'+(clientData.email||'')+(clientData.email&&clientData.tel?' · ':'')+(clientData.tel||'')+'</div>'",
  "+ '<div style=\"font-size:12px;color:var(--text3);margin-top:2px\">'+(clientData.email||'')+(clientData.email&&clientData.tel?' · ':'')+(clientData.tel||'')+'</div>'"
  "+ '<div style=\"font-size:12px;color:var(--text3);margin-top:4px\">'+((clientData.type_client===\"cd\")?'<span style=\"background:var(--gold2);color:#1a1a1a;padding:1px 6px;border-radius:4px;font-weight:700\">CD</span>':'<span style=\"background:var(--bg3);color:var(--text2);padding:1px 6px;border-radius:4px\">Extérieur</span>')+((clientData.batiment||clientData.etage)?(' · Bât '+(clientData.batiment||'-')+' · Ét. '+(clientData.etage||'-')):'')+'</div>'"),
]

def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)

def main():
    if not os.path.exists(F):
        print("ERREUR : %s introuvable" % F); sys.exit(1)
    t=read(F)
    if MARK in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)
    # verifs
    for label,old,new in CH:
        n=t.count(old)
        if n!=1:
            print("  [X] ancre '%s' trouvee %dx (attendu 1) -- rien modifie" % (label,n)); sys.exit(1)
    # application
    for label,old,new in CH:
        t=t.replace(old,new,1)
        print("  [+] %s" % label)
    write(F,t)
    if read(F).count(MARK)<1:
        print("  [!] verification inattendue"); sys.exit(1)
    print("\nTermine (interface fiche client).")

if __name__=="__main__":
    main()
