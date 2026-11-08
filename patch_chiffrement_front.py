#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_chiffrement_front.py
Carte "Chiffrement de la base" dans Parametres : statut + activation par mot de passe.
Sans node. Idempotent, CRLF/LF preserves. A lancer dans le dossier projet.
"""
import os, sys

F = "web/index.html"
MARK = "activerChiffrement"
GRID_OLD = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:900px">'

CARD = ('<div class="card" style="grid-column:1/-1;border:1px solid var(--red)">'
        '<div class="card-title">\U0001F512 Chiffrement de la base</div>'
        '<p style="font-size:13px;color:var(--text3)">Protege ta base <b>et les photos</b> (elles sont dedans) par un mot de passe. Une fois active, le mot de passe sera demande au demarrage de l\'appli.</p>'
        '<div id="encStatut" style="font-size:14px;font-weight:600;margin:8px 0">—</div>'
        '<div id="encForm" style="display:none;gap:8px;align-items:center;flex-wrap:wrap">'
        '<input type="password" id="encPwd1" placeholder="Nouveau mot de passe" style="padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px">'
        '<input type="password" id="encPwd2" placeholder="Confirmer" style="padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px">'
        '<button class="btn primary" onclick="activerChiffrement()">Activer le chiffrement</button></div>'
        '<div style="font-size:12px;color:var(--text3);margin-top:8px">⚠ Note bien ton mot de passe : sans lui, la base est illisible.</div></div>')

JS = r"""
/* ===== CHIFFREMENT BASE ===== */
async function loadEncryptStatus(){
  try{
    var r=await api('/api/encrypt/status');
    var enc=!!(r&&r.ok&&r.data&&r.data.encrypted);
    var st=document.getElementById('encStatut'), fm=document.getElementById('encForm');
    if(st) st.innerHTML = enc
      ? '<span style="color:var(--green)">✓ Base chiffrée</span> <span style="color:var(--text3);font-weight:400">(mot de passe demandé au démarrage)</span>'
      : '<span style="color:var(--red)">⚠ Base NON chiffrée</span>';
    if(fm) fm.style.display = enc ? 'none' : 'flex';
  }catch(e){}
}
async function activerChiffrement(){
  var a=document.getElementById('encPwd1'), b=document.getElementById('encPwd2');
  var p=a?a.value:'', q=b?b.value:'';
  if(p.length<4){ if(typeof notify==='function')notify('Mot de passe trop court (4 min)','error'); return; }
  if(p!==q){ if(typeof notify==='function')notify('Les deux mots de passe ne correspondent pas','error'); return; }
  if(typeof notify==='function')notify('Chiffrement en cours…');
  try{
    var r=await api('/api/encrypt/setup',{method:'POST',body:{password:p}});
    if(r&&r.ok){ if(a)a.value=''; if(b)b.value=''; if(typeof notify==='function')notify('Base chiffrée ✓'); loadEncryptStatus(); }
    else{ if(typeof notify==='function')notify((r&&r.error)||'Échec','error'); }
  }catch(e){ if(typeof notify==='function')notify('Erreur','error'); }
}
"""

def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)

def main():
    if not os.path.exists(F):
        print("ERREUR : %s introuvable" % F); sys.exit(1)
    t=read(F); eol="\r\n" if "\r\n" in t else "\n"
    if MARK in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)
    if t.count(GRID_OLD)!=1: print("  [X] ancre grille settings %dx" % t.count(GRID_OLD)); sys.exit(1)
    if t.rfind("</body>")<0: print("  [X] </body> introuvable"); sys.exit(1)

    # carte
    t=t.replace(GRID_OLD, GRID_OLD+CARD, 1)

    # hook chargement (tolerant : avec ou sans la carte cloud)
    h_after = "loadVisionKey();loadCloudBackup();}"
    h_plain = "loadVisionKey();}"
    if h_after in t:
        t=t.replace(h_after, "loadVisionKey();loadCloudBackup();loadEncryptStatus();}", 1)
        print("  [+] hook settings (apres cloud) + carte")
    elif h_plain in t:
        t=t.replace(h_plain, "loadVisionKey();loadEncryptStatus();}", 1)
        print("  [+] hook settings + carte")
    else:
        print("  [!] hook settings non trouve -- la carte est posee, le statut se chargera a l'ouverture suivante")

    # module
    pos=t.rfind("</body>")
    block="<script>"+eol+eol.join(JS.split("\n"))+eol+"</script>"+eol
    t=t[:pos]+block+t[pos:]
    write(F,t)
    print("  [+] module chiffrement injecte")

    if read(F).count(MARK)<1:
        print("  [!] verification inattendue"); sys.exit(1)
    print("\nTermine (interface chiffrement).")

if __name__ == "__main__":
    main()
