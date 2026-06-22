#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeI2_photo_facture.py  (CRLF-safe, api.py uniquement)
Ajoute la vignette de l'article (photo du catalogue) sur les factures :
  - facture simple (_build_facture_html)
  - facture groupee (_build_facture_groupee_html)
A lancer dans le dossier projet : python etapeI2_photo_facture.py
"""
import io
ap="api.py"
api=io.open(ap,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in api else "\n"

# 1) Helper _catalogue_photo_map (avant la route racine)
if "def _catalogue_photo_map" not in api:
    helper=('def _catalogue_photo_map():'+eol
            +'    m = {}'+eol
            +'    try:'+eol
            +'        for c in db.get_catalogue():'+eol
            +'            if c.get("photo"):'+eol
            +'                m[c.get("nom")] = c.get("photo")'+eol
            +'    except Exception:'+eol
            +'        pass'+eol
            +'    return m'+eol+eol)
    i=api.find('@app.route("/", defaults')
    if i!=-1:
        api=api[:i]+helper+api[i:]
        print("1) helper _catalogue_photo_map ajoute")
    else:
        print("1) ATTENTION route racine non trouvee")
else:
    print("1) helper deja present")

# 2) facture simple : calcul de la vignette apres la ligne numero
num_line='    numero = f"{prefix}-{now_str}-{tid:05d}"'
if num_line in api and "_pimg" not in api.split("def _build_facture_html")[1][:1200]:
    add=(num_line+eol
         +'    _pmap = _catalogue_photo_map()'+eol
         +'    _ph = _pmap.get(motif, "")'+eol
         +'    _pimg = f\'<img src="{_ph}" style="width:40px;height:40px;object-fit:cover;border-radius:4px;vertical-align:middle;margin-right:8px">\' if _ph else ""')
    api=api.replace(num_line,add,1)
    print("2) facture simple : vignette calculee")
elif "_pimg" in api.split("def _build_facture_html")[1][:1200]:
    print("2) deja present")
else:
    print("2) ATTENTION ligne numero (facture simple) non trouvee")

# 3) groupee : _pmap apres rows_html=""
rh='    rows_html = ""'
if rh in api and "_pmap = _catalogue_photo_map()" in api:
    # s'assurer qu'on ajoute le _pmap groupee une seule fois
    if api.count("_pmap = _catalogue_photo_map()")<2:
        api=api.replace(rh, rh+eol+'    _pmap = _catalogue_photo_map()', 1)
        print("3) groupee : _pmap ajoute")
    else:
        print("3) groupee : _pmap deja present")
else:
    print("3) ATTENTION rows_html='' non trouve ou helper manquant")

# 4) groupee : _pimg dans la boucle (apres 'total += mb')
tm='        total += mb'
if tm in api and "_ph = _pmap.get(motif" not in api.split("def _build_facture_groupee_html")[1][:1500] if "def _build_facture_groupee_html" in api else False:
    add4=(tm+eol
          +'        _ph = _pmap.get(motif, "")'+eol
          +'        _pimg = f\'<img src="{_ph}" style="width:34px;height:34px;object-fit:cover;border-radius:4px;vertical-align:middle;margin-right:6px">\' if _ph else ""')
    api=api.replace(tm,add4,1)
    print("4) groupee : vignette calculee dans la boucle")
elif "def _build_facture_groupee_html" in api and "_ph = _pmap.get(motif" in api.split("def _build_facture_groupee_html")[1][:1500]:
    print("4) deja present")
else:
    print("4) ATTENTION 'total += mb' non trouve")

# 5) groupee : inserer la vignette dans la cellule article (avant la cellule simple)
g_old='<tr><td><strong>{motif}</strong></td>'
g_new='<tr><td>{_pimg}<strong>{motif}</strong></td>'
if g_old in api:
    api=api.replace(g_old,g_new,1)
    print("5) groupee : vignette dans la cellule article")
elif '<tr><td>{_pimg}<strong>{motif}</strong></td>' in api:
    print("5) deja present")
else:
    print("5) ATTENTION cellule groupee non trouvee")

# 6) facture simple : inserer la vignette dans la cellule article
s_old='<td><strong>{motif}</strong></td>'
s_new='<td>{_pimg}<strong>{motif}</strong></td>'
if s_old in api:
    api=api.replace(s_old,s_new,1)
    print("6) facture simple : vignette dans la cellule article")
elif '<td>{_pimg}<strong>{motif}</strong></td>' in api:
    print("6) deja present")
else:
    print("6) ATTENTION cellule facture simple non trouvee")

io.open(ap,"w",encoding="utf-8",newline="").write(api)
print("=== TERMINE ===")
