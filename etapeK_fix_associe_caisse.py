#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeK_fix_associe_caisse.py  (CRLF-safe, web/index.html)
  1) addToCart : supprime le prompt() (KO dans PyWebView) -> associe = ajout au prix coutant, qty ajustable dans le panier
  2) populateClientSelects : inclut les associes dans le menu de la page Soldes & Dettes
A lancer dans le dossier projet : python etapeK_fix_associe_caisse.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()

# 1) addToCart sans prompt
add_old="function addToCart(it){var uLabel=(it.unite==='gramme'?'g':it.unite==='litre'?'L':'pieces');var line=posCart.find(function(l){return l.id===it.id;});if(line){if(posIsAssocie){var q=prompt('Quantite a vendre ('+uLabel+') pour '+it.nom+' :',line.qty);if(q===null)return;var qn=parseFloat(q);if(isNaN(qn)||qn<=0)return;line.qty=qn;}else{line.qty+=1;}}else{var pv=parseFloat(it.prix_vente)||0;var pa=parseFloat(it.prix_achat)||0;var qty=1;if(posIsAssocie){var q2=prompt('Quantite a vendre ('+uLabel+') pour '+it.nom+' :','1');if(q2===null)return;var qn2=parseFloat(q2);if(isNaN(qn2)||qn2<=0)return;qty=qn2;}posCart.push({id:it.id,nom:it.nom,prixVente:pv,prixAchat:pa,prix:(posIsAssocie?pa:pv),qty:qty,unite:it.unite||'piece'});}renderPosCart();}"
add_new="function addToCart(it){var line=posCart.find(function(l){return l.id===it.id;});if(line){line.qty+=1;}else{var pv=parseFloat(it.prix_vente)||0;var pa=parseFloat(it.prix_achat)||0;posCart.push({id:it.id,nom:it.nom,prixVente:pv,prixAchat:pa,prix:(posIsAssocie?pa:pv),qty:1,unite:it.unite||'piece'});}renderPosCart();}"
if add_old in html:
    html=html.replace(add_old,add_new,1)
    print("1) addToCart corrige (plus de prompt, associe au prix coutant)")
elif "function addToCart(it){var line=posCart.find" in html:
    print("1) deja corrige")
else:
    print("1) ATTENTION addToCart d'origine non trouve")

# 2) Inclure les associes dans le menu Soldes
sel_old="clientsCache.filter(function(c){return !c.associe;}).forEach(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=c.nom;sel.appendChild(o);});"
sel_new="var includeAssoc=(id==='soldeClientSel');clientsCache.filter(function(c){return includeAssoc||!c.associe;}).forEach(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=c.nom+((c.associe&&includeAssoc)?' (associé)':'');sel.appendChild(o);});"
if sel_old in html:
    html=html.replace(sel_old,sel_new,1)
    print("2) page Soldes : associes inclus dans le menu")
elif "var includeAssoc=(id==='soldeClientSel')" in html:
    print("2) deja present")
else:
    print("2) ATTENTION populateClientSelects non trouve a l'identique")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
