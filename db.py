# db.py — Gestion dettes Premium
import sqlite3
import hashlib
import os
from datetime import datetime

DB_FILE = "dettes.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row   # accès par nom de colonne
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Crée toutes les tables si elles n'existent pas, et migre si besoin."""
    with get_conn() as conn:
        c = conn.cursor()

        # Tables principales
        c.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nom   TEXT    NOT NULL,
            email TEXT,
            tel   TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id      INTEGER NOT NULL,
            type           TEXT    NOT NULL CHECK(type IN ('credit','debit')),
            motif          TEXT,
            quantite       INTEGER DEFAULT 1,
            prix_unitaire  REAL    DEFAULT 0.0,
            montant_brut   REAL,
            mode_paiement  TEXT,
            frais          REAL    DEFAULT 0.0,
            montant_net    REAL,
            date           TEXT,
            reference      TEXT,
            notes          TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS paiements (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            montant        REAL,
            date_paiement  TEXT,
            mode_paiement  TEXT,
            note           TEXT,
            FOREIGN KEY(transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_client
            ON transactions(client_id);
        CREATE INDEX IF NOT EXISTS idx_transactions_date
            ON transactions(date);
        CREATE INDEX IF NOT EXISTS idx_transactions_type
            ON transactions(type);
        """)

        # Table rappels
        c.execute("""
        CREATE TABLE IF NOT EXISTS rappels (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id  INTEGER NOT NULL,
            nom        TEXT,
            dette      REAL DEFAULT 0,
            date       TEXT,
            note       TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        )
        """)

        # ── Migration colonne created_at dans clients ─────────────────────────
        client_cols = {row[1] for row in c.execute("PRAGMA table_info(clients)").fetchall()}
        if "created_at" not in client_cols:
            c.execute("ALTER TABLE clients ADD COLUMN created_at TEXT DEFAULT NULL")

        # ── Migration table auth ──────────────────────────────────────────────
        # Vérifie si la table auth existe et quelles colonnes elle a
        cols = {row[1] for row in c.execute("PRAGMA table_info(auth)").fetchall()}

        if not cols:
            # Table auth absente → la créer dans la nouvelle structure
            c.execute("""
                CREATE TABLE auth (
                    id         INTEGER PRIMARY KEY CHECK(id = 1),
                    pin_hash   TEXT,
                    salt       TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
        elif "pin_hash" not in cols:
            # Ancienne structure (pw_hash / kdf_params) → recréer proprement
            c.execute("DROP TABLE auth")
            c.execute("""
                CREATE TABLE auth (
                    id         INTEGER PRIMARY KEY CHECK(id = 1),
                    pin_hash   TEXT,
                    salt       TEXT,
                    pin_length INTEGER DEFAULT 4,
                    auth_type  TEXT DEFAULT 'pin',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
        # Si pin_hash existe déjà → vérifier pin_length
        else:
            auth_cols = {row[1] for row in c.execute("PRAGMA table_info(auth)").fetchall()}
            if "pin_length" not in auth_cols:
                c.execute("ALTER TABLE auth ADD COLUMN pin_length INTEGER DEFAULT 4")
            if "auth_type" not in auth_cols:
                c.execute("ALTER TABLE auth ADD COLUMN auth_type TEXT DEFAULT 'pin'")

        conn.commit()

# ── AUTH ──────────────────────────────────────────────────────────────────────

def _hash_pin(pin: str, salt: str):
    return hashlib.sha256((salt + pin).encode()).hexdigest()

def set_pin(pin: str, auth_type: str = "pin"):
    """Définit ou remplace le PIN/mot de passe (hashé + sel aléatoire)."""
    salt = os.urandom(16).hex()
    pin_hash = _hash_pin(pin, salt)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO auth (id, pin_hash, salt, pin_length, auth_type) VALUES (1, ?, ?, ?, ?)",
            (pin_hash, salt, len(pin), auth_type)
        )
        conn.commit()

def check_pin(pin: str):
    """Vérifie le PIN. Retourne True si correct."""
    with get_conn() as conn:
        row = conn.execute("SELECT pin_hash, salt FROM auth WHERE id=1").fetchone()
    if not row:
        return False
    return _hash_pin(pin, row["salt"]) == row["pin_hash"]

def has_pin():
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM auth WHERE id=1").fetchone()
    return row is not None

# ── CLIENTS ───────────────────────────────────────────────────────────────────

def add_client(nom, email=None, tel=None, notes=None):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clients (nom,email,tel,notes) VALUES (?,?,?,?)",
            (nom, email or "", tel or "", notes or "")
        )
        conn.commit()
        return cur.lastrowid

def get_clients():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, tel, notes FROM clients ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]

def get_client(client_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE id=?", (client_id,)
        ).fetchone()
    return dict(row) if row else None

def update_client(client_id: int, nom=None, email=None, tel=None, notes=None):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE clients SET nom=?,email=?,tel=?,notes=? WHERE id=?",
            (nom or row["nom"], email or row["email"],
             tel or row["tel"], notes or row["notes"], client_id)
        )
        conn.commit()
    return True

def delete_client(client_id: int):
    """Supprime un client et toutes ses transactions (CASCADE)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
        conn.commit()

# ── TRANSACTIONS ──────────────────────────────────────────────────────────────

def add_transaction(client_id, type_, motif, quantite, prix_unitaire,
                    mode_paiement, frais, montant_brut, montant_net,
                    reference=None, notes=None):
    date = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO transactions
               (client_id,type,motif,quantite,prix_unitaire,montant_brut,
                mode_paiement,frais,montant_net,date,reference,notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, type_, motif, quantite, prix_unitaire, montant_brut,
             mode_paiement, frais, montant_net, date, reference or "", notes or "")
        )
        conn.commit()
        return cur.lastrowid

def get_transactions(client_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id,date,type,motif,quantite,prix_unitaire,
                      montant_brut,mode_paiement,frais,montant_net,reference,notes
               FROM transactions WHERE client_id=? ORDER BY date DESC""",
            (client_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def get_all_transactions(limit=200):
    """Toutes les transactions avec le nom du client."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT t.*, c.nom as client_nom
               FROM transactions t
               JOIN clients c ON c.id = t.client_id
               ORDER BY t.date DESC LIMIT ?""",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

def delete_transaction(trans_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE id=?", (trans_id,))
        conn.commit()

# ── STATISTIQUES ──────────────────────────────────────────────────────────────

def get_stats_client(client_id: int):
    with get_conn() as conn:
        def q(sql, *a):
            return conn.execute(sql, a).fetchone()[0] or 0

        nb        = q("SELECT COUNT(*) FROM transactions WHERE client_id=?", client_id)
        credit    = q("SELECT COALESCE(SUM(montant_net),0) FROM transactions WHERE client_id=? AND type='credit'", client_id)
        debit     = q("SELECT COALESCE(SUM(montant_net),0) FROM transactions WHERE client_id=? AND type='debit'", client_id)
        frais     = q("SELECT COALESCE(SUM(frais),0) FROM transactions WHERE client_id=? AND type='credit'", client_id)
        nb_credit = q("SELECT COUNT(*) FROM transactions WHERE client_id=? AND type='credit'", client_id)
        nb_debit  = q("SELECT COUNT(*) FROM transactions WHERE client_id=? AND type='debit'", client_id)

    return {
        "nb_transactions": nb,
        "total_credit":    round(credit, 2),   # remboursements reçus
        "total_debit":     round(debit, 2),    # ventes effectuées
        "solde":           round(debit - credit, 2),  # dette nette du client (debit-credit)
        "total_frais":     round(frais, 2),
        "nb_credits":      nb_credit,
        "nb_debits":       nb_debit,
    }

def get_stats_global():
    """Stats agrégées pour le tableau de bord."""
    with get_conn() as conn:
        def q(sql):
            return conn.execute(sql).fetchone()[0] or 0

        total_credit  = q("SELECT COALESCE(SUM(montant_net),0) FROM transactions WHERE type='credit'")
        total_debit   = q("SELECT COALESCE(SUM(montant_net),0) FROM transactions WHERE type='debit'")
        total_frais   = q("SELECT COALESCE(SUM(frais),0) FROM transactions WHERE type='credit'")
        nb_clients    = q("SELECT COUNT(*) FROM clients")
        nb_trans      = q("SELECT COUNT(*) FROM transactions")

        # Clients avec solde négatif (dettes)
        rows_soldes = conn.execute("""
            SELECT client_id,
                   SUM(CASE WHEN type='credit' THEN montant_net ELSE 0 END) -
                   SUM(CASE WHEN type='debit'  THEN montant_net ELSE 0 END) AS solde
            FROM transactions GROUP BY client_id
        """).fetchall()
        nb_debiteurs = sum(1 for r in rows_soldes if (r["solde"] or 0) < 0)  # debit < credit → tu leur dois

        # Transactions par mois (6 derniers mois)
        mois_rows = conn.execute("""
            SELECT strftime('%Y-%m', date) as mois,
                   SUM(CASE WHEN type='credit' THEN montant_net ELSE 0 END) as credit,
                   SUM(CASE WHEN type='debit'  THEN montant_net ELSE 0 END) as debit
            FROM transactions
            WHERE date >= date('now', '-6 months')
            GROUP BY mois ORDER BY mois
        """).fetchall()

        # Répartition par mode de paiement
        mode_rows = conn.execute("""
            SELECT mode_paiement, SUM(montant_net) as total
            FROM transactions GROUP BY mode_paiement
        """).fetchall()

    return {
        "total_credit":  round(total_credit, 2),
        "total_debit":   round(total_debit, 2),
        "solde_net":     round(total_debit - total_credit, 2),  # dette nette globale
        "total_frais":   round(total_frais, 2),
        "nb_clients":    nb_clients,
        "nb_transactions": nb_trans,
        "nb_debiteurs":  nb_debiteurs,
        "par_mois": [
            {"mois": r["mois"], "credit": round(r["credit"], 2), "debit": round(r["debit"], 2)}
            for r in mois_rows
        ],
        "par_mode": [
            {"mode": r["mode_paiement"], "total": round(r["total"], 2)}
            for r in mode_rows
        ],
    }

def update_transaction(trans_id, data):
    """Met à jour une transaction existante et recalcule les montants."""
    FEES = {"Liquide": 0, "Virement": 0, "PCS": 0.07, "Paysafecard": 0.05, "WesternUnion": 0}
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM transactions WHERE id=?", (trans_id,)).fetchone()
        if not row:
            return None
        type_      = data.get("type",          row["type"])
        motif      = data.get("motif",         row["motif"])
        quantite   = int(data.get("quantite",  row["quantite"]))
        prix_u     = float(data.get("prix_unitaire", row["prix_unitaire"]))
        mode       = data.get("mode_paiement", row["mode_paiement"])
        notes      = data.get("notes",         row["notes"] or "")
        date       = data.get("date",          row["date"])
        brut       = round(quantite * prix_u, 2)
        frais      = round(brut * FEES.get(mode, 0), 2) if type_ == "credit" else 0.0
        net        = round(brut - frais, 2)
        conn.execute("""
            UPDATE transactions SET
              type=?, motif=?, quantite=?, prix_unitaire=?,
              montant_brut=?, mode_paiement=?, frais=?, montant_net=?, notes=?, date=?
            WHERE id=?""",
            (type_, motif, quantite, prix_u, brut, mode, frais, net, notes, date, trans_id)
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM transactions WHERE id=?", (trans_id,)).fetchone()
    return dict(updated)

# ── RAPPELS ──────────────────────────────────────────────────────────────────

def add_rappel(client_id, nom, dette, date, note=""):
    with get_conn() as conn:
        # Un seul rappel actif par client — remplacer si existe
        conn.execute("DELETE FROM rappels WHERE client_id=?", (client_id,))
        cur = conn.execute(
            "INSERT INTO rappels (client_id,nom,dette,date,note) VALUES (?,?,?,?,?)",
            (client_id, nom, dette, date, note or "")
        )
        conn.commit()
        return cur.lastrowid

def get_rappels():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM rappels ORDER BY date DESC"
        ).fetchall()
    return [dict(r) for r in rows]

def get_rappel(client_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM rappels WHERE client_id=?", (client_id,)
        ).fetchone()
    return dict(row) if row else None

def delete_rappel(rappel_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM rappels WHERE id=?", (rappel_id,))
        conn.commit()

def delete_rappel_by_client(client_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM rappels WHERE client_id=?", (client_id,))
        conn.commit()