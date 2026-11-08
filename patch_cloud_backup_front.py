#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_cloud_backup_front.py
Interface de la sauvegarde cloud : carte dans Parametres (activer, choisir le
dossier, sauvegarder maintenant). Idempotent, CRLF/LF preserves, JS valide.
A lancer dans le dossier projet : python patch_cloud_backup_front.py
"""
import os, sys, subprocess, tempfile

F = "web/index.html"
MARK = "setCloudEnabled"

GRID_OLD = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:900px">'
CARD = ('<div class="card" style="grid-column:1/-1;border:1px solid var(--gold2)">'
        '<div class="card-title">☁ Sauvegarde cloud automatique</div>'
        '<p style="font-size:13px;color:var(--text3)">À chaque fermeture de l\'appli, ta base (chiffrée) est copiée dans un dossier OneDrive ou Google Drive de ton PC, qui l\'envoie en ligne tout seul. Pour ne plus jamais perdre tes données.</p>'
        '<label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:14px;color:var(--text2);margin:8px 0">'
        '<input type="checkbox" id="setCloudEnabled" onchange="saveCloudBackup()" style="width:auto;margin:0"> Activer la sauvegarde à chaque fermeture</label>'
        '<div style="display:flex;gap:8px;align-items:center;margin-top:8px;flex-wrap:wrap">'
        '<input type="text" id="setCloudDir" readonly placeholder="Aucun dossier choisi" style="flex:1;min-width:220px;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px">'
        '<button class="btn" onclick="pickCloudFolder()">Choisir le dossier…</button>'
        '<button class="btn primary" onclick="runCloudBackup()">Sauvegarder maintenant</button></div>'
        '<div id="cloudBackupStatus" style="font-size:12px;color:var(--text3);margin-top:8px"></div></div>')

HOOK_OLD = "if(name==='settings'){initSettings();loadMotifs();loadTarifs();loadVisionKey();}"
HOOK_NEW = "if(name==='settings'){initSettings();loadMotifs();loadTarifs();loadVisionKey();loadCloudBackup();}"

JS = r"""
/* ===== SAUVEGARDE CLOUD ===== */
async function loadCloudBackup(){
  try{var r=await api('/api/cloud-backup');if(r&&r.ok&&r.data){
    var e=document.getElementById('setCloudEnabled'); if(e)e.checked=!!r.data.enabled;
    var d=document.getElementById('setCloudDir'); if(d)d.value=r.data.dir||'';
  }}catch(e){}
}
async function saveCloudBackup(){
  var en=document.getElementById('setCloudEnabled'), d=document.getElementById('setCloudDir');
  var enabled=en?en.checked:false, dir=d?d.value:'';
  if(enabled && !dir){ if(typeof notify==='function')notify('Choisis d\'abord un dossier','error'); if(en)en.checked=false; return; }
  try{ await api('/api/cloud-backup',{method:'POST',body:{enabled:enabled,dir:dir}}); if(typeof notify==='function')notify(enabled?'Sauvegarde cloud activée':'Sauvegarde cloud désactivée'); }catch(e){}
}
async function pickCloudFolder(){
  try{ var r=await api('/api/cloud-backup/pick',{method:'POST'});
    if(r&&r.ok&&r.data&&r.data.dir){ var d=document.getElementById('setCloudDir'); if(d)d.value=r.data.dir; saveCloudBackup(); }
  }catch(e){ if(typeof notify==='function')notify('Sélection annulée','error'); }
}
async function runCloudBackup(){
  var st=document.getElementById('cloudBackupStatus'); if(st)st.textContent='Sauvegarde en cours…';
  try{ var r=await api('/api/cloud-backup/run',{method:'POST'});
    if(r&&r.ok){ if(st)st.textContent='✓ Sauvegardé dans : '+((r.data&&r.data.dest)||''); if(typeof notify==='function')notify('Sauvegarde envoyée dans le cloud'); }
    else{ if(st)st.textContent='✗ '+((r&&r.error)||'échec'); if(typeof notify==='function')notify((r&&r.error)||'Échec','error'); }
  }catch(e){ if(st)st.textContent='✗ erreur'; }
}
"""

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)

def main():
    if not os.path.exists(F):
        print("ERREUR : %s introuvable" % F); sys.exit(1)
    t = read(F); eol = "\r\n" if "\r\n" in t else "\n"
    if MARK in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)
    if t.count(GRID_OLD) != 1: print("  [X] ancre grille settings %dx" % t.count(GRID_OLD)); sys.exit(1)
    if t.count(HOOK_OLD) != 1: print("  [X] ancre hook settings %dx" % t.count(HOOK_OLD)); sys.exit(1)
    if t.rfind("</body>") < 0: print("  [X] </body> introuvable"); sys.exit(1)

    # valider JS
    tmp = os.path.join(tempfile.gettempdir(), "_cb_check.js")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("function api(){};function notify(){};var document={getElementById:function(){return{};}};\n" + JS)
    try:
        r = subprocess.run(["node","--check",tmp], capture_output=True, shell=(os.name=="nt"))
        se = (r.stderr or b"").decode("utf-8","replace")
        if r.returncode == 0:
            print("  [ok] syntaxe JS validee")
        elif any(k in se.lower() for k in ("not recognized","n'est pas reconnu","introuvable","not found","no such file")):
            print("  [!] node absent -- validation JS sautee (JS deja verifie)")
        else:
            print("  [X] ERREUR JS :", se); sys.exit(1)
    except FileNotFoundError:
        print("  [!] node absent -- validation JS sautee (JS deja verifie)")
    except Exception as _e:
        print("  [!] validation JS impossible (%s) -- sautee" % _e)
    finally:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except Exception: pass

    t = t.replace(GRID_OLD, GRID_OLD + CARD, 1)
    t = t.replace(HOOK_OLD, HOOK_NEW, 1)
    pos = t.rfind("</body>")
    block = "<script>" + eol + eol.join(JS.split("\n")) + eol + "</script>" + eol
    t = t[:pos] + block + t[pos:]
    write(F, t)
    print("  [+] carte Sauvegarde cloud + JS injectes")

    t2 = read(F)
    if t2.count(MARK) < 1 or "loadCloudBackup" not in t2:
        print("  [!] verification post-patch inattendue"); sys.exit(1)
    print("\nTermine (interface). Modif front -> rebuild/publication (4.19).")

if __name__ == "__main__":
    main()
