#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_caisse_date.py
  1) Champ date dans la caisse (aujourd'hui par defaut, modifiable)
  2) Envoi de la date a l'encaissement (vente + remboursement)
  3) Correction du sens de "j'absorbe les frais" selon la regle :
     cochee  -> j'absorbe -> credit total (frais_deduits=0)
     decochee-> client paye -> credit reduit + frais dus (frais_deduits=1)
A lancer dans le dossier projet : python fix_caisse_date.py
"""
import io, re
p="web/index.html"
html=io.open(p,"r",encoding="utf-8").read()
orig=len(html)

# ── 1) Ajouter le champ date dans la topbar caisse (apres posSearch) ──
old_search='<input class="pos-search" id="posSearch" placeholder="Rechercher un article..." oninput="renderPosGrid(this.value)">'
date_field='<input class="pos-search" id="posSearch" placeholder="Rechercher un article..." oninput="renderPosGrid(this.value)">\n              <input type="date" id="posDate" class="pos-search" style="width:160px" title="Date de la vente">'
if 'id="posDate"' not in html and old_search in html:
    html=html.replace(old_search,date_field,1)
    print("1) champ date ajoute dans la caisse")
elif 'id="posDate"' in html:
    print("1) champ date deja present")
else:
    print("1) ATTENTION champ recherche caisse introuvable")

# ── 2) Initialiser la date du jour dans initCaisse ──
m=re.search(r"(function initCaisse\(\)\{)", html)
if m and "posDate" not in html.split("function initCaisse")[1][:400]:
    inject=m.group(1)+"var _pd=document.getElementById('posDate');if(_pd&&!_pd.value){_pd.value=new Date().toISOString().slice(0,10);}"
    html=html.replace(m.group(1),inject,1)
    print("2) date du jour pre-remplie a l'ouverture de la caisse")
else:
    print("2) initCaisse deja ok ou introuvable")

# ── 3) Vente : envoyer la date ──
old_vente="var body={client_id:cid,type:'debit',motif:l.nom,quantite:l.qty,unite:l.unite,prix_unitaire:l.prix,mode_paiement:modeVente,notes:(posPayMode==='cash'?'[CAISSE PAYE] ':'[CAISSE CREDIT] ')+'Vente caisse',frais_deduits:0,compte:'euro'};"
new_vente="var _posDate=(document.getElementById('posDate')&&document.getElementById('posDate').value)?document.getElementById('posDate').value:undefined;var body={client_id:cid,type:'debit',motif:l.nom,quantite:l.qty,unite:l.unite,prix_unitaire:l.prix,mode_paiement:modeVente,notes:(posPayMode==='cash'?'[CAISSE PAYE] ':'[CAISSE CREDIT] ')+'Vente caisse',frais_deduits:0,compte:'euro',date:_posDate};"
if old_vente in html:
    html=html.replace(old_vente,new_vente,1)
    print("3) vente: date envoyee")
elif "_posDate=" in html:
    print("3) vente: date deja envoyee")
else:
    print("3) ATTENTION corps vente caisse introuvable")

# ── 4) Remboursement : corriger le sens des frais + envoyer la date ──
old_absorbe="var absorbe=document.getElementById('posRembFrais')?(document.getElementById('posRembFrais').checked?1:0):1;"
new_absorbe="var jAbsorbe=document.getElementById('posRembFrais')?document.getElementById('posRembFrais').checked:true;var fraisDeduits=jAbsorbe?0:1;"
if old_absorbe in html:
    html=html.replace(old_absorbe,new_absorbe,1)
    print("4a) sens 'j'absorbe' corrige (cochee=credit total)")
elif "var fraisDeduits=jAbsorbe?0:1;" in html:
    print("4a) sens deja corrige")
else:
    print("4a) ATTENTION ligne absorbe introuvable")

old_bodyR="var bodyR={client_id:cid,type:'credit',motif:'Remboursement',quantite:1,unite:'piece',prix_unitaire:remb,mode_paiement:mode,notes:'[CAISSE] Remboursement dette',frais_deduits:absorbe,compte:'euro'};"
new_bodyR="var bodyR={client_id:cid,type:'credit',motif:'Remboursement',quantite:1,unite:'piece',prix_unitaire:remb,mode_paiement:mode,notes:'[CAISSE] Remboursement dette',frais_deduits:fraisDeduits,compte:'euro',date:_posDate};"
if old_bodyR in html:
    html=html.replace(old_bodyR,new_bodyR,1)
    print("4b) remboursement: frais corriges + date envoyee")
elif "frais_deduits:fraisDeduits" in html:
    print("4b) remboursement deja corrige")
else:
    print("4b) ATTENTION corps remboursement introuvable")

io.open(p,"w",encoding="utf-8").write(html)
print("")
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
