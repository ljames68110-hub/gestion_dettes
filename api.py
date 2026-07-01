# api.py — Serveur Flask pour Gestion Dettes Premium
"""
Lance un serveur HTTP local (127.0.0.1:5000) que l'interface web consulte.
Toutes les routes nécessitent un token de session sauf /api/auth/login et /api/auth/status.
"""

import os
import secrets
import csv
import io
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, make_response
from flask_cors import CORS

import db
try:
    import updater
    HAS_UPDATER = True
except ImportError:
    HAS_UPDATER = False

import sys as _sys

def _get_web_folder():
    """Retourne le chemin du dossier web/ — fonctionne en mode normal ET PyInstaller."""
    if getattr(_sys, "frozen", False):
        # Mode exe PyInstaller : les fichiers sont dans _MEIPASS
        return os.path.join(_sys._MEIPASS, "web")
    # Mode développement : dossier web/ à côté de api.py
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

_WEB_FOLDER = _get_web_folder()
app = Flask(__name__, static_folder=_WEB_FOLDER, static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "http://127.0.0.1:5000"}})

# Token de session en mémoire (valide jusqu'au redémarrage)
PENDING_UPDATE = None  # infos de la mise à jour disponible
SESSION_TOKEN = None
TOKEN_HEADER = "X-Session-Token"

# ── HELPERS ──────────────────────────────────────────────────────────────────

def ok(data=None, **kw):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(kw)
    return jsonify(payload)

def err(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code

def require_auth(f):
    """Décorateur : vérifie le token de session."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get(TOKEN_HEADER) or request.args.get("token")
        if not token or token != SESSION_TOKEN:
            return err("Non autorisé — veuillez vous connecter", 401)
        return f(*args, **kwargs)
    return wrapper

# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/status")
def auth_status():
    """L'app demande si un PIN est déjà configuré."""
    return ok({"has_pin": db.has_pin()})

@app.route("/api/auth/setup", methods=["POST"])
def auth_setup():
    """Premier lancement : définir le PIN."""
    if db.has_pin():
        return err("PIN déjà configuré", 409)
    data = request.json or {}
    pin = str(data.get("pin", "")).strip()
    if len(pin) < 4:
        return err("Le PIN doit contenir au moins 4 caractères")
    db.set_pin(pin)
    return ok({"message": "PIN configuré"})

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Vérifie le PIN et retourne un token de session."""
    global SESSION_TOKEN
    data = request.json or {}
    pin = str(data.get("pin", "")).strip()
    if not db.check_pin(pin):
        return err("PIN incorrect", 401)
    SESSION_TOKEN = secrets.token_hex(32)
    return ok({"token": SESSION_TOKEN})

@app.route("/api/auth/logout", methods=["POST"])
@require_auth
def auth_logout():
    global SESSION_TOKEN
    SESSION_TOKEN = None
    return ok({"message": "Déconnecté"})

@app.route("/api/auth/change-pin", methods=["POST"])
@require_auth
def auth_change_pin():
    data = request.json or {}
    old_pin = str(data.get("old_pin", "")).strip()
    new_pin = str(data.get("new_pin", "")).strip()
    if not db.check_pin(old_pin):
        return err("Ancien PIN incorrect", 401)
    if len(new_pin) < 4:
        return err("Le nouveau PIN doit contenir au moins 4 chiffres")
    # auth_type envoyé explicitement par le frontend
    auth_type = data.get("auth_type", "pin")
    if auth_type not in ("pin", "password"):
        auth_type = "pin"
    db.set_pin(new_pin, auth_type)
    return ok({"message": "Code mis à jour"})

# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@require_auth
def dashboard():
    return ok(db.get_stats_global())

# ── CLIENTS ───────────────────────────────────────────────────────────────────

@app.route("/api/clients")
@require_auth
def clients_list():
    return ok(db.get_clients())

@app.route("/api/clients", methods=["POST"])
@require_auth
def clients_create():
    data = request.json or {}
    nom = (data.get("nom") or "").strip()
    if not nom:
        return err("Le champ 'nom' est obligatoire")
    cid = db.add_client(
        nom=nom,
        email=data.get("email", ""),
        tel=data.get("tel", ""),
        notes=data.get("notes", ""),
        photo=data.get("photo", ""),
    )
    return ok(db.get_client(cid)), 201

@app.route("/api/clients/<int:cid>")
@require_auth
def clients_get(cid):
    c = db.get_client(cid)
    if not c:
        return err("Client introuvable", 404)
    return ok(c)

@app.route("/api/clients/<int:cid>", methods=["PUT"])
@require_auth
def clients_update(cid):
    data = request.json or {}
    if not db.update_client(cid, **{k: data.get(k) for k in ("nom","email","tel","notes","photo")}):
        return err("Client introuvable", 404)
    return ok(db.get_client(cid))

@app.route("/api/clients/<int:cid>", methods=["DELETE"])
@require_auth
def clients_delete(cid):
    if not db.get_client(cid):
        return err("Client introuvable", 404)
    db.delete_client(cid)
    return ok({"deleted": cid})

@app.route("/api/clients/<int:cid>/stats-comptes")
@require_auth
def client_stats_comptes(cid):
    """Retourne les stats par compte (euro/cantine/tabac) pour un client."""
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT 
                COALESCE(compte,'euro') as compte,
                type,
                COALESCE(SUM(montant_brut),0) as total_brut,
                COALESCE(SUM(montant_net),0) as total_net,
                COALESCE(SUM(frais),0) as total_frais,
                COUNT(*) as nb
            FROM transactions
            WHERE client_id=?
            GROUP BY COALESCE(compte,'euro'), type
        """, (cid,)).fetchall()

        paye_rows = conn.execute("""
            SELECT COALESCE(compte,'euro') as compte, COALESCE(SUM(montant_net),0) as paye
            FROM transactions
            WHERE client_id=? AND type='debit' AND notes LIKE '%[CAISSE PAYE]%'
            GROUP BY COALESCE(compte,'euro')
        """, (cid,)).fetchall()
        paye = {}
        for _pr in paye_rows:
            paye[_pr["compte"]] = _pr["paye"]
        _assoc = conn.execute("SELECT COALESCE(associe,0) FROM clients WHERE id=?", (cid,)).fetchone()[0] or 0
    
    result = {"euro":{"debit":0,"credit":0,"frais":0}, 
              "cantine":{"debit":0,"credit":0,"frais":0},
              "tabac":{"debit":0,"credit":0,"frais":0}}
    
    for r in rows:
        compte = r["compte"] if r["compte"] in result else "euro"
        if r["type"] == "debit":
            result[compte]["debit"] += r["total_net"]
        else:
            result[compte]["credit"] += r["total_net"]
            result[compte]["frais"] += r["total_frais"]
    
    # Calculer les soldes
    for c in result:
        result[c]["solde"] = round(result[c]["debit"] - (0 if _assoc else paye.get(c, 0)) - result[c]["credit"], 2)
        result[c]["debit"] = round(result[c]["debit"], 2)
        result[c]["credit"] = round(result[c]["credit"], 2)
    
    return ok(result)

@app.route("/api/clients/<int:cid>/stats")
@require_auth
def clients_stats(cid):
    if not db.get_client(cid):
        return err("Client introuvable", 404)
    return ok(db.get_stats_client(cid))

@app.route("/api/clients/<int:cid>/transactions")
@require_auth
def clients_transactions(cid):
    if not db.get_client(cid):
        return err("Client introuvable", 404)
    return ok(db.get_transactions(cid))

# ── TRANSACTIONS ──────────────────────────────────────────────────────────────

FEES = {"Liquide": 0, "Virement": 0, "PCS": 0.07, "Paysafecard": 0.05, "WesternUnion": 0}

@app.route("/api/transactions")
@require_auth
def transactions_list():
    limit = min(int(request.args.get("limit", 200)), 1000)
    return ok(db.get_all_transactions(limit))

@app.route("/api/transactions", methods=["POST"])
@require_auth
def transactions_create():
    data = request.json or {}

    # Validation
    required = ["client_id", "type", "motif", "quantite", "prix_unitaire", "mode_paiement"]
    for field in required:
        if field not in data:
            return err(f"Champ manquant : {field}")

    type_  = data["type"]
    if type_ not in ("credit", "debit"):
        return err("type doit être 'credit' ou 'debit'")

    if not db.get_client(data["client_id"]):
        return err("Client introuvable", 404)

    qty   = float(data["quantite"]) if data.get("unite","piece") == "gramme" else float(data.get("quantite", 1))
    pu    = float(data["prix_unitaire"])
    mode  = data["mode_paiement"]
    unite = data.get("unite", "piece")
    entree_id = data.get("entree_id")
    linked_debit_id = data.get("linked_debit_id")
    frais_deduits = int(data.get("frais_deduits", 1))

    brut  = round(qty * pu, 2)
    if type_ == "credit":
        frais_rate = FEES.get(mode, 0) if frais_deduits else 0
        frais = round(brut * frais_rate, 2)
        # Si j absorbe les frais : net = brut (client credite du total)
        net = round(brut - frais, 2)
    else:
        frais = 0
        net = brut

    tid = db.add_transaction(
        client_id     = data["client_id"],
        type_         = type_,
        motif         = data["motif"],
        quantite      = qty,
        prix_unitaire = pu,
        mode_paiement = mode,
        frais         = frais,
        montant_brut  = brut,
        montant_net   = net,
        reference     = data.get("reference", ""),
        notes         = data.get("notes", ""),
        date          = data.get("date") or None,
    )

    # Sauvegarder entree_id, linked_debit_id, unite, compte dans la transaction
    compte = data.get("compte", "euro")
    if entree_id or linked_debit_id or unite != "piece" or compte != "euro":
        with db.get_conn() as conn:
            conn.execute("""UPDATE transactions SET entree_id=?, linked_debit_id=?, unite=?, compte=?
                           WHERE id=?""", (entree_id, linked_debit_id, unite, compte, tid))
            conn.commit()

    # Mettre à jour le stock si vente liée à une entrée
    if entree_id and type_ == "debit":
        db.update_stock(int(entree_id), qty)

    trans = db.get_transactions(data["client_id"])
    created = next((t for t in trans if t["id"] == tid), None)

    # ── Génération automatique de la facture ──────────────────────────────────
    try:
        client = db.get_client(data["client_id"])
        type_doc = "vente" if type_ == "debit" else "remboursement"
        if created and not data.get("no_facture"):
            html_content, numero = _build_facture_html(created, client, type_doc)
            db.create_facture(tid, data["client_id"], type_doc, html_content, net)
    except Exception as _fe:
        pass  # La facture est optionnelle, on ne bloque pas la transaction

    return ok(created), 201

@app.route("/api/transactions/<int:tid>", methods=["PUT"])
@require_auth
def transactions_update(tid):
    data = request.json or {}
    result = db.update_transaction(tid, data)
    if not result:
        return err("Transaction introuvable", 404)
    return ok(result)

@app.route("/api/transactions/<int:tid>", methods=["DELETE"])
@require_auth
def transactions_delete(tid):
    db.delete_transaction(tid)
    return ok({"deleted": tid})

# ── EXPORT ────────────────────────────────────────────────────────────────────

@app.route("/api/export/csv/<int:cid>")
@require_auth
def export_csv(cid):
    """Génère un CSV pour un client et le renvoie en téléchargement."""
    client = db.get_client(cid)
    if not client:
        return err("Client introuvable", 404)

    rows = db.get_transactions(cid)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id","date","type","motif","quantite","prix_unitaire",
        "montant_brut","mode_paiement","frais","montant_net","reference","notes"
    ])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

    filename = f"export_{client['nom'].replace(' ','_')}_{cid}.csv"
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

@app.route("/api/export/csv/all")
@require_auth
def export_csv_all():
    """CSV complet toutes transactions."""
    rows = db.get_all_transactions(limit=10000)
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=export_complet.csv"
    return response

# ── MISE À JOUR ───────────────────────────────────────────────────────────────

@app.route("/api/update/check")
@require_auth
def update_check():
    """Vérifie si une mise à jour est disponible."""
    if not HAS_UPDATER:
        return ok({"available": False, "reason": "updater non disponible", "current_version": "?"})
    global PENDING_UPDATE
    remote = updater.fetch_remote_info()
    if not remote:
        return ok({"available": False, "reason": "Impossible de joindre GitHub", "current_version": (updater.get_current_version().get("version","?") if HAS_UPDATER else "?")})
    current = updater.get_current_version()
    available = updater.version_gt(remote.get("version","0"), current.get("version","0"))
    if available:
        PENDING_UPDATE = remote
    return ok({
        "available":       available,
        "current_version": current.get("version","?"),
        "new_version":     remote.get("version","?") if available else None,
    })

@app.route("/api/update/apply", methods=["POST"])
@require_auth
def update_apply():
    """Lance le téléchargement et l'installation de la mise à jour."""
    global PENDING_UPDATE
    if not HAS_UPDATER:
        return err("updater non disponible")
    if not PENDING_UPDATE:
        return err("Aucune mise à jour en attente — faites d'abord /api/update/check")
    rem = PENDING_UPDATE
    import threading, tempfile, time
    def _do():
        try:
            exe = updater.get_current_exe()
            if not exe:
                print("[Updater] mode dev - pas d'exe a remplacer"); return
            tmp = tempfile.NamedTemporaryFile(suffix=".exe", dir=exe.parent, delete=False); tmp.close()
            updater.download_update(rem["asset_url"], tmp.name, rem.get("sha256"))
            updater.apply_update_windows(tmp.name, str(exe))
            time.sleep(2); os._exit(0)
        except Exception as e:
            print(f"[Updater] erreur apply: {e}")
    threading.Thread(target=_do, daemon=True).start()
    return ok({"message": f"Téléchargement de {PENDING_UPDATE['version']} en cours..."})



@app.route("/api/clients/<int:cid>/dettes-ouvertes")
@require_auth
def dettes_ouvertes(cid):
    """Retourne les débits non totalement remboursés d'un client."""
    with db.get_conn() as conn:
        _assoc = conn.execute("SELECT COALESCE(associe,0) FROM clients WHERE id=?", (cid,)).fetchone()[0] or 0
        excl_paye = (not _assoc)
        rows = conn.execute(
            "SELECT id, date, type, COALESCE(montant_net,0), COALESCE(montant_brut,0), linked_debit_id, "
            "motif, mode_paiement, notes, quantite, COALESCE(unite,'piece'), COALESCE(compte,'euro'), COALESCE(prix_unitaire,0) "
            "FROM transactions WHERE client_id=? AND type IN ('debit','credit') "
            "ORDER BY date ASC, id ASC", (cid,)).fetchall()
        rem = {}
        opened = []
        info = {}
        for r in rows:
            rid, rtype, mnet, mbrut, linked = r[0], r[2], r[3], r[4], r[5]
            notes = r[8] or ""
            if rtype == 'debit':
                if excl_paye and ('[CAISSE PAYE]' in notes):
                    continue
                rem[rid] = mnet
                opened.append(rid)
                info[rid] = r
            else:
                amt = mbrut
                if linked and (linked in rem) and rem[linked] > 0:
                    take = min(rem[linked], amt); rem[linked] -= take; amt -= take
                if amt > 0:
                    for did in reversed(opened):
                        if amt <= 0:
                            break
                        if rem.get(did, 0) > 0:
                            take = min(rem[did], amt); rem[did] -= take; amt -= take
        result = []
        for did in reversed(opened):
            restant = rem.get(did, 0)
            if restant > 0.01:
                d = info[did]
                montant_net = d[3]
                result.append({
                    "id": did,
                    "date": d[1],
                    "motif": d[6],
                    "montant_net": montant_net,
                    "mode_paiement": d[7],
                    "notes": d[8] or "",
                    "quantite": d[9],
                    "unite": d[10],
                    "compte": d[11],
                    "prix_unitaire": d[12],
                    "total_credite": round(montant_net - restant, 2),
                    "restant": round(restant, 2)
                })
    return ok(result)




# ── TARIFS ────────────────────────────────────────────────────────────────────

@app.route("/api/tarifs")
@require_auth
def tarifs_list():
    return ok(db.get_tarifs())

@app.route("/api/tarifs", methods=["POST"])
@require_auth
def tarifs_save():
    data = request.json or {}
    article = data.get("article","")
    prix = float(data.get("prix_unitaire", 0))
    db.save_tarif(article, prix)
    return ok({"saved": article})


# ── SETTINGS ──────────────────────────────────────────────────────────────────

@app.route("/api/settings")
@require_auth
def settings_list():
    return ok(db.get_all_settings())

@app.route("/api/settings", methods=["POST"])
@require_auth
def settings_save():
    data = request.json or {}
    for key, value in data.items():
        db.set_setting(key, value)
    return ok({"saved": len(data)})

# ── BACKUP ────────────────────────────────────────────────────────────────────

@app.route("/api/backup/create", methods=["POST"])
@require_auth
def backup_create():
    """Crée une sauvegarde de la base de données."""
    import shutil
    from datetime import datetime
    backup_dir = os.path.join(os.path.dirname(db.DB_FILE), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"dettes_backup_{date_str}.db")
    shutil.copy2(db.DB_FILE, backup_path)
    # Garder seulement les 10 dernières sauvegardes
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
    for old in backups[:-10]:
        os.remove(os.path.join(backup_dir, old))
    return ok({"path": backup_path, "date": date_str})

@app.route("/api/backup/list")
@require_auth  
def backup_list():
    """Liste les sauvegardes disponibles."""
    backup_dir = os.path.join(os.path.dirname(db.DB_FILE), "backups")
    if not os.path.exists(backup_dir):
        return ok([])
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')], reverse=True)
    result = []
    for b in backups[:10]:
        path = os.path.join(backup_dir, b)
        size = os.path.getsize(path)
        result.append({"name": b, "path": path, "size": size})
    return ok(result)

@app.route("/api/backup/restore", methods=["POST"])
@require_auth
def backup_restore():
    """Restaure une sauvegarde."""
    import shutil
    data = request.json or {}
    backup_path = data.get("path", "")
    if not backup_path or not os.path.exists(backup_path):
        return err("Sauvegarde introuvable")
    shutil.copy2(backup_path, db.DB_FILE)
    return ok({"restored": backup_path})

# ── MOTIFS ────────────────────────────────────────────────────────────────────

@app.route("/api/motifs")
@require_auth
def motifs_list():
    try:
        return ok(db.get_motifs())
    except Exception as e:
        import traceback
        print(f"[MOTIFS ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        # Fallback: retourner liste vide si table pas encore créée
        try:
            import sqlite3
            conn = sqlite3.connect(db.DB_FILE)
            conn.execute("""CREATE TABLE IF NOT EXISTS motifs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE,
                actif INTEGER DEFAULT 1
            )""")
            for m in ["Achat","Bedo","Blonde","Cigarette","Pot","Recharge","Tabac","Autre"]:
                try: conn.execute("INSERT INTO motifs (nom) VALUES (?)", (m,))
                except: pass
            conn.commit()
            rows = conn.execute("SELECT * FROM motifs WHERE actif=1 ORDER BY nom").fetchall()
            result = [{"id": r[0], "nom": r[1], "actif": r[2]} for r in rows]
            conn.close()
            return ok(result)
        except Exception as e2:
            return err(f"Erreur motifs: {str(e2)}", 500)

@app.route("/api/motifs", methods=["POST"])
@require_auth
def motifs_create():
    data = request.json or {}
    nom = data.get("nom", "").strip()
    if not nom:
        return err("Nom requis")
    db.add_motif(nom)
    return ok({"created": nom}), 201

@app.route("/api/motifs/<int:mid>", methods=["PUT"])
@require_auth
def motifs_update(mid):
    data = request.json or {}
    nom = data.get("nom", "").strip()
    if not nom:
        return err("Nom requis")
    db.update_motif(mid, nom)
    return ok({"updated": mid})

@app.route("/api/motifs/<int:mid>", methods=["DELETE"])
@require_auth
def motifs_delete(mid):
    db.delete_motif(mid)
    return ok({"deleted": mid})

# ── ENTRÉES MATÉRIEL ──────────────────────────────────────────────────────────

@app.route("/api/entrees")
@require_auth
def entrees_list():
    return ok(db.get_entrees())

@app.route("/api/entrees", methods=["POST"])
@require_auth
def entrees_create():
    data = request.json or {}
    if not data.get("description"):
        return err("Description requise")
    eid = db.add_entree(
        description = data["description"],
        quantite    = float(data.get("quantite", 1)),
        prix_achat  = float(data.get("prix_achat", 0)),
        date        = data.get("date", ""),
        notes       = data.get("notes", ""),
        unite       = data.get("unite", "piece"),
    )
    return ok({"id": eid}), 201

@app.route("/api/entrees/<int:eid>", methods=["PUT"])
@require_auth
def entrees_update(eid):
    data = request.json or {}
    db.update_entree(eid, data.get("description",""), float(data.get("quantite",1)),
                     float(data.get("prix_achat",0)), data.get("date",""), data.get("notes",""),
                     data.get("unite","piece"))
    return ok({"updated": eid})

@app.route("/api/entrees/<int:eid>", methods=["DELETE"])
@require_auth
def entrees_delete(eid):
    db.delete_entree(eid)
    return ok({"deleted": eid})

# ── RÉCAPITULATIF MENSUEL ─────────────────────────────────────────────────────

@app.route("/api/recap-mensuel")
@require_auth
def recap_mensuel():
    mois = request.args.get("mois", "")  # format YYYY-MM
    with db.get_conn() as conn:
        # Ventes du mois
        q = """
            SELECT t.*, c.nom as client_nom,
                   e.description as entree_desc, e.date as entree_date
            FROM transactions t
            LEFT JOIN clients c ON t.client_id = c.id
            LEFT JOIN entrees_materiel e ON t.entree_id = e.id
            WHERE 1=1
        """
        params = []
        if mois:
            q += " AND substr(t.date,1,7) = ?"
            params.append(mois)
        q += " ORDER BY t.date DESC"
        rows = conn.execute(q, params).fetchall()
        transactions = [dict(r) for r in rows]

        # Entrées matériel du mois
        eq = "SELECT * FROM entrees_materiel WHERE 1=1"
        eparams = []
        if mois:
            eq += " AND substr(date,1,7) = ?"
            eparams.append(mois)
        eq += " ORDER BY date DESC"
        erows = conn.execute(eq, eparams).fetchall()
        entrees = [dict(r) for r in erows]

    return ok({"transactions": transactions, "entrees": entrees})

# ── RAPPELS ───────────────────────────────────────────────────────────────────

@app.route("/api/rappels")
@require_auth
def rappels_list():
    return ok(db.get_rappels())

@app.route("/api/rappels", methods=["POST"])
@require_auth
def rappels_create():
    data = request.json or {}
    if not data.get("client_id"):
        return err("client_id requis")
    rid = db.add_rappel(
        client_id = int(data["client_id"]),
        nom       = data.get("nom", ""),
        dette     = float(data.get("dette", 0)),
        date      = data.get("date", ""),
        note      = data.get("note", ""),
    )
    return ok({"id": rid}), 201

@app.route("/api/rappels/actif", methods=["POST"])
@require_auth
def rappels_set_actif():
    data = request.json or {}
    cid = data.get("client_id")
    if not cid:
        return err("client_id manquant")
    actif = 1 if data.get("actif", 1) else 0
    db.set_rappel_actif(int(cid), actif, data.get("nom", ""), data.get("dette", 0) or 0)
    return ok({"client_id": cid, "actif": actif})

@app.route("/api/rappels/<int:rid>", methods=["DELETE"])
@require_auth
def rappels_delete(rid):
    db.delete_rappel(rid)
    return ok({"deleted": rid})

@app.route("/api/rappels/client/<int:cid>", methods=["DELETE"])
@require_auth
def rappels_delete_by_client(cid):
    db.delete_rappel_by_client(cid)
    return ok({"deleted_client": cid})


# ── EXPORT / IMPORT BASE DE DONNÉES ──────────────────────────────────────────


@app.route("/api/export/db/save", methods=["POST"])
@require_auth
def export_db_save():
    """Sauvegarde la base via boite de dialogue Windows ou dans Documents."""
    import shutil
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"GestionPerso_backup_{date_str}.db"
    db_path  = db.DB_FILE
    if not os.path.exists(db_path):
        return err("Base introuvable", 404)

    # Essayer boite de dialogue Windows
    save_path = None
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        save_path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("Base SQLite", "*.db"), ("Tous les fichiers", "*.*")],
            initialfile=filename,
            title="Exporter la base de données"
        )
        root.destroy()
    except Exception:
        pass

    if not save_path:
        # Fallback : sauvegarder dans Documents
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        os.makedirs(docs, exist_ok=True)
        save_path = os.path.join(docs, filename)

    shutil.copy2(db_path, save_path)
    return ok({"path": save_path, "filename": filename})

@app.route("/api/export/db")
@require_auth
def export_db():
    """Télécharge le fichier dettes.db complet."""
    import shutil, tempfile
    from flask import send_file
    db_path = db.DB_FILE
    if not os.path.exists(db_path):
        return err("Base de données introuvable", 404)
    # Copier dans un temp pour éviter les locks SQLite
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    shutil.copy2(db_path, tmp.name)
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        tmp.name,
        as_attachment=True,
        download_name=f"GestionPerso_backup_{date_str}.db",
        mimetype="application/octet-stream"
    )

@app.route("/api/import/db", methods=["POST"])
@require_auth
def import_db():
    """Remplace la base de données par le fichier uploadé."""
    import shutil, tempfile, sqlite3
    if "db" not in request.files:
        return err("Fichier manquant")
    f = request.files["db"]
    if not f.filename.endswith(".db"):
        return err("Le fichier doit être un .db SQLite")
    # Sauvegarder dans un temp
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.save(tmp.name)
    tmp.close()
    # Vérifier que c'est bien un fichier SQLite valide
    try:
        conn = sqlite3.connect(tmp.name)
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
    except Exception as e:
        os.remove(tmp.name)
        return err(f"Fichier SQLite invalide : {e}")
    # Backup de l'ancienne base
    db_path = db.DB_FILE
    backup_path = db_path + ".backup"
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
    # Remplacer la base
    shutil.move(tmp.name, db_path)
    # Réinitialiser la connexion
    db.init_db()
    return ok({"message": "Base importée avec succès"})


@app.route("/api/export/csv/save", methods=["POST"])
@require_auth
def export_csv_save():
    """Export CSV complet avec boite de dialogue Windows."""
    import csv, io, tempfile
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"GestionPerso_export_{date_str}.csv"

    # Générer le CSV
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT t.date, c.nom, t.type, t.motif, t.mode_paiement,
                   t.quantite, t.prix_unitaire, t.montant_brut, t.frais, t.montant_net,
                   e.description as entree, t.notes
            FROM transactions t
            LEFT JOIN clients c ON t.client_id = c.id
            LEFT JOIN entrees_materiel e ON t.entree_id = e.id
            ORDER BY t.date DESC
        """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Date','Client','Type','Motif','Mode','Quantite','Prix unitaire',
                     'Montant brut','Frais','Montant net','Entree materiel','Notes'])
    for r in rows:
        writer.writerow([
            r[0], r[1],
            'Vente' if r[2]=='debit' else 'Remboursement',
            r[3], r[4], r[5], r[6], r[7], r[8], r[9],
            r[10] or '', r[11] or ''
        ])

    csv_content = output.getvalue()

    # Boite de dialogue Windows
    save_path = None
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Tous les fichiers", "*.*")],
            initialfile=filename, title="Exporter les transactions"
        )
        root.destroy()
    except Exception: pass

    if not save_path:
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        os.makedirs(docs, exist_ok=True)
        save_path = os.path.join(docs, filename)

    with open(save_path, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(csv_content)

    return ok({"path": save_path})


# ── ASSISTANT IA ──────────────────────────────────────────────────────────────

@app.route("/api/ai/claude", methods=["POST"])
@require_auth
def ai_claude():
    """Proxy vers l API Claude pour l assistant IA."""
    import urllib.request, json as _json
    data = request.json or {}
    message = data.get("message", "")
    context = data.get("context", "")
    history = data.get("history", [])

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return err("Cle API Claude non configuree. Ajoutez ANTHROPIC_API_KEY dans les variables d environnement.")

    messages = [{"role":"user","content":context}]
    for h in history[-6:]:
        messages.append(h)
    messages.append({"role":"user","content":message})

    payload = _json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 500,
        "messages": messages
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = _json.loads(r.read().decode())
            response = result["content"][0]["text"]
            return ok({"response": response})
    except Exception as e:
        return err(f"Erreur Claude API : {e}")


# ── CATALOGUE ─────────────────────────────────────────────────────────────────

@app.route("/api/catalogue")
@require_auth
def catalogue_list():
    return ok(db.get_catalogue())

@app.route("/api/catalogue", methods=["POST"])
@require_auth
def catalogue_create():
    data = request.json or {}
    nom = (data.get("nom") or "").strip()
    if not nom:
        return err("Nom requis")
    iid = db.add_catalogue_item(
        nom          = nom,
        categorie    = data.get("categorie", "Général"),
        description  = data.get("description", ""),
        prix_vente   = float(data.get("prix_vente", 0)),
        prix_achat   = float(data.get("prix_achat", 0)),
        unite        = data.get("unite", "piece"),
        stock_min    = float(data.get("stock_min", 0)),
        stock        = float(data.get("stock", 0)),
        grammes_piece = float(data.get("grammes_piece", 0) or 0),
        code_barre   = (data.get("code_barre") or "").strip(),
    )
    return ok(db.get_catalogue_item(iid)), 201

@app.route("/api/catalogue/<int:iid>", methods=["PUT"])
@require_auth
def catalogue_update(iid):
    data = request.json or {}
    nom = (data.get("nom") or "").strip()
    if not nom:
        return err("Nom requis")
    db.update_catalogue_item(
        item_id      = iid,
        nom          = nom,
        categorie    = data.get("categorie", "Général"),
        description  = data.get("description", ""),
        prix_vente   = float(data.get("prix_vente", 0)),
        prix_achat   = float(data.get("prix_achat", 0)),
        unite        = data.get("unite", "piece"),
        stock_min    = float(data.get("stock_min", 0)),
        stock        = (float(data["stock"]) if "stock" in data and data["stock"] is not None else None),
        grammes_piece = (float(data["grammes_piece"]) if "grammes_piece" in data and data["grammes_piece"] is not None else None),
        code_barre   = data.get("code_barre"),
    )
    return ok(db.get_catalogue_item(iid))

@app.route("/api/catalogue/<int:iid>", methods=["DELETE"])
@require_auth
def catalogue_delete(iid):
    db.delete_catalogue_item(iid)
    return ok({"deleted": iid})

# ── FACTURES ──────────────────────────────────────────────────────────────────

def _fmt_ticket(raw):
    parts = []
    for p in (raw or '').split('|'):
        if ':' in p:
            c, am = p.rsplit(':', 1)
            parts.append(f'{c} ({am} €)' if am else c)
        elif p:
            parts.append(p)
    return ', '.join(parts)

def _build_facture_html(trans, client, type_):
    """Génère le HTML d'une facture ou d'un bon de remboursement."""
    from datetime import datetime
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    date_trans = trans.get("date","")[:10].split("-")
    date_fmt = "/".join(reversed(date_trans)) if len(date_trans)==3 else trans.get("date","")
    is_vente = type_ == "vente"
    _paye = is_vente and ("[CAISSE PAYE]" in (trans.get("notes") or ""))
    titre = "FACTURE DE VENTE" if is_vente else ("BON DE DÉPÔT" if (client and client.get("associe")) else "BON DE REMBOURSEMENT")
    couleur = "#16a34a" if is_vente else "#c9a84c"
    _logo = db.get_setting("app_logo", "")
    _logo_html = f'<img src="{_logo}" style="height:46px;width:auto;margin-bottom:8px;display:block">' if _logo else ""
    montant_brut = trans.get("montant_brut", 0) or 0
    frais = trans.get("frais", 0) or 0
    montant_net = trans.get("montant_net", 0) or 0
    mode = trans.get("mode_paiement","—")
    motif = trans.get("motif","—")
    qty = trans.get("quantite", 1) or 1
    pu = trans.get("prix_unitaire", 0) or 0
    unite = trans.get("unite","piece")
    unite_label = "g" if unite=="gramme" else ("L" if unite=="litre" else ("paquet(s)" if unite=="paquet" else "pcs"))
    notes = trans.get("notes","") or ""
    import re as _re
    notes_clean = _re.sub(r'\[[^\]]*\]', '', notes)
    notes_clean = _re.sub(r'\s{2,}', ' ', notes_clean).strip()
    ticket_aff = ''
    if '[TICKET code=' in notes:
        ticket_aff = _fmt_ticket(notes.split('[TICKET code=',1)[1].split(']',1)[0])
    ticket_html = f'<span>Code ticket : <strong>{ticket_aff}</strong></span>' if ticket_aff else ''
    client_nom = client.get("nom","—") if client else "—"
    client_tel = client.get("tel","") or ""
    client_email = client.get("email","") or ""

    # Numéro provisoire basé sur l'id transaction
    tid = trans.get("id",0)
    prefix = "FAC" if is_vente else "BON"
    now_str = datetime.now().strftime("%Y%m%d")
    numero = f"{prefix}-{now_str}-{tid:05d}"
    _pmap = _catalogue_photo_map()
    _ph = _pmap.get(motif, "")
    _pimg = f'<img src="{_ph}" style="width:40px;height:40px;object-fit:cover;border-radius:4px;vertical-align:middle;margin-right:8px">' if _ph else ""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>{titre} {numero}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;font-size:12px;color:#111;padding:32px;max-width:600px;margin:auto}}
.header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:28px;padding-bottom:16px;border-bottom:3px solid {couleur}}}
.app-name{{font-size:22px;font-weight:bold;color:{couleur}}}
.app-sub{{font-size:11px;color:#666;margin-top:2px}}
.doc-type{{text-align:right}}
.doc-type h1{{font-size:18px;font-weight:bold;color:{couleur}}}
.doc-type .numero{{font-size:13px;font-weight:600;color:#333;margin-top:4px;font-family:monospace}}
.doc-type .date{{font-size:11px;color:#666;margin-top:2px}}
.section{{margin-bottom:20px}}
.section-title{{font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#888;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee}}
.info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.info-box{{background:#f9f9f9;border:1px solid #eee;border-radius:6px;padding:12px}}
.info-box strong{{display:block;font-size:13px;margin-bottom:4px;color:#333}}
.info-box span{{font-size:12px;color:#555}}
table{{width:100%;border-collapse:collapse;margin-bottom:16px}}
thead tr{{background:{couleur};color:white}}
th{{padding:8px 10px;text-align:left;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:8px 10px;border-bottom:1px solid #f0f0f0;font-size:12px}}
tr:nth-child(even) td{{background:#fafafa}}
.total-section{{background:#f5f5f5;border:1px solid #ddd;border-radius:6px;padding:16px;margin-top:8px}}
.total-row{{display:flex;justify-content:space-between;padding:4px 0;font-size:13px}}
.total-row.main{{font-size:16px;font-weight:bold;color:{couleur};border-top:2px solid {couleur};margin-top:8px;padding-top:8px}}
.badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;background:{couleur}22;color:{couleur};border:1px solid {couleur}44}}
.notes-box{{background:#fffbeb;border:1px solid #fbbf24;border-radius:6px;padding:10px;font-size:12px;color:#92400e}}
.footer{{margin-top:32px;padding-top:16px;border-top:1px solid #eee;text-align:center;font-size:10px;color:#999}}
</style>
</head>
<body>

<div class="header">
  <div>
    {_logo_html}{_logo_html}{_logo_html}<div class="app-name">Gestion Perso</div>
    <div class="app-sub">Gestion de dettes &amp; créances</div>
  </div>
  <div class="doc-type">
    <h1>{titre}</h1>
    <div class="numero">{numero}</div>
    <div class="date">Émis le {date_str}</div>
  </div>
</div>

<div class="section">
  <div class="info-grid">
    <div class="info-box">
      <div class="section-title">Client</div>
      <strong>{client_nom}</strong>
      <span>{client_tel}</span>
      {"<span>" + client_email + "</span>" if client_email else ""}
    </div>
    <div class="info-box">
      <div class="section-title">Transaction</div>
      <strong>#{tid} — {date_fmt}</strong>
      {ticket_html}<span>Type : <span class="badge">{"Vente" if is_vente else ("Dépôt" if (client and client.get("associe")) else "Remboursement")}</span></span>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">Détail</div>
  <table>
    <thead><tr><th>Article</th><th>Qté</th><th>P.U.</th><th>Mode</th><th style="text-align:right">Montant</th></tr></thead>
    <tbody>
      <tr>
        <td>{_pimg}<strong>{motif}</strong></td>
        <td>{float(qty):.1f} {unite_label}</td>
        <td>{float(pu):.2f} €</td>
        <td>{mode}</td>
        <td style="text-align:right;font-weight:600">{float(montant_brut):.2f} €</td>
      </tr>
    </tbody>
  </table>
</div>

<div class="total-section">
  <div class="total-row"><span>Montant brut</span><span>{float(montant_brut):.2f} €</span></div>
  {"<div class='total-row'><span>Frais (" + mode + ")</span><span style='color:#dc2626'>- " + f"{float(frais):.2f}" + " €</span></div>" if frais > 0 else ""}
  <div class="total-row main">
    <span>{("Total payé" if _paye else "Total dû") if is_vente else ("Montant déposé" if (client and client.get("associe")) else "Montant remboursé")}</span>
    <span>{float(montant_net):.2f} €</span>
  </div>
</div>

{"<div class='notes-box' style='margin-top:16px'><strong>Notes :</strong> " + notes_clean + "</div>" if notes_clean else ""}

<div class="footer">
  Document généré automatiquement par Gestion Perso · {date_str}<br>
  Ce document est un justificatif interne — non valable comme facture fiscale officielle
</div>

</body>
</html>"""
    return html, numero

@app.route("/api/factures")
@require_auth
def factures_list():
    cid = request.args.get("client_id")
    limit = int(request.args.get("limit", 100))
    return ok(db.get_factures(int(cid) if cid else None, limit))

@app.route("/api/factures/<int:fid>")
@require_auth
def factures_get(fid):
    f = db.get_facture(fid)
    if not f:
        return err("Facture introuvable", 404)
    return ok(f)

@app.route("/api/factures/<int:fid>/html")
@require_auth
def factures_html(fid):
    f = db.get_facture(fid)
    if not f:
        return err("Facture introuvable", 404)
    response = make_response(f["contenu_html"])
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

@app.route("/api/factures/<int:fid>", methods=["DELETE"])
@require_auth
def factures_delete(fid):
    db.delete_facture(fid)
    return ok({"deleted": fid})

@app.route("/api/factures/generer/<int:tid>", methods=["POST"])
@require_auth
def factures_generer(tid):
    """Génère (ou regénère) la facture pour une transaction existante."""
    with db.get_conn() as conn:
        row = conn.execute(
            """SELECT t.*, c.nom as client_nom, e.description as entree_desc
               FROM transactions t
               LEFT JOIN clients c ON t.client_id=c.id
               LEFT JOIN entrees_materiel e ON t.entree_id=e.id
               WHERE t.id=?""", (tid,)
        ).fetchone()
    if not row:
        return err("Transaction introuvable", 404)
    trans = dict(row)
    client = db.get_client(trans["client_id"])
    type_ = "vente" if trans["type"] == "debit" else "remboursement"
    html_content, numero = _build_facture_html(trans, client, type_)
    db.delete_factures_by_transaction(tid)
    fid, num = db.create_facture(tid, trans["client_id"], type_, html_content, trans["montant_net"])
    return ok({"id": fid, "numero": num}), 201




# -- CATEGORIES ---------------------------------------------------------------
@app.route("/api/categories")
@require_auth
def categories_list():
    return ok(db.get_categories())

@app.route("/api/categories", methods=["POST"])
@require_auth
def categories_create():
    data = request.json or {}
    try:
        cid = db.add_category(data.get("nom",""))
    except ValueError as e:
        return err(str(e))
    return ok({"id": cid}), 201

@app.route("/api/categories/<int:cid>", methods=["DELETE"])
@require_auth
def categories_delete(cid):
    try:
        db.delete_category(cid)
    except ValueError as e:
        return err(str(e), 409)
    return ok({"deleted": cid})


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

@app.route("/api/frais-dus/paye", methods=["POST"])
@require_auth
def frais_dus_paye():
    data = request.json or {}
    ids = data.get("ids", [])
    if not ids:
        return err("Selection vide")
    total = db.payer_frais_dus(ids)
    return ok({"total": total})

@app.route("/api/frais-dus/oublier", methods=["POST"])
@require_auth
def frais_dus_oublier():
    data = request.json or {}
    ids = data.get("ids", [])
    if not ids:
        return err("Selection vide")
    db.set_frais_statut(ids, "oublie")
    return ok({"oublies": len(ids)})


# -- TYPES DE TABAC -----------------------------------------------------------
@app.route("/api/types-tabac")
@require_auth
def types_tabac_list():
    return ok(db.get_types_tabac())

@app.route("/api/types-tabac", methods=["POST"])
@require_auth
def types_tabac_create():
    data=request.json or {}
    try:
        tid=db.add_type_tabac(data.get("nom",""), data.get("prix",0))
    except ValueError as e:
        return err(str(e))
    return ok({"id":tid}), 201

@app.route("/api/types-tabac/<int:tid>", methods=["PUT"])
@require_auth
def types_tabac_update(tid):
    data=request.json or {}
    db.update_type_tabac(tid,
        nom=data.get("nom"),
        prix=data.get("prix"),
        stock=data.get("stock"))
    return ok({"id":tid})

@app.route("/api/types-tabac/<int:tid>", methods=["DELETE"])
@require_auth
def types_tabac_delete(tid):
    db.delete_type_tabac(tid)
    return ok({"deleted":tid})


@app.route("/api/catalogue/<int:iid>/adjust-stock", methods=["POST"])
@require_auth
def catalogue_adjust_stock(iid):
    data = request.json or {}
    delta = float(data.get("delta", 0))
    db.adjust_stock_catalogue(iid, delta)
    return ok(db.get_catalogue_item(iid))


# -- ASSOCIES -----------------------------------------------------------------
@app.route("/api/associes")
@require_auth
def associes_list():
    return ok(db.get_associes())

@app.route("/api/associes", methods=["POST"])
@require_auth
def associes_create():
    data = request.json or {}
    nom = (data.get("nom") or "").strip()
    if not nom:
        return err("Nom requis")
    cid = db.add_client(nom=nom, associe=1)
    return ok({"id": cid}), 201

@app.route("/api/clients/<int:cid>/tabac-paquets")
@require_auth
def client_tabac_paquets(cid):
    with db.get_conn() as conn:
        rows = conn.execute("""SELECT COALESCE(mode_paiement,'Tabac') as nom, type, COALESCE(SUM(quantite),0) as qte FROM transactions WHERE client_id=? AND COALESCE(compte,'euro')='tabac' GROUP BY COALESCE(mode_paiement,'Tabac'), type""", (cid,)).fetchall()
        prix_map = {}
        try:
            for t in conn.execute("SELECT nom, prix FROM types_tabac").fetchall():
                prix_map[t["nom"]] = t["prix"]
        except Exception:
            pass
    detail = {}
    for r in rows:
        nom = r["nom"] or "Tabac"
        d = detail.setdefault(nom, {"nom": nom, "paquets": 0, "prix": prix_map.get(nom, 0)})
        if r["type"] == "debit":
            d["paquets"] += r["qte"]
        else:
            d["paquets"] -= r["qte"]
    total_p = 0; total_v = 0; details = []
    for nom, d in detail.items():
        d["paquets"] = round(d["paquets"], 2)
        d["valeur"] = round(d["paquets"] * (d["prix"] or 0), 2)
        if d["paquets"] != 0:
            total_p += d["paquets"]; total_v += d["valeur"]; details.append(d)
    return ok({"paquets": round(total_p,2), "valeur": round(total_v,2), "details": details})


def _build_facture_groupee_html(transs, client, type_):
    from datetime import datetime
    date_str = datetime.now().strftime("%d/%m/%Y a %H:%M")
    is_vente = type_ == "vente"
    titre = "FACTURE DE VENTE" if is_vente else ("BON DE DÉPÔT" if (client and client.get("associe")) else "BON DE REMBOURSEMENT")
    couleur = "#16a34a" if is_vente else "#c9a84c"
    _logo = db.get_setting("app_logo", "")
    _logo_html = f'<img src="{_logo}" style="height:46px;width:auto;margin-bottom:8px;display:block">' if _logo else ""
    client_nom = client.get("nom","-") if client else "-"
    client_tel = client.get("tel","") or ""
    tid0 = transs[0].get("id",0)
    prefix = "FAC" if is_vente else "BON"
    numero = f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{tid0:05d}"
    date_t = (transs[0].get("date","") or "")[:10].split("-")
    date_fmt = "/".join(reversed(date_t)) if len(date_t)==3 else ""
    rows_html = ""
    _allcodes = []
    for _tt in transs:
        _n = _tt.get("notes","") or ""
        if '[TICKET code=' in _n:
            for _cc in _n.split('[TICKET code=',1)[1].split(']',1)[0].split('|'):
                _cc = _cc.strip()
                if _cc and _cc not in _allcodes:
                    _allcodes.append(_cc)
    tickets_html_g = ('<div class="total-row"><span>Codes ticket</span><span>' + ', '.join(_fmt_ticket(_x) for _x in _allcodes) + '</span></div>') if _allcodes else ''
    _pmap = _catalogue_photo_map()
    total = 0
    for t in transs:
        qty = t.get("quantite",1) or 1
        pu = t.get("prix_unitaire",0) or 0
        mb = t.get("montant_brut",0) or 0
        mode = t.get("mode_paiement","-")
        motif = t.get("motif","-")
        unite = t.get("unite","piece")
        ulabel = "g" if unite=="gramme" else ("L" if unite=="litre" else ("paquet(s)" if unite=="paquet" else "pcs"))
        total += mb
        _ph = _pmap.get(motif, "")
        _pimg = f'<img src="{_ph}" style="width:34px;height:34px;object-fit:cover;border-radius:4px;vertical-align:middle;margin-right:6px">' if _ph else ""
        rows_html += f"<tr><td>{_pimg}<strong>{motif}</strong></td><td>{float(qty):.1f} {ulabel}</td><td>{float(pu):.2f} EUR</td><td>{mode}</td><td style='text-align:right;font-weight:600'>{float(mb):.2f} EUR</td></tr>"
    total = round(total,2)
    _paye = is_vente and bool(transs) and all(("[CAISSE PAYE]" in (t.get("notes") or "")) for t in transs)
    total_label = ("Total payé" if _paye else "Total du") if is_vente else ("Montant déposé" if (client and client.get("associe")) else "Montant rembourse")
    html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>{titre} {numero}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Arial,sans-serif;font-size:12px;color:#111;padding:32px;max-width:600px;margin:auto}}
.header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:28px;padding-bottom:16px;border-bottom:3px solid {couleur}}}
.app-name{{font-size:22px;font-weight:bold;color:{couleur}}}.app-sub{{font-size:11px;color:#666}}
.doc-type{{text-align:right}}.doc-type h1{{font-size:18px;color:{couleur}}}.numero{{font-size:13px;font-family:monospace;color:#333;margin-top:4px}}.date{{font-size:11px;color:#666}}
.section{{margin-bottom:20px}}.section-title{{font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#888;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee}}
.info-box{{background:#f9f9f9;border:1px solid #eee;border-radius:6px;padding:12px}}.info-box strong{{display:block;margin-bottom:4px;color:#333}}
table{{width:100%;border-collapse:collapse;margin-bottom:16px}}thead tr{{background:{couleur};color:white}}th{{padding:8px 10px;text-align:left;font-size:11px}}td{{padding:8px 10px;border-bottom:1px solid #f0f0f0}}
.total-section{{background:#f5f5f5;border:1px solid #ddd;border-radius:6px;padding:16px}}.total-row.main{{font-size:16px;font-weight:bold;color:{couleur};border-top:2px solid {couleur};margin-top:8px;padding-top:8px;display:flex;justify-content:space-between}}
.footer{{margin-top:32px;padding-top:16px;border-top:1px solid #eee;text-align:center;font-size:10px;color:#999}}</style></head><body>
<div class="header"><div>{_logo_html}{_logo_html}{_logo_html}<div class="app-name">Gestion Perso</div><div class="app-sub">Gestion de dettes &amp; creances</div></div>
<div class="doc-type"><h1>{titre}</h1><div class="numero">{numero}</div><div class="date">Emis le {date_str}</div></div></div>
<div class="section"><div class="section-title">Client</div><div class="info-box"><strong>{client_nom}</strong><span>{client_tel}</span></div></div>
<div class="section"><div class="section-title">Detail ({date_fmt})</div><table><thead><tr><th>Article</th><th>Qte</th><th>P.U.</th><th>Mode</th><th style="text-align:right">Montant</th></tr></thead><tbody>{rows_html}</tbody></table></div>
<div class="total-section">{tickets_html_g}<div class="total-row main"><span>{total_label}</span><span>{total:.2f} EUR</span></div></div>
<div class="footer">Gestion Perso - Document genere le {date_str}</div></body></html>"""
    return html, numero

@app.route("/api/factures/groupee", methods=["POST"])
@require_auth
def factures_groupee():
    data = request.json or {}
    cid = data.get("client_id")
    tids = data.get("transaction_ids", [])
    type_ = data.get("type", "vente")
    if not cid or not tids:
        return err("Donnees manquantes")
    client = db.get_client(cid)
    with db.get_conn() as conn:
        qmarks = ",".join("?" for _ in tids)
        rows = conn.execute("SELECT * FROM transactions WHERE id IN (%s)" % qmarks, tuple(tids)).fetchall()
    transs = [dict(r) for r in rows]
    if not transs:
        return err("Transactions introuvables")
    total_net = round(sum((t.get("montant_net") or 0) for t in transs), 2)
    html_content, numero = _build_facture_groupee_html(transs, client, type_)
    fid, num = db.create_facture(transs[0]["id"], cid, type_, html_content, total_net)
    return ok({"facture_id": fid, "numero": num}), 201

@app.route("/api/catalogue/<int:iid>/photo", methods=["POST"])
@require_auth
def catalogue_set_photo(iid):
    data = request.json or {}
    photo = data.get("photo", "")
    db._ensure_catalogue_table()
    with db.get_conn() as conn:
        conn.execute("UPDATE catalogue SET photo=? WHERE id=?", (photo, iid))
        conn.commit()
    return ok(db.get_catalogue_item(iid))

def _catalogue_photo_map():
    m = {}
    try:
        for c in db.get_catalogue():
            if c.get("photo"):
                m[c.get("nom")] = c.get("photo")
    except Exception:
        pass
    return m

_UNLOCK_HANDLER = None
def set_unlock_handler(fn):
    global _UNLOCK_HANDLER
    _UNLOCK_HANDLER = fn

@app.route("/api/unlock", methods=["POST"])
def api_unlock():
    data = request.json or {}
    pwd = str(data.get("password", ""))
    if _UNLOCK_HANDLER is None:
        return jsonify({"ok": True})
    try:
        res = _UNLOCK_HANDLER(pwd) or {}
    except Exception as e:
        res = {"ok": False, "error": str(e)}
    return jsonify(res)

# -- Relais scan telephone -----------------------------------------------------
import threading as _scan_th
_SCAN_QUEUE = []
_SCAN_LOCK = _scan_th.Lock()
PHONE_PORT = 5443

def _lan_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

@app.route("/api/scan-push", methods=["POST"])
def scan_push():
    data = request.json or {}
    code = str(data.get("code", "")).strip()
    if code:
        with _SCAN_LOCK:
            _SCAN_QUEUE.append(code)
            if len(_SCAN_QUEUE) > 50:
                del _SCAN_QUEUE[:-50]
    return jsonify({"ok": True})

@app.route("/api/scan-pull")
def scan_pull():
    with _SCAN_LOCK:
        items = _SCAN_QUEUE[:]
        _SCAN_QUEUE.clear()
    return jsonify({"ok": True, "codes": items})

@app.route("/api/scan-info")
def scan_info():
    return jsonify({"ok": True, "ip": _lan_ip(), "port": PHONE_PORT})

def start_phone_https(certfile, keyfile, host="0.0.0.0", port=None):
    import ssl
    from werkzeug.serving import make_server
    port = port or PHONE_PORT
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile, keyfile)
    srv = make_server(host, port, app, ssl_context=ctx, threaded=True)
    srv.serve_forever()

# -- Generation codes-barres EAN-13 -------------------------------------------
def _ean13(n):
    base = "200" + str(int(n)).zfill(9)
    s = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(base))
    chk = (10 - (s % 10)) % 10
    return base + str(chk)

@app.route("/api/catalogue/generate-barcodes", methods=["POST"])
@require_auth
def catalogue_generate_barcodes():
    items = db.get_catalogue()
    done = []
    for it in items:
        if str(it.get("code_barre") or "").strip():
            continue
        code = _ean13(it["id"])
        db.update_catalogue_item(
            it["id"], it.get("nom",""), it.get("categorie",""), it.get("description",""),
            it.get("prix_vente",0), it.get("prix_achat",0), it.get("unite","piece"),
            it.get("stock_min",0), code_barre=code,
        )
        done.append({"id": it["id"], "nom": it.get("nom",""), "code": code})
    return ok({"count": len(done), "items": done})

# -- Desactivation du 2eme mot de passe (PIN) ---------------------------------
def _is_local_request():
    ra = (request.remote_addr or "")
    host = (request.host or "")
    return (host.startswith("127.0.0.1") or host.startswith("localhost")
            or ra in ("127.0.0.1", "::1", "localhost") or ra.startswith("127."))

def _auth_disabled():
    try:
        return str(db.get_setting("auth_disabled", "0")) == "1"
    except Exception:
        return False

@app.route("/api/auth/can-skip")
def auth_can_skip():
    return jsonify({"ok": True, "data": {"auth_disabled": _auth_disabled()}})

@app.route("/api/auth/auto-login", methods=["POST"])
def auth_auto_login():
    global SESSION_TOKEN
    if not _is_local_request():
        return jsonify({"ok": False, "error": "interdit"}), 403
    if not _auth_disabled():
        return jsonify({"ok": False, "error": "desactive"})
    SESSION_TOKEN = secrets.token_hex(32)
    return jsonify({"ok": True, "data": {"token": SESSION_TOKEN}})

@app.route("/api/auth/set-skip", methods=["POST"])
@require_auth
def auth_set_skip():
    data = request.json or {}
    val = "1" if str(data.get("enabled")) in ("1", "true", "True") else "0"
    db.set_setting("auth_disabled", val)
    return ok({"auth_disabled": val == "1"})

# -- Anti-cache (WebView2 gardait des pages en cache -> MAJ pas appliquees) ----
@app.after_request
def _no_cache(resp):
    try:
        ct = resp.headers.get("Content-Type", "")
        if ("text/html" in ct) or ("javascript" in ct) or ("text/css" in ct):
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
    except Exception:
        pass
    return resp

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Sert l'interface web depuis le dossier web/ (résolu pour PyInstaller)."""
    if path and os.path.exists(os.path.join(_WEB_FOLDER, path)):
        return send_from_directory(_WEB_FOLDER, path)
    return send_from_directory(_WEB_FOLDER, "index.html")

# ── DÉMARRAGE ─────────────────────────────────────────────────────────────────

# -- PRETS TABAC --------------------------------------------------------------
@app.route("/api/clients/<int:cid>/prets")
@require_auth
def client_prets(cid):
    return ok(db.get_prets_client(cid))

@app.route("/api/prets/en-cours")
@require_auth
def prets_en_cours():
    return ok(db.get_prets_en_cours())

@app.route("/api/prets", methods=["POST"])
@require_auth
def prets_create():
    data = request.json or {}
    cid = data.get("client_id")
    if not cid:
        return err("Client requis")
    try:
        pid = db.add_pret(cid, data.get("type_tabac",""), data.get("qte_pretee",0), data.get("qte_rendre",0), data.get("date_echeance"), data.get("notes"), data.get("catalogue_id"))
    except Exception as e:
        return err(str(e))
    return ok({"id": pid}), 201

@app.route("/api/prets/<int:pid>/rendu", methods=["PUT","POST"])
@require_auth
def prets_rendu(pid):
    db.marquer_pret_rendu(pid)
    return ok({"id": pid})

@app.route("/api/prets/<int:pid>", methods=["DELETE"])
@require_auth
def prets_delete(pid):
    db.delete_pret(pid)
    return ok({"deleted": pid})


@app.route("/api/clients/<int:cid>/effacer-transactions", methods=["POST"])
@require_auth
def client_effacer_transactions(cid):
    if not db.get_client(cid):
        return err("Client introuvable", 404)
    n = db.reset_client_data(cid)
    return ok({"deleted": n})


@app.route("/api/update/apply-local", methods=["POST"])
@require_auth
def update_apply_local():
    """Met a jour depuis un fichier .exe fourni (sans telechargement reseau)."""
    if not HAS_UPDATER:
        return err("updater non disponible")
    data = request.json or {}
    b64 = data.get("data") or ""
    if not b64:
        return err("Aucun fichier recu")
    exe = updater.get_current_exe()
    if not exe:
        return err("Mode dev : pas d'exe a remplacer")
    import base64, tempfile, threading, time
    try:
        raw = base64.b64decode(b64)
        if len(raw) < 1000000:
            return err("Fichier trop petit (pas un .exe ?)")
        tmp = tempfile.NamedTemporaryFile(suffix=".exe", dir=exe.parent, delete=False)
        tmp.write(raw); tmp.close()
        updater.apply_update_windows(tmp.name, str(exe))
    except Exception as e:
        return err("Echec : " + str(e))
    def _bye():
        time.sleep(2); os._exit(0)
    threading.Thread(target=_bye, daemon=True).start()
    return ok({"message": "Mise a jour depuis le fichier, redemarrage..."})


@app.route("/api/sim-cards", methods=["GET"])
@require_auth
def sim_cards_list():
    cid = request.args.get("catalogue_id")
    statut = request.args.get("statut")
    cards = db.get_sim_cards(int(cid) if cid else None, statut or None)
    return ok({"cards": cards})

@app.route("/api/sim-cards", methods=["POST"])
@require_auth
def sim_cards_create():
    data = request.json or {}
    cat = data.get("catalogue_id")
    cat = int(cat) if cat else None
    if data.get("items"):
        n = db.add_sim_cards_bulk(cat, data.get("items"))
        return ok({"added": n})
    numero = (data.get("numero") or "").strip()
    if not numero:
        return err("Numero requis")
    sid = db.add_sim_card(cat, numero, data.get("last4", ""))
    return ok({"id": sid})

@app.route("/api/sim-cards/<int:sid>", methods=["DELETE"])
@require_auth
def sim_cards_delete(sid):
    db.delete_sim_card(sid)
    return ok()

@app.route("/api/sim-cards/<int:sid>/sold", methods=["POST"])
@require_auth
def sim_cards_sold(sid):
    data = request.json or {}
    row = db.mark_sim_sold(sid, data.get("transaction_id"), data.get("client_id"), data.get("date"))
    if not row:
        return err("Puce introuvable")
    return ok(row)


@app.route("/api/rentabilite")
@require_auth
def rentabilite_list():
    return ok(db.get_rentabilite())


@app.route("/api/transactions/<int:tid>/photo-ticket", methods=["POST"])
@require_auth
def transaction_set_photo(tid):
    data = request.json or {}
    db.set_transaction_photo(tid, data.get("photo", ""))
    return ok({"id": tid})


@app.route("/api/ocr-ticket", methods=["POST"])
@require_auth
def ocr_ticket_route():
    data = request.json or {}
    photo = data.get("photo", "")
    if not photo:
        return ok({"ok": False, "error": "Photo manquante"})
    try:
        import ocr
        res = ocr.lire_ticket(photo, hint=data.get("mode", ""))
    except Exception as e:
        res = {"ok": False, "error": str(e)}
    return ok(res)


@app.route("/api/logo")
def app_logo_public():
    return ok({"logo": db.get_setting("app_logo", "")})


def start(host="127.0.0.1", port=5000, debug=False):
    db.init_db()
    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    start(debug=True)

@app.route("/api/auth/pin-length")
def auth_pin_length():
    """Retourne la longueur et le type d'auth — route publique."""
    try:
        with db.get_conn() as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(auth)").fetchall()}
            row = conn.execute("SELECT * FROM auth WHERE id=1").fetchone()
            length    = int(row["pin_length"]) if row and "pin_length" in cols and row["pin_length"] else 4
            auth_type = row["auth_type"] if row and "auth_type" in cols and row["auth_type"] else "pin"
    except Exception:
        length, auth_type = 4, "pin"
    return jsonify({"ok": True, "data": {"length": length, "auth_type": auth_type}})

@app.route("/api/version")
def get_version():
    """Retourne la version locale depuis latest.json."""
    try:
        import json, pathlib
        # Chercher latest.json à côté de l'exe ou du script
        import sys as _sys
        base = pathlib.Path(_sys.executable).parent if getattr(_sys, "frozen", False) \
               else pathlib.Path(__file__).parent
        f = base / "latest.json"
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            return jsonify({"ok": True, "data": {"version": data.get("version", "dev")}})
    except Exception:
        pass
    return jsonify({"ok": True, "data": {"version": "dev"}})
