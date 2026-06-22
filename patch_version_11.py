#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_version_11.py
 - updater.py  : ajoute APP_VERSION = "1.1" et fait lire la version courante
                 depuis le code en mode compile (elle voyage avec l'exe).
 - installer.iss : #define AppVersion "1.0" -> "1.1"
A lancer dans le dossier projet : python patch_version_11.py
"""
import os
NEW_VERSION = "1.1"

def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def to_eol(b,eol): return eol.join(b.split("\n"))

NEW_GETVER = '''def get_current_version():
    """Version courante de l'app. En mode compile, lue depuis APP_VERSION (elle
    voyage donc avec l'exe). En dev, depuis latest.json local s'il existe."""
    if getattr(sys, "frozen", False):
        return {"version": APP_VERSION}
    local = Path(__file__).parent / "latest.json"
    if local.exists():
        try:
            return json.loads(local.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": APP_VERSION}'''

def patch_updater(path="updater.py"):
    t=read(path); eol=eol_of(t)
    changed=False
    # 1) constante APP_VERSION avant get_current_exe
    if "APP_VERSION" not in t:
        anchor="def get_current_exe():"
        i=t.find(anchor)
        if i==-1:
            print("ATTENTION updater.py : get_current_exe introuvable")
        else:
            const='APP_VERSION = "'+NEW_VERSION+'"  # version courante - incremente a chaque MAJ'
            t=t[:i]+to_eol(const,eol)+eol+eol+t[i:]
            changed=True; print("updater.py : APP_VERSION ajoutee OK")
    else:
        # deja present : on met juste a jour le numero
        import re
        t2=re.sub(r'APP_VERSION\s*=\s*"[^"]*"', 'APP_VERSION = "'+NEW_VERSION+'"', t, count=1)
        if t2!=t:
            t=t2; changed=True; print("updater.py : APP_VERSION mise a jour ->", NEW_VERSION)
        else:
            print("updater.py : APP_VERSION deja a", NEW_VERSION)
    # 2) remplacer get_current_version
    s=t.find("def get_current_version():")
    if s==-1:
        print("ATTENTION updater.py : get_current_version introuvable")
    elif "return {\"version\": APP_VERSION}" in t and "frozen" in t[s:s+400]:
        print("updater.py : get_current_version deja patchee, saute")
    else:
        marker='return {"version": "0.0.0"}'
        e=t.find(marker, s)
        if e==-1:
            print("ATTENTION updater.py : fin de get_current_version introuvable")
        else:
            e=e+len(marker)
            t=t[:s]+to_eol(NEW_GETVER,eol)+t[e:]
            changed=True; print("updater.py : get_current_version reecrite OK")
    if changed: write(path,t)

def patch_iss(path="installer.iss"):
    t=read(path)
    old='#define AppVersion "1.0"'
    new='#define AppVersion "'+NEW_VERSION+'"'
    if new in t:
        print("installer.iss : deja en", NEW_VERSION); return
    if old not in t:
        print("ATTENTION installer.iss : ligne AppVersion 1.0 introuvable (verifie manuellement)"); return
    t=t.replace(old,new,1); write(path,t)
    print("installer.iss : AppVersion 1.0 ->", NEW_VERSION, "OK")

if __name__=="__main__":
    if os.path.exists("updater.py"): patch_updater()
    else: print("ATTENTION updater.py introuvable")
    if os.path.exists("installer.iss"): patch_iss()
    else: print("ATTENTION installer.iss introuvable")
    print("=== TERMINE ===")
