#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feature_frais_dus.py
Fonctionnalite complete "Frais dus" :
  - DB : table frais_dus (statut en_attente/facture/oublie) + migration des frais existants
  - API : lister / facturer / oublier
  - WEB : panneau sur la fiche client (cases a cocher + Facturer + Oublier)
A lancer dans le dossier projet : python feature_frais_dus.py
"""
import io, re

def read(p):
    with io.open(p,"r",encoding="utf-8") as f: return f.read()
def write(p,c):
    with io.open(p,"w",encoding="utf-8") as f: f.write(c)

# ════════════════════════════════════════════════════════════════
# DB.PY
# ════════════════════════════════════════════════════════════════
db = read("db.py")
if "_ensure_frais_dus_table" not in db:
    block = '''

# -- FRAIS DUS ----------------------------------------------------------------
def _ensure_frais_dus_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS frais_dus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            transaction_id INTEGER,
            montant REAL NOT NULL,
            date TEXT,
            statut TEXT DEFAULT 'en_attente',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        )""")
        conn.commit()

def migrate_frais_dus():
    """Cree une ligne frais_dus 'en_attente' pour chaque frais existant
    sur les remboursements (credits) qui n'a pas encore ete migre."""
    _ensure_frais_dus_table()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, client_id, frais, date FROM transactions
            WHERE type='credit' AND frais > 0
        """).fetchall()
        created = 0
        for r in rows:
            tid = r["id"]
            exists = conn.execute("SELECT COUNT(*) FROM frais_dus WHERE transaction_id=?", (tid,)).fetchone()[0]
            if exists == 0:
                conn.execute("""INSERT INTO frais_dus (client_id, transaction_id, montant, date, statut)
                                VALUES (?,?,?,?,'en_attente')""",
                             (r["client_id"], tid, r["frais"], r["date"]))
                created += 1
        conn.commit()
    return created

def get_frais_dus(client_id, statut="en_attente"):
    _ensure_frais_dus_table()
    with get_conn() as conn:
        if statut == "all":
            rows = conn.execute("SELECT * FROM frais_dus WHERE client_id=? ORDER BY date DESC", (client_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM frais_dus WHERE client_id=? AND statut=? ORDER BY date DESC", (client_id, statut)).fetchall()
    return [dict(r) for r in rows]

def get_total_frais_dus(client_id):
    _ensure_frais_dus_table()
    with get_conn() as conn:
        v = conn.execute("SELECT COALESCE(SUM(montant),0) FROM frais_dus WHERE client_id=? AND statut='en_attente'", (client_id,)).fetchone()[0]
    return round(v or 0, 2)

def set_frais_statut(frais_ids, statut):
    _ensure_frais_dus_table()
    with get_conn() as conn:
        for fid in frais_ids:
            conn.execute("UPDATE frais_dus SET statut=? WHERE id=?", (statut, int(fid)))
        conn.commit()
'''
    db = db.rstrip() + "\n" + block
    write("db.py", db)
    print("DB) table frais_dus + fonctions + migration ajoutees")
else:
    print("DB) frais_dus deja present")

# ════════════════════════════════════════════════════════════════
# API.PY  (routes avant la route racine "/")
# ════════════════════════════════════════════════════════════════
api = read("api.py")
if '/api/frais-dus' not in api:
    routes = '''
# -- FRAIS DUS ----------------------------------------------------------------
@app.route("/api/clients/<int:cid>/frais-dus")
@require_auth
def frais_dus_list(cid):
    db.migrate_frais_dus()  # s'assure que les frais existants sont presents
    return ok({"frais": db.get_frais_dus(cid, "en_attente"), "total": db.get_total_frais_dus(cid)})

@app.route("/api/frais-dus/facturer", methods=["POST"])
@require_auth
def frais_dus_facturer():
    data = request.json or {}
    ids = data.get("ids", [])
    cid = data.get("client_id")
    if not ids or not cid:
        return err("Selection vide")
    # Total des frais selectionnes
    frais_list = db.get_frais_dus(cid, "all")
    total = sum(f["montant"] for f in frais_list if f["id"] in [int(i) for i in ids])
    total = round(total, 2)
    if total <= 0:
        return err("Montant nul")
    # 1) Creer une transaction debit (ajoute a la dette)
    tid = db.add_transaction(
        client_id=cid, type_="debit", motif="Frais factures",
        quantite=1, prix_unitaire=total, mode_paiement="Liquide",
        frais=0, montant_brut=total, montant_net=total,
        reference="", notes="[FRAIS] Facturation de frais dus")
    # 2) Generer une facture pour cette transaction
    try:
        with db.get_conn() as conn:
            row = conn.execute("SELECT * FROM transactions WHERE id=?", (tid,)).fetchone()
        trans = dict(row) if row else None
        client = db.get_client(cid)
        if trans:
            html_content, numero = _build_facture_html(trans, client, "vente")
            db.create_facture(tid, cid, "vente", html_content, total)
    except Exception:
        pass
    # 3) Marquer les frais comme factures
    db.set_frais_statut(ids, "facture")
    return ok({"total": total, "transaction_id": tid})

@app.route("/api/frais-dus/oublier", methods=["POST"])
@require_auth
def frais_dus_oublier():
    data = request.json or {}
    ids = data.get("ids", [])
    if not ids:
        return err("Selection vide")
    db.set_frais_statut(ids, "oublie")
    return ok({"oublies": len(ids)})

'''
    idx = api.find('@app.route("/", defaults')
    if idx != -1:
        api = api[:idx] + routes + api[idx:]
        print("API) routes frais-dus ajoutees")
    else:
        print("API) ATTENTION route racine introuvable")
    write("api.py", api)
else:
    print("API) routes frais-dus deja presentes")

# ════════════════════════════════════════════════════════════════
# WEB : panneau frais dus + JS
# ════════════════════════════════════════════════════════════════
html = read("web/index.html")

# Charger le panneau a la fin de loadSolde : on accroche apres l'affichage.
# On injecte un appel loadFraisDus(cid) juste apres "content.style.display='flex';"
hook = "content.style.display='flex';"
if "loadFraisDus(" not in html and hook in html:
    html = html.replace(hook, hook + "\n  loadFraisDus(cid);", 1)
    print("WEB-1) appel loadFraisDus ajoute dans loadSolde")
elif "loadFraisDus(" in html:
    print("WEB-1) loadFraisDus deja appele")
else:
    print("WEB-1) ATTENTION hook loadSolde introuvable")

# Conteneur du panneau : on l'ajoute dans #soldeContent au debut (via JS, cree si absent)
if "function loadFraisDus" not in html:
    JS = r"""
<script>
// ===== FRAIS DUS (fiche client) =====
async function loadFraisDus(cid){
  if(!cid)return;
  var res=await api('/api/clients/'+cid+'/frais-dus');
  if(!res||!res.ok)return;
  var data=res.data;
  // Trouver ou creer le conteneur dans la fiche
  var content=document.getElementById('soldeContent');
  if(!content)return;
  var box=document.getElementById('fraisDusPanel');
  if(!box){
    box=document.createElement('div');
    box.id='fraisDusPanel';
    box.className='card';
    box.style.cssText='background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:20px';
    content.appendChild(box);
  }
  renderFraisDus(cid,data);
}
function renderFraisDus(cid,data){
  var box=document.getElementById('fraisDusPanel');
  if(!box)return;
  var frais=data.frais||[];
  var total=data.total||0;
  var h='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">'
    +'<div class="card-title" style="margin:0">Frais dus</div>'
    +'<div style="font-family:DM Mono,monospace;font-size:20px;font-weight:700;color:'+(total>0?'var(--gold2)':'var(--text3)')+'">'+total.toFixed(2)+' EUR</div></div>';
  if(!frais.length){
    h+='<div style="color:var(--text3);font-size:13px;text-align:center;padding:16px">Aucun frais en attente pour ce client</div>';
    box.innerHTML=h;
    return;
  }
  h+='<div style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px">';
  frais.forEach(function(f){
    var d=(f.date||'').slice(0,10);
    h+='<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius2);cursor:pointer">'
      +'<input type="checkbox" class="fraisDusCheck" value="'+f.id+'" data-montant="'+f.montant+'" onchange="updateFraisDusSel()" style="width:auto;margin:0">'
      +'<span style="flex:1;font-size:13px;color:var(--text)">Frais du '+d+'</span>'
      +'<span style="font-family:DM Mono,monospace;font-weight:600;color:var(--gold2)">'+parseFloat(f.montant).toFixed(2)+' EUR</span>'
      +'</label>';
  });
  h+='</div>';
  h+='<div style="display:flex;gap:8px;align-items:center">'
    +'<span id="fraisDusSelInfo" style="font-size:12px;color:var(--text3);margin-right:auto">0 selectionne(s) - 0.00 EUR</span>'
    +'<button class="btn" style="font-size:12px" onclick="fraisDusSelectAll(true)">Tout cocher</button>'
    +'<button class="btn danger" style="font-size:12px" onclick="oublierFraisDus('+cid+')">Oublier la selection</button>'
    +'<button class="btn primary" style="font-size:12px" onclick="facturerFraisDus('+cid+')">Facturer la selection</button>'
    +'</div>';
  box.innerHTML=h;
  updateFraisDusSel();
}
function getFraisDusChecked(){
  return Array.prototype.slice.call(document.querySelectorAll('.fraisDusCheck:checked'));
}
function updateFraisDusSel(){
  var checked=getFraisDusChecked();
  var total=checked.reduce(function(s,c){return s+(parseFloat(c.dataset.montant)||0);},0);
  var info=document.getElementById('fraisDusSelInfo');
  if(info)info.textContent=checked.length+' selectionne(s) - '+total.toFixed(2)+' EUR';
}
function fraisDusSelectAll(v){
  document.querySelectorAll('.fraisDusCheck').forEach(function(c){c.checked=v;});
  updateFraisDusSel();
}
async function facturerFraisDus(cid){
  var ids=getFraisDusChecked().map(function(c){return parseInt(c.value);});
  if(!ids.length){notify('Coche au moins un frais','error');return;}
  var total=getFraisDusChecked().reduce(function(s,c){return s+(parseFloat(c.dataset.montant)||0);},0);
  if(!confirm('Facturer '+ids.length+' frais ('+total.toFixed(2)+' EUR) ? Ils seront ajoutes a la dette et une facture sera generee.'))return;
  var res=await api('/api/frais-dus/facturer',{method:'POST',body:{ids:ids,client_id:cid}});
  if(res&&res.ok){
    notify('Frais factures : '+res.data.total.toFixed(2)+' EUR ajoutes a la dette');
    loadSolde();
    if(typeof loadDashboard==='function')loadDashboard();
  }else notify(res&&res.error?res.error:'Erreur','error');
}
async function oublierFraisDus(cid){
  var ids=getFraisDusChecked().map(function(c){return parseInt(c.value);});
  if(!ids.length){notify('Coche au moins un frais','error');return;}
  if(!confirm('Oublier '+ids.length+' frais ? Ils ne seront plus reclames.'))return;
  var res=await api('/api/frais-dus/oublier',{method:'POST',body:{ids:ids}});
  if(res&&res.ok){notify(ids.length+' frais oublie(s)');loadSolde();}
  else notify(res&&res.error?res.error:'Erreur','error');
}
</script>
"""
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+"\n"+JS+html[at:]
    print("WEB-2) JS frais dus injecte")
else:
    print("WEB-2) JS frais dus deja present")

write("web/index.html", html)

no=html.count("<script>");nc=html.count("</script>")
print("Balises script : %d / %d" % (no,nc))
print("")
print("=== TERMINE ===")
print("Frais dus : panneau sur la fiche client (cocher + Facturer + Oublier).")
