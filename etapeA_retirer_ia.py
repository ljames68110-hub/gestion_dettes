#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeA_retirer_ia.py
Retire l'Assistant IA de l'interface :
  - entree sidebar
  - appel dans goPage
  - entree dans TITLES
On laisse les fonctions JS (inactives) pour ne rien casser.
A lancer dans le dossier projet : python etapeA_retirer_ia.py
"""
import io, re
p="web/index.html"
html=io.open(p,"r",encoding="utf-8").read()
orig=len(html)

# 1) Entree sidebar
nav='''    <div class="nav-item" onclick="goPage('assistant',this)"><span class="nav-icon">🤖</span> Assistant IA</div>\n'''
if nav in html:
    html=html.replace(nav,'',1)
    print("1) entree sidebar Assistant IA retiree")
else:
    # tolerant aux espaces
    m=re.search(r'\s*<div class="nav-item" onclick="goPage\(\'assistant\',this\)">.*?</div>\n', html)
    if m:
        html=html.replace(m.group(0),'\n',1)
        print("1) entree sidebar retiree (tolerant)")
    else:
        print("1) ATTENTION entree sidebar introuvable")

# 2) Appel dans goPage
call="  if(name==='assistant')initAssistant();\n"
if call in html:
    html=html.replace(call,'',1)
    print("2) appel initAssistant retire de goPage")
else:
    call2="if(name==='assistant')initAssistant();"
    if call2 in html:
        html=html.replace(call2,'',1)
        print("2) appel initAssistant retire (compact)")
    else:
        print("2) ATTENTION appel goPage introuvable")

# 3) Entree TITLES
if "assistant:'Assistant IA'," in html:
    html=html.replace("assistant:'Assistant IA',","",1)
    print("3) entree TITLES retiree")
elif "assistant:'Assistant IA'" in html:
    html=html.replace("assistant:'Assistant IA'","",1)
    print("3) entree TITLES retiree (sans virgule)")
else:
    print("3) ATTENTION entree TITLES introuvable")

# 4) Cacher la page assistant (au cas ou) - on la laisse mais inaccessible
# (pas de suppression du bloc HTML pour eviter tout risque)

io.open(p,"w",encoding="utf-8").write(html)
print("")
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
