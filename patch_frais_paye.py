#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_frais_paye.py
Ajoute un bouton "Paye" dans le panneau "Frais dus".
 - db.py   : fonction payer_frais_dus(frais_ids) -> remet frais=0 / net=brut sur
             la transaction liee, note [FRAIS PAYE], passe frais_dus en 'paye'.
 - api.py  : route POST /api/frais-dus/paye
 - web/index.html : bouton "Paye" + fonction JS payerFraisDus(cid)
A lancer dans le dossier projet : python patch_frais_paye.py
"""
import os

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)
def eol_of(t):
    return "\r\n" if "\r\n" in t else "\n"
def to_eol(block_lf, eol):
    return eol.join(block_lf.split("\n"))

DB_FUNC = r'''def payer_frais_dus(frais_ids):
    """Marque des frais comme payes : remet frais=0 et net=brut sur la
    transaction liee (le solde se corrige), garde la trace [FRAIS PAYE],
    et passe la ligne frais_dus en statut paye. Renvoie le total regle."""
    _ensure_frais_dus_table()
    total = 0.0
    with get_conn() as conn:
        for fid in frais_ids:
            row = conn.execute("SELECT transaction_id, montant FROM frais_dus WHERE id=?", (int(fid),)).fetchone()
            if not row:
                continue
            tid = row["transaction_id"]
            montant = row["montant"] or 0
            if tid:
                t = conn.execute("SELECT montant_brut, COALESCE(notes,'') AS notes FROM transactions WHERE id=?", (tid,)).fetchone()
                if t:
                    brut = t["montant_brut"]
                    notes = t["notes"] or ""
                    if "[FRAIS PAYE]" not in notes:
                        notes = (notes + " [FRAIS PAYE]").strip()
                    conn.execute("UPDATE transactions SET frais=0, montant_net=?, notes=? WHERE id=?", (brut, notes, tid))
                    total += montant
            conn.execute("UPDATE frais_dus SET statut='paye' WHERE id=?", (int(fid),))
        conn.commit()
    return round(total, 2)
'''

API_ROUTE = r'''@app.route("/api/frais-dus/paye", methods=["POST"])
@require_auth
def frais_dus_paye():
    data = request.json or {}
    ids = data.get("ids", [])
    if not ids:
        return err("Selection vide")
    total = db.payer_frais_dus(ids)
    return ok({"total": total})
'''

JS_FUNC = r'''async function payerFraisDus(cid){
  var ids=getFraisDusChecked().map(function(c){return parseInt(c.value);});
  if(!ids.length){notify('Coche au moins un frais','error');return;}
  var total=getFraisDusChecked().reduce(function(s,c){return s+(parseFloat(c.dataset.montant)||0);},0);
  if(!confirm('Marquer '+ids.length+' frais comme paye(s) ('+total.toFixed(2)+' EUR) ? Ils seront retires du solde, la transaction reste visible.'))return;
  var res=await api('/api/frais-dus/paye',{method:'POST',body:{ids:ids}});
  if(res&&res.ok){
    notify('Frais paye(s) : '+res.data.total.toFixed(2)+' EUR retires du solde');
    loadSolde();
    if(typeof loadDashboard==='function')loadDashboard();
  }else notify(res&&res.error?res.error:'Erreur','error');
}
'''

def patch_db(path="db.py"):
    t = read(path); eol = eol_of(t)
    if "def payer_frais_dus" in t:
        print("db.py : payer_frais_dus deja present, saute"); return
    anchor = "# -- TYPES DE TABAC"
    i = t.find(anchor)
    if i == -1:
        print("ATTENTION db.py : ancre 'TYPES DE TABAC' introuvable"); return
    block = to_eol(DB_FUNC, eol)            # finit par eol (ligne vide finale du raw string)
    t = t[:i] + block + eol + t[i:]         # une ligne vide avant l'ancre
    write(path, t)
    print("db.py : fonction payer_frais_dus ajoutee OK")

def patch_api(path="api.py"):
    t = read(path); eol = eol_of(t)
    if "/api/frais-dus/paye" in t:
        print("api.py : route /api/frais-dus/paye deja presente, saute"); return
    anchor = '@app.route("/api/frais-dus/oublier"'
    i = t.find(anchor)
    if i == -1:
        print("ATTENTION api.py : ancre route 'oublier' introuvable"); return
    block = to_eol(API_ROUTE, eol)
    t = t[:i] + block + eol + t[i:]
    write(path, t)
    print("api.py : route /api/frais-dus/paye ajoutee OK")

def patch_web(path="web/index.html"):
    t = read(path); eol = eol_of(t)
    changed = False
    # 1) bouton "Paye" apres le bouton "Oublier la selection"
    if "payerFraisDus(" not in t.split("</script>")[0] and "onclick=\"payerFraisDus(" not in t:
        parts = t.split(eol)
        marker = "onclick=\"oublierFraisDus('+cid+')\">Oublier la selection</button>'"
        done = False
        for idx, line in enumerate(parts):
            if marker in line and "btn" in line:
                indent = line[:len(line) - len(line.lstrip())]
                newline = indent + "+'<button class=\"btn\" style=\"font-size:12px;background:#2e7d32;color:#fff\" onclick=\"payerFraisDus('+cid+')\">&#10003; Paye</button>'"
                parts.insert(idx + 1, newline)
                done = True
                break
        if done:
            t = eol.join(parts); changed = True; print("web : bouton 'Paye' insere OK")
        else:
            print("ATTENTION web : ligne bouton 'Oublier la selection' introuvable")
    else:
        print("web : bouton 'Paye' deja present, saute")
    # 2) fonction JS payerFraisDus avant oublierFraisDus
    if "function payerFraisDus" not in t:
        anchor = "async function oublierFraisDus(cid){"
        i = t.find(anchor)
        if i == -1:
            print("ATTENTION web : fonction oublierFraisDus introuvable")
        else:
            block = to_eol(JS_FUNC, eol)
            t = t[:i] + block + eol + t[i:]
            changed = True; print("web : fonction payerFraisDus inseree OK")
    else:
        print("web : fonction payerFraisDus deja presente, saute")
    if changed:
        write(path, t)

if __name__ == "__main__":
    if os.path.exists("db.py"): patch_db()
    else: print("ATTENTION : db.py introuvable ici")
    if os.path.exists("api.py"): patch_api()
    else: print("ATTENTION : api.py introuvable ici")
    if os.path.exists("web/index.html"): patch_web()
    else: print("ATTENTION : web/index.html introuvable ici")
    print("=== TERMINE ===")
