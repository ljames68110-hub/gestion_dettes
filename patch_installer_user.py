#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_installer_user.py
Installe l'appli dans un dossier utilisateur (writable) pour que la mise a jour
automatique puisse remplacer l'exe sans droits admin.
 - DefaultDirName : {autopf}\\Gestion Perso -> {localappdata}\\Gestion Perso
 - PrivilegesRequired : admin -> lowest
 - UsePreviousAppDir : yes -> no  (ne pas reutiliser l'ancien dossier Program Files)
A lancer dans le dossier projet : python patch_installer_user.py
"""
import os
def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)

def main(path="installer.iss"):
    if not os.path.exists(path):
        print("ATTENTION : installer.iss introuvable"); return
    t = read(path); orig = t
    repls = [
        ("DefaultDirName={autopf}\\Gestion Perso", "DefaultDirName={localappdata}\\Gestion Perso"),
        ("PrivilegesRequired=admin", "PrivilegesRequired=lowest"),
        ("UsePreviousAppDir=yes", "UsePreviousAppDir=no"),
    ]
    for old, new in repls:
        if new in t:
            print("deja fait :", new)
        elif old in t:
            t = t.replace(old, new, 1)
            print("OK :", old, "->", new)
        else:
            print("ATTENTION introuvable :", old)
    if t != orig:
        write(path, t); print("installer.iss mis a jour")
    else:
        print("aucune modification")
    print("=== TERMINE ===")

if __name__ == "__main__":
    main()
