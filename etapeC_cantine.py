#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeC_cantine.py
Bouton Cantine dans le menu de paiement de la caisse :
  - comptant -> simple transaction (compte cantine)
  - credit   -> dette sur le compte cantine du client
A lancer dans le dossier projet : python etapeC_cantine.py
"""
import io
p="web/index.html"
html=io.open(p,"r",encoding="utf-8").read()
orig=len(html)

# 1) Ajouter l'option Cantine dans le menu de paiement
old_opt='<option value="WesternUnion">Western Union</option>'
new_opt='<option value="WesternUnion">Western Union</option><option value="Cantine">🍽 Cantine</option>'
if '<option value="Cantine">🍽 Cantine</option>' not in html and old_opt in html:
    html=html.replace(old_opt,new_opt,1)
    print("1) option Cantine ajoutee au menu de paiement")
elif '<option value="Cantine">🍽 Cantine</option>' in html:
    print("1) option Cantine deja presente")
else:
    print("1) ATTENTION option Western Union non trouvee")

# 2) posEncaisser : compte cantine quand mode=Cantine
old_mv="var modeVente=(posPayMode==='credit')?'Liquide':mode;"
new_mv="var modeVente=(posPayMode==='credit')?(mode==='Cantine'?'Cantine':'Liquide'):mode;var _compteVente=(mode==='Cantine')?'cantine':'euro';"
if old_mv in html:
    html=html.replace(old_mv,new_mv,1)
    print("2) detection cantine dans posEncaisser")
elif "_compteVente=(mode==='Cantine')" in html:
    print("2) deja present")
else:
    print("2) ATTENTION ligne modeVente non trouvee")

# 3) Appliquer le compte cantine au corps de la vente
old_body="frais_deduits:0,compte:'euro',date:_posDate};"
new_body="frais_deduits:0,compte:_compteVente,date:_posDate};"
if old_body in html:
    html=html.replace(old_body,new_body,1)
    print("3) vente: compte cantine applique")
elif "compte:_compteVente,date:_posDate}" in html:
    print("3) deja present")
else:
    print("3) ATTENTION corps vente non trouve")

io.open(p,"w",encoding="utf-8").write(html)
print("")
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
