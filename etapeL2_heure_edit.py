#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeL2_heure_edit.py  (CRLF-safe, web/index.html)
Heure modifiable dans le formulaire d'edition d'une transaction.
A lancer dans le dossier projet : python etapeL2_heure_edit.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()

# 1) Champ heure dans le formulaire d'edition (a cote de la date)
fld_old='<div class="form-group"><label>Date</label><input type="date" id="etDate"></div>'
fld_new=fld_old+'<div class="form-group"><label>Heure</label><input type="time" id="etTime"></div>'
if 'id="etTime"' not in html and fld_old in html:
    html=html.replace(fld_old,fld_new,1)
    print("1) champ Heure ajoute au formulaire d'edition")
elif 'id="etTime"' in html:
    print("1) deja present")
else:
    print("1) ATTENTION champ etDate non trouve")

# 2) openEditTrans : pre-remplir l'heure
oe_old="document.getElementById('etDate').value=t.date?t.date.slice(0,10):new Date().toISOString().slice(0,10);"
oe_new=oe_old+"if(document.getElementById('etTime'))document.getElementById('etTime').value=(t.date&&t.date.length>10)?t.date.slice(11,16):'';"
if oe_old in html and "getElementById('etTime').value=(t.date" not in html:
    html=html.replace(oe_old,oe_new,1)
    print("2) openEditTrans pre-remplit l'heure")
elif "getElementById('etTime').value=(t.date" in html:
    print("2) deja present")
else:
    print("2) ATTENTION ligne etDate dans openEditTrans non trouvee")

# 3) saveEditTrans : combiner date + heure
sv_old="date:document.getElementById('etDate').value};"
sv_new="date:document.getElementById('etDate').value+((document.getElementById('etTime')&&document.getElementById('etTime').value)?(' '+document.getElementById('etTime').value):'')};"
if sv_old in html:
    html=html.replace(sv_old,sv_new,1)
    print("3) saveEditTrans combine date + heure")
elif "etTime')&&document.getElementById('etTime').value" in html:
    print("3) deja present")
else:
    print("3) ATTENTION ligne date dans saveEditTrans non trouvee")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
