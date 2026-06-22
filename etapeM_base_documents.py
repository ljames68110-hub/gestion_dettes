#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeM_base_documents.py  (CRLF-safe, main.py)
L'exe range la base dans Documents\\GestionPerso (au lieu d'AppData),
avec migration automatique des donnees existantes depuis AppData au 1er lancement.
A lancer dans le dossier projet : python etapeM_base_documents.py
"""
import io
mp="main.py"
m=io.open(mp,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in m else "\n"

old_lines=[
'        # Toujours stocker les donnees dans AppData/Roaming/GestionPerso',
'        # Peu importe ou est installe l exe',
'        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))',
'        d = os.path.join(appdata, "GestionPerso")',
'        os.makedirs(d, exist_ok=True)',
'        return d',
]
old_block=eol.join(old_lines)

new_lines=[
'        # Stockage dans Documents\\GestionPerso (toutes versions de l exe)',
'        home = os.path.expanduser("~")',
'        docs = os.path.join(home, "Documents")',
'        if not os.path.isdir(docs):',
'            docs = home',
'        d = os.path.join(docs, "GestionPerso")',
'        os.makedirs(d, exist_ok=True)',
'        # Migration unique depuis l ancien emplacement AppData',
'        try:',
'            new_db = os.path.join(d, "dettes.db")',
'            if not os.path.exists(new_db):',
'                appdata = os.environ.get("APPDATA", "")',
'                if appdata:',
'                    old_dir = os.path.join(appdata, "GestionPerso")',
'                    old_db = os.path.join(old_dir, "dettes.db")',
'                    if os.path.exists(old_db):',
'                        import shutil',
'                        shutil.copy2(old_db, new_db)',
'                        old_bak = os.path.join(old_dir, "dettes_backup.db")',
'                        if os.path.exists(old_bak):',
'                            shutil.copy2(old_bak, os.path.join(d, "dettes_backup.db"))',
'        except Exception:',
'            pass',
'        return d',
]
new_block=eol.join(new_lines)

if "Documents" in m and 'os.path.join(docs, "GestionPerso")' in m:
    print("deja present")
elif old_block in m:
    m=m.replace(old_block,new_block,1)
    io.open(mp,"w",encoding="utf-8",newline="").write(m)
    print("OK : la base sera dans Documents\\GestionPerso (migration auto depuis AppData)")
else:
    print("ATTENTION : bloc data_dir d'origine non trouve a l'identique")
    print("--- Je m'attendais a ce bloc (8 espaces d'indentation) :")
    for l in old_lines: print(l)
