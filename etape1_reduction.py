#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etape1_reduction.py
Ajoute une REDUCTION dans la caisse :
  - champ "Reduction (EUR)" dans le pied de caisse
  - le total vente affiche le total apres reduction
  - la reduction est repartie sur les articles a l'encaissement
A lancer dans le dossier projet : python etape1_reduction.py
"""
import io, re
p="web/index.html"
html=io.open(p,"r",encoding="utf-8").read()
orig=len(html)

# ── 1) Champ reduction dans le pied de caisse, juste avant la ligne VENTE ──
old_total='<div class="pos-total"><span style="font-size:14px;color:var(--text3);font-weight:500">VENTE</span><span class="amt" id="posTotal">0.00 EUR</span></div>'
red_field='''<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                <span style="font-size:13px;color:var(--text3);flex:1">Reduction</span>
                <input type="number" id="posReduc" value="0" step="1" min="0" style="width:90px;text-align:right;padding:6px 8px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px" oninput="updatePosTotals()">
                <span style="font-size:13px;color:var(--text3)">EUR</span>
              </div>
              '''+old_total
if 'id="posReduc"' not in html and old_total in html:
    html=html.replace(old_total,red_field,1)
    print("1) champ reduction ajoute dans la caisse")
elif 'id="posReduc"' in html:
    print("1) champ reduction deja present")
else:
    print("1) ATTENTION ligne total caisse introuvable")

# ── 2) Fonction utilitaire getReduc + total apres reduction ──
old_getcart="function getCartTotal(){ var t=0; posCart.forEach(function(l){t+=l.prix*l.qty;}); return t; }"
new_getcart="""function getCartTotal(){ var t=0; posCart.forEach(function(l){t+=l.prix*l.qty;}); return t; }
function getReduc(){ var r=document.getElementById('posReduc'); var v=r?(parseFloat(r.value)||0):0; return v<0?0:v; }
function getCartTotalNet(){ var t=getCartTotal()-getReduc(); return t<0?0:t; }"""
if old_getcart in html and "function getReduc(" not in html:
    html=html.replace(old_getcart,new_getcart,1)
    print("2) fonctions getReduc + getCartTotalNet ajoutees")
elif "function getReduc(" in html:
    print("2) deja present")
else:
    print("2) ATTENTION getCartTotal introuvable")

# ── 3) updatePosTotals : afficher le total apres reduction ──
old_disp="var venteTotal=getCartTotal();\n  var el=document.getElementById('posTotal'); if(el)el.textContent=venteTotal.toFixed(2)+' EUR';"
new_disp="""var venteBrut=getCartTotal();var reduc=getReduc();var venteTotal=venteBrut-reduc;if(venteTotal<0)venteTotal=0;
  var el=document.getElementById('posTotal'); if(el)el.textContent=venteTotal.toFixed(2)+' EUR'+(reduc>0?' (-'+reduc.toFixed(2)+')':'');"""
if old_disp in html:
    html=html.replace(old_disp,new_disp,1)
    print("3) affichage total apres reduction")
elif "venteBrut=getCartTotal()" in html:
    print("3) deja present")
else:
    print("3) ATTENTION updatePosTotals introuvable (verif manuelle)")

# ── 4) A l'encaissement : repartir la reduction au prorata sur les articles ──
# On insere, juste apres la recuperation de venteTotal dans posEncaisser, un facteur de reduction.
old_enc="var venteTotal=getCartTotal();\n  var remb=getRemb();"
new_enc="""var venteBrutEnc=getCartTotal();var reducEnc=getReduc();var venteTotal=venteBrutEnc-reducEnc;if(venteTotal<0)venteTotal=0;
  var facteurReduc=(venteBrutEnc>0)?(venteTotal/venteBrutEnc):1;
  var remb=getRemb();"""
if old_enc in html:
    html=html.replace(old_enc,new_enc,1)
    print("4a) calcul du facteur de reduction a l'encaissement")
elif "facteurReduc" in html:
    print("4a) deja present")
else:
    print("4a) ATTENTION debut posEncaisser introuvable")

# Appliquer le facteur au prix unitaire envoye pour chaque article
old_price="prix_unitaire:l.prix,mode_paiement:modeVente"
new_price="prix_unitaire:Math.round(l.prix*facteurReduc*100)/100,mode_paiement:modeVente"
if old_price in html:
    html=html.replace(old_price,new_price,1)
    print("4b) reduction appliquee au prix de chaque article")
elif "l.prix*facteurReduc" in html:
    print("4b) deja present")
else:
    print("4b) ATTENTION prix article dans posEncaisser introuvable")

# ── 5) Remettre la reduction a 0 apres encaissement reussi ──
old_reset="posCart=[];renderPosCart();"
new_reset="posCart=[];var _pr=document.getElementById('posReduc');if(_pr)_pr.value='0';renderPosCart();"
if old_reset in html and "_pr=document.getElementById('posReduc')" not in html:
    html=html.replace(old_reset,new_reset,1)
    print("5) reduction remise a zero apres encaissement")
else:
    print("5) deja present ou ancre absente")

io.open(p,"w",encoding="utf-8").write(html)
print("")
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
