#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeL_heure_caisse.py  (CRLF-safe, web/index.html)
Heure de la transaction dans la caisse :
  - champ heure a cote de la date
  - heure du jour par defaut
  - l'heure est enregistree avec la transaction (date = 'YYYY-MM-DD HH:MM')
  - fmtDate affiche l'heure quand elle est presente
A lancer dans le dossier projet : python etapeL_heure_caisse.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()

# 1) fmtDate : afficher l'heure si presente
fd_old="function fmtDate(d){return d?d.slice(0,10).split('-').reverse().join('/'):'—';}"
fd_new="function fmtDate(d){if(!d)return '—';var s=d.slice(0,10).split('-').reverse().join('/');if(d.length>10){var h=d.slice(11,16);if(h)s+=' '+h;}return s;}"
if fd_old in html:
    html=html.replace(fd_old,fd_new,1)
    print("1) fmtDate affiche l'heure si presente")
elif "if(d.length>10){var h=d.slice(11,16)" in html:
    print("1) deja present")
else:
    print("1) ATTENTION fmtDate non trouve a l'identique")

# 2) champ heure a cote de la date dans la caisse
pd_old='<input type="date" id="posDate" class="pos-search" style="width:160px" title="Date de la vente">'
pd_new=pd_old+'<input type="time" id="posTime" class="pos-search" style="width:110px" title="Heure de la vente">'
if 'id="posTime"' not in html and pd_old in html:
    html=html.replace(pd_old,pd_new,1)
    print("2) champ heure ajoute dans la caisse")
elif 'id="posTime"' in html:
    print("2) deja present")
else:
    print("2) ATTENTION champ posDate non trouve")

# 3) initCaisse : heure du jour par defaut
ic_old="var _pd=document.getElementById('posDate');if(_pd&&!_pd.value){_pd.value=new Date().toISOString().slice(0,10);}"
ic_new=ic_old+"var _pt=document.getElementById('posTime');if(_pt&&!_pt.value){var _now=new Date();_pt.value=(''+_now.getHours()).padStart(2,'0')+':'+(''+_now.getMinutes()).padStart(2,'0');}"
if ic_old in html and "id('posTime')" not in html.split("function initCaisse")[1][:600] if "function initCaisse" in html else False:
    html=html.replace(ic_old,ic_new,1)
    print("3) initCaisse : heure du jour par defaut")
elif "function initCaisse" in html and "getElementById('posTime')" in html.split("function initCaisse")[1][:800]:
    print("3) deja present")
elif ic_old not in html:
    print("3) ATTENTION ligne date par defaut (initCaisse) non trouvee")
else:
    print("3) deja present")

# 4) posEncaisser : combiner date + heure
pe_old="var _posDate=(document.getElementById('posDate')&&document.getElementById('posDate').value)?document.getElementById('posDate').value:undefined;"
pe_new="var _posTimeEl=document.getElementById('posTime');var _posDate=(document.getElementById('posDate')&&document.getElementById('posDate').value)?(document.getElementById('posDate').value+((_posTimeEl&&_posTimeEl.value)?(' '+_posTimeEl.value):'')):undefined;"
if pe_old in html:
    html=html.replace(pe_old,pe_new,1)
    print("4) posEncaisser combine date + heure")
elif "_posTimeEl=document.getElementById('posTime')" in html:
    print("4) deja present")
else:
    print("4) ATTENTION ligne _posDate (posEncaisser) non trouvee")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
