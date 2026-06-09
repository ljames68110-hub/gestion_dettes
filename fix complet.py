#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_complet.py - Corrige les frais ET ajoute le choix de date a la creation.

FRAIS:
  - VENTE (debit)         : jamais de frais (net = brut)
  - REMBOURSEMENT (credit): frais selon mode SI case "absorber les frais" cochee
  - Respecte le choix a la CREATION et a la MODIFICATION

DATE:
  - Champ date dans le modal de creation (defaut = aujourd'hui)
  - Envoyee au backend, qui la respecte (sinon date du jour)

Usage (dans le dossier du projet): python fix_complet.py
"""
import io, re

def read(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read()
def write(p, c):
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(c)

# ══════════════════════════════════════════════════════════════════
# DB.PY
# ══════════════════════════════════════════════════════════════════
db = read("db.py")

# --- A) add_transaction accepte un parametre date ---
old_sig = '''def add_transaction(client_id, type_, motif, quantite, prix_unitaire,
                    mode_paiement, frais, montant_brut, montant_net,
                    reference=None, notes=None):
    date = datetime.utcnow().isoformat(sep=' ', timespec='seconds')'''
new_sig = '''def add_transaction(client_id, type_, motif, quantite, prix_unitaire,
                    mode_paiement, frais, montant_brut, montant_net,
                    reference=None, notes=None, date=None):
    if not date:
        date = datetime.utcnow().isoformat(sep=' ', timespec='seconds')'''
if old_sig in db:
    db = db.replace(old_sig, new_sig)
    print("DB-A) add_transaction accepte une date personnalisee")
elif "date=None):" in db:
    print("DB-A) add_transaction deja modifiee")
else:
    print("DB-A) ATTENTION signature add_transaction non trouvee")

# --- B) update_transaction respecte frais_deduits ---
old_calc = 'frais      = round(brut * FEES.get(mode, 0), 2) if type_ == "credit" else 0.0\n        net        = round(brut - frais, 2)'
new_calc = '''frais_deduits = int(data.get("frais_deduits", row["frais_deduits"] if "frais_deduits" in row.keys() else 1))
        if type_ == "credit" and frais_deduits:
            frais = round(brut * FEES.get(mode, 0), 2)
        else:
            frais = 0.0
        net        = round(brut - frais, 2)'''
if old_calc in db:
    db = db.replace(old_calc, new_calc)
    print("DB-B) update_transaction respecte frais_deduits (vente=0, remb selon choix)")
elif 'frais_deduits = int(data.get("frais_deduits"' in db:
    print("DB-B) update_transaction deja corrigee")
else:
    print("DB-B) ATTENTION calcul frais update non trouve")

# --- C) update_transaction sauvegarde frais_deduits ---
old_usql = '''montant_brut=?, mode_paiement=?, frais=?, montant_net=?, notes=?, date=?
            WHERE id=?""",
            (type_, motif, quantite, prix_u, brut, mode, frais, net, notes, date, trans_id)'''
new_usql = '''montant_brut=?, mode_paiement=?, frais=?, montant_net=?, notes=?, date=?, frais_deduits=?
            WHERE id=?""",
            (type_, motif, quantite, prix_u, brut, mode, frais, net, notes, date, frais_deduits, trans_id)'''
if old_usql in db:
    db = db.replace(old_usql, new_usql)
    print("DB-C) update_transaction sauvegarde frais_deduits")
elif "frais=?, montant_net=?, notes=?, date=?, frais_deduits=?" in db:
    print("DB-C) deja ok")
else:
    print("DB-C) ATTENTION UPDATE SQL non trouve")

write("db.py", db)

# ══════════════════════════════════════════════════════════════════
# API.PY  -- passer la date a add_transaction
# ══════════════════════════════════════════════════════════════════
api = read("api.py")

old_add = '''        reference     = data.get("reference", ""),
        notes         = data.get("notes", ""),
    )'''
new_add = '''        reference     = data.get("reference", ""),
        notes         = data.get("notes", ""),
        date          = data.get("date") or None,
    )'''
if old_add in api:
    api = api.replace(old_add, new_add)
    print("API) creation transaction transmet la date choisie")
elif 'date          = data.get("date") or None,' in api:
    print("API) deja ok")
else:
    print("API) ATTENTION appel add_transaction non trouve")

write("api.py", api)

# ══════════════════════════════════════════════════════════════════
# WEB/INDEX.HTML
# ══════════════════════════════════════════════════════════════════
html = read("web/index.html")

# --- 1) Champ DATE dans le modal de creation (avant Notes) ---
if 'id="mDate"' not in html:
    notes_field = '<div class="form-group full"><label>Notes</label><input type="text" id="mNotes" placeholder="Facultatif..."></div>'
    date_field = '<div class="form-group full"><label>Date</label><input type="date" id="mDate" style="padding:10px 12px;border-radius:var(--radius2);border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px;font-family:Outfit,sans-serif"></div>\n      ' + notes_field
    if notes_field in html:
        html = html.replace(notes_field, date_field, 1)
        print("WEB-1) Champ date ajoute au modal de creation")
    else:
        print("WEB-1) ATTENTION champ Notes creation non trouve")
else:
    print("WEB-1) Champ date creation deja present")

# --- 2) saveTrans envoie la date ---
old_body = "frais_deduits:_fraisDeduits?1:0,compte:compte_val};"
new_body = "frais_deduits:_fraisDeduits?1:0,compte:compte_val,date:(document.getElementById('mDate')&&document.getElementById('mDate').value?document.getElementById('mDate').value:undefined)};"
if old_body in html:
    html = html.replace(old_body, new_body)
    print("WEB-2) saveTrans envoie la date choisie")
elif "date:(document.getElementById('mDate')" in html:
    print("WEB-2) deja ok")
else:
    print("WEB-2) ATTENTION body saveTrans non trouve")

# --- 3) Pre-remplir la date du jour quand on ouvre le modal creation ---
# On accroche a openModal('transaction') ou la fonction d'ouverture. Strategie simple :
# ajouter une init dans la fonction qui ouvre le modal transaction si reperable.
if "if(document.getElementById('mDate')&&!document.getElementById('mDate').value)" not in html:
    # On cible la fin de calcModal pour garantir un defaut, sinon defaut au focus
    # Plus robuste : initialiser au moment ou on clique "Nouvelle transaction".
    # On cherche openModal definition
    m = re.search(r"function openModal\(([^)]*)\)\s*\{", html)
    if m:
        inject = m.group(0) + "\n  try{var _md=document.getElementById('mDate');if(_md&&!_md.value){_md.value=new Date().toISOString().slice(0,10);}}catch(e){}"
        html = html.replace(m.group(0), inject, 1)
        print("WEB-3) date du jour pre-remplie a l'ouverture du modal")
    else:
        print("WEB-3) openModal non trouve - date par defaut non auto (non bloquant)")
else:
    print("WEB-3) deja ok")

# --- 4) calcEditModal respecte la case frais ---
old_edit_calc = "const brut=qty*prix;const frais=type==='credit'?brut*(FEES[mode]||0):0;const net=brut-frais;"
new_edit_calc = "var etFd=document.getElementById('etFraisDeduits');var fdChecked=etFd?etFd.checked:true;const brut=qty*prix;const frais=(type==='credit'&&fdChecked)?brut*(FEES[mode]||0):0;const net=brut-frais;"
if old_edit_calc in html:
    html = html.replace(old_edit_calc, new_edit_calc)
    print("WEB-4) calcEditModal respecte la case frais")
elif "fdChecked" in html:
    print("WEB-4) deja ok")
else:
    print("WEB-4) ATTENTION calcEditModal non trouve")

# --- 5) saveEditTrans envoie frais_deduits ---
old_ebody = "mode_paiement:document.getElementById('etMode').value,notes:document.getElementById('etNotes').value,date:document.getElementById('etDate').value};"
new_ebody = "mode_paiement:document.getElementById('etMode').value,notes:document.getElementById('etNotes').value,date:document.getElementById('etDate').value,frais_deduits:(document.getElementById('etFraisDeduits')?(document.getElementById('etFraisDeduits').checked?1:0):1)};"
if old_ebody in html:
    html = html.replace(old_ebody, new_ebody)
    print("WEB-5) saveEditTrans envoie frais_deduits")
elif "frais_deduits:(document.getElementById('etFraisDeduits')" in html:
    print("WEB-5) deja ok")
else:
    print("WEB-5) ATTENTION body saveEditTrans non trouve")

# --- 6) Case "absorber les frais" dans le modal edition ---
if 'id="etFraisDeduits"' not in html:
    anchor = '<div class="calc-item" id="etFraisRow">'
    if anchor in html:
        checkbox = '''<div class="form-group full" id="etFraisDeduitsWrap" style="margin-bottom:8px"><label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text2);cursor:pointer"><input type="checkbox" id="etFraisDeduits" checked onchange="calcEditModal()" style="width:auto;margin:0"> J'absorbe les frais</label></div>\n      ''' + anchor
        html = html.replace(anchor, checkbox, 1)
        print("WEB-6) case 'absorber les frais' ajoutee (modal edition)")
    else:
        print("WEB-6) ATTENTION etFraisRow non trouve")
else:
    print("WEB-6) case frais edition deja presente")

# --- 7) openEditTrans coche la case selon la transaction + cache si vente ---
old_open = "toggleEditTypeFields();document.getElementById('modalEditTrans').classList.add('open');"
new_open = "if(document.getElementById('etFraisDeduits'))document.getElementById('etFraisDeduits').checked=(t.frais_deduits!==0);if(document.getElementById('etFraisDeduitsWrap'))document.getElementById('etFraisDeduitsWrap').style.display=(t.type==='credit'?'block':'none');toggleEditTypeFields();document.getElementById('modalEditTrans').classList.add('open');"
if old_open in html and "etFraisDeduits').checked=(t.frais_deduits" not in html:
    html = html.replace(old_open, new_open)
    print("WEB-7) openEditTrans initialise la case selon la transaction")
else:
    print("WEB-7) deja ok ou ancre absente")

# --- 8) toggleEditTypeFields cache la case si vente ---
old_toggle = "document.getElementById('etFraisRow').style.display=isDebit?'none':'flex';"
new_toggle = "document.getElementById('etFraisRow').style.display=isDebit?'none':'flex';var _efw=document.getElementById('etFraisDeduitsWrap');if(_efw)_efw.style.display=isDebit?'none':'block';"
if old_toggle in html and "_efw" not in html:
    html = html.replace(old_toggle, new_toggle)
    print("WEB-8) toggleEditTypeFields cache la case frais sur une vente")
else:
    print("WEB-8) deja ok")

write("web/index.html", html)

print("")
print("=== TERMINE ===")
print("FRAIS : vente=0 | remboursement selon case | respecte a la creation ET modif")
print("DATE  : choisissable a la creation (defaut aujourd'hui) et a la modification")
