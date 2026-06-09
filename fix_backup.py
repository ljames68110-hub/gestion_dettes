#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_backup.py
  1) Neutralise autoBackup() (plus de sauvegarde a l'ouverture)
  2) Sauvegarde a la FERMETURE dans main.py : dettes.db -> dettes_backup.db
     (copie unique ecrasee a chaque fermeture)
  3) Remet debug=False (plus de DevTools au demarrage)
Idempotent. Usage (dossier projet): python fix_backup.py
"""
import io, re

# ════════════════════════════════════════════════════════════════
# WEB : neutraliser autoBackup
# ════════════════════════════════════════════════════════════════
p="web/index.html"
with io.open(p,"r",encoding="utf-8") as f:
    html=f.read()

old_fn = """async function autoBackup(){
  var lastBackup = store.get('lastBackup'); // FIX: utiliser store (avec fallback mémoire) au lieu de localStorage brut
  var today = new Date().toISOString().slice(0,10);
  if(lastBackup !== today){
    store.set('lastBackup', today);
    // Sauvegarde silencieuse vers Documents (sans boite de dialogue)
    api('/api/export/db/save', {method:'POST'}).catch(function(){});
  }
}"""
new_fn = """async function autoBackup(){
  // Desactive : la sauvegarde se fait automatiquement a la FERMETURE de l'app (cote main.py)
  return;
}"""
if old_fn in html:
    html=html.replace(old_fn,new_fn,1)
    print("WEB-1) autoBackup neutralise (plus de sauvegarde a l'ouverture)")
elif "// Desactive : la sauvegarde se fait automatiquement a la FERMETURE" in html:
    print("WEB-1) autoBackup deja neutralise")
else:
    print("WEB-1) ATTENTION autoBackup non trouve a l'identique")

with io.open(p,"w",encoding="utf-8") as f:
    f.write(html)

# ════════════════════════════════════════════════════════════════
# MAIN.PY : sauvegarde a la fermeture + debug False
# ════════════════════════════════════════════════════════════════
mp="main.py"
with io.open(mp,"r",encoding="utf-8") as f:
    main=f.read()

# a) debug=True -> False
if "debug=True" in main:
    main=main.replace("debug=True","debug=False")
    print("MAIN-a) debug remis a False (plus de DevTools)")
else:
    print("MAIN-a) debug deja False")

# b) Ajouter une fonction de sauvegarde + atexit, juste avant def main()
if "def _save_backup_on_exit" not in main:
    func = '''
def _save_backup_on_exit():
    """Copie de secours unique de la base, ecrasee a chaque fermeture."""
    try:
        import shutil
        if os.path.exists(DB_PATH):
            backup_path = os.path.join(DATA_DIR, "dettes_backup.db")
            shutil.copy2(DB_PATH, backup_path)
            print(f"[Gestion Perso] Sauvegarde de secours : {backup_path}")
    except Exception as e:
        print(f"[Gestion Perso] Echec sauvegarde fermeture : {e}")

'''
    # inserer avant 'def main():'
    idx = main.find("def main():")
    if idx != -1:
        main = main[:idx] + func + main[idx:]
        print("MAIN-b) fonction de sauvegarde ajoutee")
    else:
        print("MAIN-b) ATTENTION def main() introuvable")
else:
    print("MAIN-b) fonction sauvegarde deja presente")

# c) Enregistrer atexit dans main() (filet de securite quel que soit le mode de sortie)
if "atexit.register(_save_backup_on_exit)" not in main:
    # ajouter l'import atexit en haut si absent
    if "import atexit" not in main:
        main = main.replace("import threading", "import threading\nimport atexit", 1)
    # enregistrer juste apres l'entree dans main()
    m = re.search(r"(def main\(\):\s*\n)", main)
    if m:
        main = main.replace(m.group(1), m.group(1) + "    atexit.register(_save_backup_on_exit)\n", 1)
        print("MAIN-c) atexit enregistre dans main()")
    else:
        print("MAIN-c) ATTENTION impossible d'enregistrer atexit")
else:
    print("MAIN-c) atexit deja enregistre")

# d) Sauvegarde explicite aussi a la fermeture de la fenetre pywebview
#    (avant le bloc 'except ImportError' du webview)
if "_save_backup_on_exit()  # apres fermeture fenetre" not in main:
    anchor = "        webview.start(debug=False, icon=icon, gui=\"edgechromium\")"
    if anchor not in main:
        # essayer variantes
        m = re.search(r"(\s*webview\.start\([^\n]*\))", main)
        anchor = m.group(1) if m else None
    if anchor:
        replacement = anchor + "\n        _save_backup_on_exit()  # apres fermeture fenetre"
        main = main.replace(anchor, replacement, 1)
        print("MAIN-d) sauvegarde declenchee apres fermeture de la fenetre")
    else:
        print("MAIN-d) ATTENTION webview.start introuvable (atexit suffira)")
else:
    print("MAIN-d) deja: sauvegarde post-fenetre")

with io.open(mp,"w",encoding="utf-8") as f:
    f.write(main)

print("")
print("=== TERMINE ===")
print("Sauvegarde auto a la fermeture -> dettes_backup.db (ecrasee a chaque fois)")
print("Plus de sauvegarde a l'ouverture. DevTools desactive.")
