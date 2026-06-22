#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_rappel_actif.py
Permet de desactiver/reactiver le rappel d'un client.
 - db.py  : colonne 'actif' (migration) + set_rappel_actif()
 - api.py : route POST /api/rappels/actif
 - web    : boutons Desactiver/Reactiver dans la liste des retards, exclusion
            des desactives du compteur et du badge, historique relances inchange.
A lancer dans le dossier projet : python patch_rappel_actif.py
"""
import os
def read(p):
    with open(p,"r",encoding="utf-8",newline="") as f: return f.read()
def write(p,t):
    with open(p,"w",encoding="utf-8",newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def to_eol(b,eol): return eol.join(b.split("\n"))

DB_FUNCS = r'''def _ensure_rappel_actif():
    with get_conn() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(rappels)").fetchall()}
        if "actif" not in cols:
            conn.execute("ALTER TABLE rappels ADD COLUMN actif INTEGER DEFAULT 1")
            conn.commit()
def set_rappel_actif(client_id, actif, nom="", dette=0):
    """Active (1) ou desactive (0) le rappel d'un client. Cree la ligne si besoin
    (date vide pour ne pas compter comme une relance reelle)."""
    _ensure_rappel_actif()
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM rappels WHERE client_id=?", (client_id,)).fetchone()
        if row:
            conn.execute("UPDATE rappels SET actif=? WHERE client_id=?", (int(actif), client_id))
        else:
            conn.execute("INSERT INTO rappels (client_id,nom,dette,date,note,actif) VALUES (?,?,?,?,?,?)",
                         (client_id, nom, dette, "", "", int(actif)))
        conn.commit()
'''

API_ROUTE = r'''@app.route("/api/rappels/actif", methods=["POST"])
@require_auth
def rappels_set_actif():
    data = request.json or {}
    cid = data.get("client_id")
    if not cid:
        return err("client_id manquant")
    actif = 1 if data.get("actif", 1) else 0
    db.set_rappel_actif(int(cid), actif, data.get("nom", ""), data.get("dette", 0) or 0)
    return ok({"client_id": cid, "actif": actif})
'''

JS_FUNCS = r'''async function desactiverRappel(cid,nom,dette){
  if(!confirm('Désactiver les rappels pour '+nom+' ? Il ne sera plus relancé (réactivable à tout moment).'))return;
  const res=await api('/api/rappels/actif',{method:'POST',body:{client_id:cid,actif:0,nom:nom,dette:dette}});
  if(res&&res.ok){notify('Rappel désactivé pour '+nom);loadRappels();}else notify('Erreur','error');
}
async function reactiverRappel(cid){
  const res=await api('/api/rappels/actif',{method:'POST',body:{client_id:cid,actif:1}});
  if(res&&res.ok){notify('Rappel réactivé');loadRappels();}else notify('Erreur','error');
}
'''

NEW_FOREACH = r'''else retards.forEach(r=>{
    const urg=r.jours>rappelSettings.delai*3?'var(--red)':r.jours>rappelSettings.delai*2?'var(--gold2)':'var(--text2)';
    const nomEsc=String(r.nom||'').replace(/'/g,"\\'");
    var ri,actions;
    if(r.desactive){
      ri='<span style="color:var(--text3);font-size:11px">🔕 Rappel désactivé</span>';
      actions='<button class="btn" style="font-size:11px;padding:5px 12px" onclick="reactiverRappel('+r.id+')">🔔 Réactiver</button>';
    }else{
      ri=(r.rappel&&r.rappel.date)?'<span style="color:var(--green);font-size:11px">✓ Relancé le '+fmtDate(r.rappel.date)+'</span>':'<span style="color:var(--red);font-size:11px">⚠ Pas relancé</span>';
      actions='<button class="btn primary" style="font-size:11px;padding:5px 12px" onclick="marquerRelance('+r.id+',\''+nomEsc+'\','+r.dette+')">📨 Relancer</button> <button class="btn danger" style="font-size:11px;padding:5px 10px" onclick="desactiverRappel('+r.id+',\''+nomEsc+'\','+r.dette+')">🔕 Désactiver</button>';
    }
    const tr=document.createElement('tr');
    if(r.desactive)tr.style.opacity='0.5';
    tr.innerHTML='<td style="color:var(--text);font-weight:500">'+r.nom+'</td><td>'+fmtDate(r.lastDebit)+'</td><td><span style="color:'+urg+';font-weight:600;font-family:DM Mono,monospace">'+r.jours+' jours</span></td><td style="text-align:right"><span class="mono" style="color:var(--green)">+'+fmt(r.dette)+'</span></td><td>'+ri+'</td><td>'+actions+'</td>';
    tbody.appendChild(tr);
  });'''

def patch_db(path="db.py"):
    t=read(path); eol=eol_of(t)
    if "def set_rappel_actif" in t:
        print("db.py : set_rappel_actif deja present, saute"); return
    anchor='def add_rappel(client_id, nom, dette, date, note=""):'
    i=t.find(anchor)
    if i==-1: print("ATTENTION db.py : ancre add_rappel introuvable"); return
    t=t[:i]+to_eol(DB_FUNCS,eol)+eol+t[i:]
    write(path,t); print("db.py : _ensure_rappel_actif + set_rappel_actif ajoutes OK")

def patch_api(path="api.py"):
    t=read(path); eol=eol_of(t)
    if "/api/rappels/actif" in t:
        print("api.py : route /api/rappels/actif deja presente, saute"); return
    anchor='@app.route("/api/rappels/<int:rid>", methods=["DELETE"])'
    i=t.find(anchor)
    if i==-1: print("ATTENTION api.py : ancre route DELETE rappels introuvable"); return
    t=t[:i]+to_eol(API_ROUTE,eol)+eol+t[i:]
    write(path,t); print("api.py : route /api/rappels/actif ajoutee OK")

def repl(t, old, new, label):
    if old not in t:
        print("ATTENTION web : introuvable -> "+label); return t, False
    return t.replace(old, new, 1), True

def patch_web(path="web/index.html"):
    t=read(path); eol=eol_of(t)
    if "desactiverRappel" in t:
        print("web : deja patche, saute"); return
    ok_all=True
    # 1) push retard : ajoute desactive
    t,o=repl(t,
        "if(jours>=rappelSettings.delai)retards.push({id:c.id,nom:c.nom,dette:Math.round(dette*100)/100,jours,lastDebit:deb[0].date,rappel:rappelsDB.find(r=>r.client_id===c.id)});",
        "if(jours>=rappelSettings.delai){var _rp=rappelsDB.find(r=>r.client_id===c.id);retards.push({id:c.id,nom:c.nom,dette:Math.round(dette*100)/100,jours,lastDebit:deb[0].date,rappel:_rp,desactive:!!(_rp&&(_rp.actif===0||_rp.actif==='0'))});}",
        "push retard"); ok_all=ok_all and o
    # 2) compteur nb retards (exclut desactives)
    t,o=repl(t,
        "document.getElementById('rNbRetard').textContent=retards.length;",
        "document.getElementById('rNbRetard').textContent=retards.filter(function(r){return !r.desactive;}).length;",
        "compteur rNbRetard"); ok_all=ok_all and o
    # 3) montant retards (exclut desactives)
    t,o=repl(t,
        "document.getElementById('rMontantRetard').textContent=fmt(retards.reduce((s,r)=>s+r.dette,0));",
        "document.getElementById('rMontantRetard').textContent=fmt(retards.filter(function(r){return !r.desactive;}).reduce((s,r)=>s+r.dette,0));",
        "montant rMontantRetard"); ok_all=ok_all and o
    # 4) tri : desactives en bas
    t,o=repl(t,
        "retards.sort((a,b)=>b.jours-a.jours);",
        "retards.sort((a,b)=>(a.desactive?1:0)-(b.desactive?1:0)||b.jours-a.jours);",
        "tri retards"); ok_all=ok_all and o
    # 5) rendu forEach (region)
    s=t.find("else retards.forEach(r=>{")
    if s==-1:
        print("ATTENTION web : forEach retards introuvable"); ok_all=False
    else:
        mid=t.find("tbody.appendChild(tr);", s)
        e=t.find("});", mid)
        if mid==-1 or e==-1:
            print("ATTENTION web : fin du forEach retards introuvable"); ok_all=False
        else:
            e=e+len("});")
            t=t[:s]+to_eol(NEW_FOREACH,eol)+t[e:]
            print("web : rendu forEach retards remplace OK")
    # 6) historique relances : n'afficher que les vraies relances (date non vide)
    t,o=repl(t,
        "const sorted=rappelsDB.slice().sort((a,b)=>(b.date||'').localeCompare(a.date||'')).slice(0,30);",
        "const sorted=rappelsDB.slice().filter(function(r){return r.date;}).sort((a,b)=>(b.date||'').localeCompare(a.date||'')).slice(0,30);",
        "historique relances"); ok_all=ok_all and o
    # 7) fonctions desactiver/reactiver avant supprimerRappel
    anchor="async function supprimerRappel(rid){"
    i=t.find(anchor)
    if i==-1:
        print("ATTENTION web : supprimerRappel introuvable"); ok_all=False
    else:
        t=t[:i]+to_eol(JS_FUNCS,eol)+eol+t[i:]
        print("web : desactiverRappel + reactiverRappel ajoutees OK")
    # 8) badge : recupere rappels + exclut desactives
    t,o=repl(t,
        "var _r803=await Promise.all([api('/api/clients'),api('/api/transactions?limit=2000')]);var cr=_r803[0];var tr2=_r803[1];",
        "var _r803=await Promise.all([api('/api/clients'),api('/api/transactions?limit=2000'),api('/api/rappels')]);var cr=_r803[0];var tr2=_r803[1];var rr=_r803[2];",
        "badge promise.all"); ok_all=ok_all and o
    t,o=repl(t,
        "const clients=cr.data;const allTrans=(tr2 && tr2.data ? tr2.data : []);const today=new Date();let nb=0;",
        "const clients=cr.data;const allTrans=(tr2 && tr2.data ? tr2.data : []);const _rdb=(rr&&rr.data?rr.data:[]);const _off={};_rdb.forEach(function(r){if(r.actif===0||r.actif==='0')_off[r.client_id]=1;});const today=new Date();let nb=0;",
        "badge clients line"); ok_all=ok_all and o
    t,o=repl(t,
        "if(jours>=rappelSettings.delai)nb++;",
        "if(jours>=rappelSettings.delai&&!_off[c.id])nb++;",
        "badge compteur"); ok_all=ok_all and o
    write(path,t)
    print("web : patch applique" + ("" if ok_all else " (AVEC AVERTISSEMENTS - verifie ci-dessus)"))

if __name__=="__main__":
    if os.path.exists("db.py"): patch_db()
    else: print("ATTENTION db.py introuvable")
    if os.path.exists("api.py"): patch_api()
    else: print("ATTENTION api.py introuvable")
    if os.path.exists("web/index.html"): patch_web()
    else: print("ATTENTION web/index.html introuvable")
    print("=== TERMINE ===")
