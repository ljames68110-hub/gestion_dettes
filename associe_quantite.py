#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
associe_quantite.py
Quand un associe est selectionne, cliquer un article demande la quantite
(en g ou pieces) et l'ajoute au prix coutant.
A lancer dans le dossier projet : python associe_quantite.py
"""
import io
p="web/index.html"
html=io.open(p,"r",encoding="utf-8").read()

old="function addToCart(it){var line=posCart.find(function(l){return l.id===it.id;});if(line){line.qty+=1;}else{var pv=parseFloat(it.prix_vente)||0;var pa=parseFloat(it.prix_achat)||0;posCart.push({id:it.id,nom:it.nom,prixVente:pv,prixAchat:pa,prix:(posIsAssocie?pa:pv),qty:1,unite:it.unite||'piece'});}renderPosCart();}"

new=("function addToCart(it){"
     "var uLabel=(it.unite==='gramme'?'g':it.unite==='litre'?'L':'pieces');"
     "var line=posCart.find(function(l){return l.id===it.id;});"
     "if(line){"
       "if(posIsAssocie){var q=prompt('Quantite a vendre ('+uLabel+') pour '+it.nom+' :',line.qty);if(q===null)return;var qn=parseFloat(q);if(isNaN(qn)||qn<=0)return;line.qty=qn;}"
       "else{line.qty+=1;}"
     "}else{"
       "var pv=parseFloat(it.prix_vente)||0;var pa=parseFloat(it.prix_achat)||0;var qty=1;"
       "if(posIsAssocie){var q2=prompt('Quantite a vendre ('+uLabel+') pour '+it.nom+' :','1');if(q2===null)return;var qn2=parseFloat(q2);if(isNaN(qn2)||qn2<=0)return;qty=qn2;}"
       "posCart.push({id:it.id,nom:it.nom,prixVente:pv,prixAchat:pa,prix:(posIsAssocie?pa:pv),qty:qty,unite:it.unite||'piece'});"
     "}renderPosCart();}")

if old in html:
    html=html.replace(old,new,1)
    io.open(p,"w",encoding="utf-8").write(html)
    print("OK : la caisse demande la quantite pour un associe (prix coutant)")
elif "Quantite a vendre ('+uLabel+')" in html:
    print("Deja present")
else:
    print("ATTENTION : addToCart non trouve a l'identique")

print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
