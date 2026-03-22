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
    db.set_pin(new_pin)
    return ok({"message": "PIN mis à jour"})

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
    if not db.update_client(cid, **{k: data.get(k) for k in ("nom","email","tel","notes")}):
        return err("Client introuvable", 404)
    return ok(db.get_client(cid))

@app.route("/api/clients/<int:cid>", methods=["DELETE"])
@require_auth
def clients_delete(cid):
    if not db.get_client(cid):
        return err("Client introuvable", 404)
    db.delete_client(cid)
    return ok({"deleted": cid})

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

    qty   = max(int(data["quantite"]), 1)
    pu    = float(data["prix_unitaire"])
    mode  = data["mode_paiement"]
    brut  = round(qty * pu, 2)
    frais = round(brut * FEES.get(mode, 0), 2)
    net   = round(brut - frais, 2)

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
    )
    # Retourner la transaction créée avec les montants calculés
    trans = db.get_transactions(data["client_id"])
    created = next((t for t in trans if t["id"] == tid), None)
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
        return ok({"available": False, "reason": "updater non disponible"})
    global PENDING_UPDATE
    remote = updater.fetch_remote_info()
    if not remote:
        return ok({"available": False, "reason": "Impossible de joindre GitHub"})
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
    import threading
    def _do():
        updater.check_and_update(
            on_update_available = lambda r: True,
            on_done = lambda ok_, msg: print(f"[Updater] {msg}"),
        )
    threading.Thread(target=_do, daemon=True).start()
    return ok({"message": f"Téléchargement de {PENDING_UPDATE['version']} en cours..."})

# ── SERVE FRONTEND ────────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Sert l'interface web depuis le dossier web/ (résolu pour PyInstaller)."""
    if path and os.path.exists(os.path.join(_WEB_FOLDER, path)):
        return send_from_directory(_WEB_FOLDER, path)
    return send_from_directory(_WEB_FOLDER, "index.html")

# ── DÉMARRAGE ─────────────────────────────────────────────────────────────────

def start(host="127.0.0.1", port=5000, debug=False):
    db.init_db()
    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    start(debug=True)

@app.route("/api/auth/pin-length")
def auth_pin_length():
    """Retourne la longueur du PIN — route publique, pas de token requis."""
    try:
        with db.get_conn() as conn:
            # Vérifier si la colonne pin_length existe
            cols = {r[1] for r in conn.execute("PRAGMA table_info(auth)").fetchall()}
            if "pin_length" in cols:
                row = conn.execute("SELECT pin_length FROM auth WHERE id=1").fetchone()
                length = int(row["pin_length"]) if row and row["pin_length"] else 4
            else:
                length = 4
    except Exception:
        length = 4
    return jsonify({"ok": True, "data": {"length": length}})