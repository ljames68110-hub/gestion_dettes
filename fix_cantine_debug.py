#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_cantine_debug.py
  1) Desactive la console DevTools (debug=False dans main.py)
  2) Ajoute reellement l'option Cantine au menu de paiement de la CAISSE
A lancer dans le dossier projet : python fix_cantine_debug.py
"""
import io

# 1) main.py : debug=False
mp="main.py"
m=io.open(mp,encoding="utf-8").read()
if "debug=True" in m:
    m=m.replace("debug=True","debug=False")
    io.open(mp,"w",encoding="utf-8").write(m)
    print("1) main.py : DevTools desactive (debug=False)")
else:
    print("1) main.py : debug deja desactive")

# 2) Cantine dans le menu posMode (caisse)
p="web/index.html"
h=io.open(p,encoding="utf-8").read()
old='<option value="Liquide">Liquide</option><option value="Virement">Virement</option><option value="PCS">PCS</option><option value="Paysafecard">Paysafecard</option><option value="WesternUnion">Western Union</option>'
new=old+'<option value="Cantine">🍽 Cantine</option>'
if new in h:
    print("2) Cantine deja dans le menu de la caisse")
elif old in h:
    h=h.replace(old,new,1)
    io.open(p,"w",encoding="utf-8").write(h)
    print("2) Cantine ajoutee au menu de la caisse")
else:
    print("2) ATTENTION menu posMode non trouve")

print("Balises script : %d / %d" % (h.count("<script>"),h.count("</script>")))
