# -*- coding: utf-8 -*-
"""
patch_tabac_stock.py
Quand on encaisse un RENDU de tabac depuis la caisse (bloc Comptes cantine & tabac),
les paquets rendus sont RAJOUTES au stock du catalogue ; quand on ajoute une DETTE
tabac, ils sont RETIRES du stock (sinon le stock gonflerait a chaque aller-retour).
Le type de tabac est associe a l'article du catalogue portant le meme nom.
Sans node. Idempotent, CRLF/LF preserves. A lancer dans le dossier du projet.
"""
import os, sys

F = "web/index.html"
MARK = "_ctTabacStock"

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def J(lines, eol): return eol.join(lines)

HELPER = [
"async function _ctTabacStock(nom, delta){",
"  try{",
"    var _rc=await api('/api/catalogue');",
"    if(_rc&&_rc.ok&&_rc.data){",
"      var _n=(nom||'').trim().toLowerCase();",
"      var _c=_rc.data.find(function(a){return (a.nom||'').trim().toLowerCase()===_n;});",
"      if(_c){",
"        await api('/api/catalogue/'+_c.id+'/adjust-stock',{method:'POST',body:{delta:delta}});",
"        if(typeof loadCatalogue==='function'){ try{ await loadCatalogue(); if(typeof renderPosGrid==='function')renderPosGrid(''); }catch(e){} }",
"      }",
"    }",
"  }catch(e){}",
"}",
"",
]

ENC_OLD = [
"async function ctEncaisserTabacDette(){",
"  var q=parseFloat(((document.getElementById('ctTabacQ')||{}).value||'0').replace(',','.'))||0;",
"  if(q<=0){ if(typeof notify==='function')notify('Nombre de paquets invalide','error'); return; }",
"  var ty=_ctTabacSel();",
"  await _ctPost({type:'credit',motif:'Rendu tabac',quantite:q,unite:'paquet',prix_unitaire:ty.prix,",
"    mode_paiement:ty.nom,notes:'[CAISSE] Rendu '+q+' x '+ty.nom,frais_deduits:0,compte:'tabac'},",
"    _fmtQte(q)+' paquet(s) rendu(s)');",
"}",
]
ENC_NEW = [
"async function ctEncaisserTabacDette(){",
"  var q=parseFloat(((document.getElementById('ctTabacQ')||{}).value||'0').replace(',','.'))||0;",
"  if(q<=0){ if(typeof notify==='function')notify('Nombre de paquets invalide','error'); return; }",
"  var ty=_ctTabacSel();",
"  var _okp=await _ctPost({type:'credit',motif:'Rendu tabac',quantite:q,unite:'paquet',prix_unitaire:ty.prix,",
"    mode_paiement:ty.nom,notes:'[CAISSE] Rendu '+q+' x '+ty.nom,frais_deduits:0,compte:'tabac'},",
"    _fmtQte(q)+' paquet(s) rendu(s)');",
"  if(_okp) await _ctTabacStock(ty.nom, q);",
"}",
]

DET_OLD = [
"async function ctDetteTabac(){",
"  var q=parseFloat(((document.getElementById('ctTabacQ')||{}).value||'0').replace(',','.'))||0;",
"  if(q<=0){ if(typeof notify==='function')notify('Nombre de paquets invalide','error'); return; }",
"  var ty=_ctTabacSel();",
"  await _ctPost({type:'debit',motif:'Tabac',quantite:q,unite:'paquet',prix_unitaire:ty.prix,",
"    mode_paiement:ty.nom,notes:'[CAISSE] Dette '+q+' x '+ty.nom,frais_deduits:0,compte:'tabac'},",
"    'Dette tabac ajoutée : '+_fmtQte(q)+' x '+ty.nom);",
"}",
]
DET_NEW = [
"async function ctDetteTabac(){",
"  var q=parseFloat(((document.getElementById('ctTabacQ')||{}).value||'0').replace(',','.'))||0;",
"  if(q<=0){ if(typeof notify==='function')notify('Nombre de paquets invalide','error'); return; }",
"  var ty=_ctTabacSel();",
"  var _okp=await _ctPost({type:'debit',motif:'Tabac',quantite:q,unite:'paquet',prix_unitaire:ty.prix,",
"    mode_paiement:ty.nom,notes:'[CAISSE] Dette '+q+' x '+ty.nom,frais_deduits:0,compte:'tabac'},",
"    'Dette tabac ajoutée : '+_fmtQte(q)+' x '+ty.nom);",
"  if(_okp) await _ctTabacStock(ty.nom, -q);",
"}",
]

def repl(t, eol, old_lines, new_lines, label):
    old = J(old_lines, eol); new = J(new_lines, eol)
    n = t.count(old)
    if n != 1:
        print("  [X] %s : ancre trouvee %dx (attendu 1)" % (label, n)); sys.exit(1)
    return t.replace(old, new, 1)

def main():
    if not os.path.exists(F):
        print("ERREUR : %s introuvable" % F); sys.exit(1)
    t = read(F); eol = "\r\n" if "\r\n" in t else "\n"
    if MARK in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)
    if "ctEncaisserTabacDette" not in t:
        print("  [X] fonctions tabac introuvables -- applique d'abord la 4.27"); sys.exit(1)

    # 1) rendu : +stock (et insere le helper juste avant)
    t = repl(t, eol, ENC_OLD, HELPER + ENC_NEW, "rendu tabac (+stock)")
    print("  [+] rendu tabac -> +stock")
    # 2) dette : -stock
    t = repl(t, eol, DET_OLD, DET_NEW, "dette tabac (-stock)")
    print("  [+] dette tabac -> -stock")

    write(F, t)
    if read(F).count(MARK) < 1:
        print("  [!] verification inattendue"); sys.exit(1)
    print("\nTermine (stock tabac au rendu/dette).")

if __name__ == "__main__":
    main()
