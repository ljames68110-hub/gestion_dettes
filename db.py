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

CAISSE_PAYE_TAG = "[CAISSE PAYE]"  # marqueur d'une vente comptant (deja payee)

def excl_paye_clause(col="notes"):
    """Fragment SQL vrai quand la transaction n'est PAS un comptant deja paye."""
    return "(" + col + " IS NULL OR " + col + " NOT LIKE '%" + CAISSE_PAYE_TAG + "%')"

def is_paye_clause(col="notes"):
    """Fragment SQL vrai quand la transaction est un comptant deja paye."""
    return col + " LIKE '%" + CAISSE_PAYE_TAG + "%'"


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

        # ── Migration colonnes transactions ────────────────────────────────────
        trans_cols = {row[1] for row in c.execute("PRAGMA table_info(transactions)").fetchall()}
        if "linked_debit_id" not in trans_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN linked_debit_id INTEGER DEFAULT NULL")
        if "entree_id" not in trans_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN entree_id INTEGER DEFAULT NULL")
        if "frais_deduits" not in trans_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN frais_deduits INTEGER DEFAULT 1")
        if "unite" not in trans_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN unite TEXT DEFAULT 'piece'")
        if "compte" not in trans_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN compte TEXT DEFAULT 'euro'")
        if "photo_ticket" not in trans_cols:
            c.execute("ALTER TABLE transactions ADD COLUMN photo_ticket TEXT DEFAULT ''")
            # Migrer les transactions existantes selon mode_paiement
            c.execute("UPDATE transactions SET compte='cantine' WHERE mode_paiement='Cantine'")
            c.execute("UPDATE transactions SET compte='tabac' WHERE mode_paiement IN ('Tabac','Blonde','PotTabac')")

        c.execute("""
        CREATE TABLE IF NOT EXISTS entrees_materiel (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT DEFAULT (date('now')),
            description TEXT NOT NULL,
            quantite    REAL DEFAULT 1,
            prix_achat  REAL DEFAULT 0,
            notes       TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        )
        """)
        # ── Migration colonnes entrees_materiel ───────────────────────────────
        ent_cols = {row[1] for row in c.execute("PRAGMA table_info(entrees_materiel)").fetchall()}
        if "unite" not in ent_cols:
            c.execute("ALTER TABLE entrees_materiel ADD COLUMN unite TEXT DEFAULT 'piece'")
        if "stock_restant" not in ent_cols:
            c.execute("ALTER TABLE entrees_materiel ADD COLUMN stock_restant REAL DEFAULT NULL")

        # ── Table entrées matériel ─────────────────────────────────────────────

        # ── Migration complète table auth ──────────────────────────────────────
        auth_cols = {row[1] for row in c.execute("PRAGMA table_info(auth)").fetchall()}
        if not auth_cols:
            c.execute("""CREATE TABLE auth (
                id INTEGER PRIMARY KEY CHECK(id=1),
                pin_hash TEXT, salt TEXT,
                pin_length INTEGER DEFAULT 4,
                auth_type TEXT DEFAULT 'pin',
                created_at TEXT DEFAULT (datetime('now'))
            )""")
        else:
            if "pin_hash" not in auth_cols:
                c.execute("ALTER TABLE auth ADD COLUMN pin_hash TEXT")
            if "salt" not in auth_cols:
                c.execute("ALTER TABLE auth ADD COLUMN salt TEXT")
            if "pin_length" not in auth_cols:
                c.execute("ALTER TABLE auth ADD COLUMN pin_length INTEGER DEFAULT 4")
            if "auth_type" not in auth_cols:
                c.execute("ALTER TABLE auth ADD COLUMN auth_type TEXT DEFAULT 'pin'")

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

def add_client(nom, email=None, tel=None, notes=None, associe=0, photo=None):
    _ensure_associe_column()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clients (nom,email,tel,notes,associe,photo) VALUES (?,?,?,?,?,?)",
            (nom, email or "", tel or "", notes or "", int(associe or 0), photo or "")
        )
        conn.commit()
        return cur.lastrowid

def get_clients():
    _ensure_associe_column()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, tel, notes, COALESCE(associe,0) as associe, COALESCE(photo,'') as photo FROM clients ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]

def get_client(client_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE id=?", (client_id,)
        ).fetchone()
    return dict(row) if row else None

def update_client(client_id: int, nom=None, email=None, tel=None, notes=None, photo=None):
    _ensure_associe_column()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE clients SET nom=?,email=?,tel=?,notes=?,photo=? WHERE id=?",
            (nom or row["nom"], email or row["email"],
             tel or row["tel"], notes or row["notes"],
             (photo if photo is not None else row["photo"]), client_id)
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
                    reference=None, notes=None, date=None):
    if not date:
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
            """SELECT t.id,t.date,t.type,t.motif,t.quantite,t.prix_unitaire,
                      t.montant_brut,t.mode_paiement,t.frais,t.montant_net,
                      t.reference,t.notes,t.entree_id,t.linked_debit_id,
                      COALESCE(t.unite,'piece') as unite,
                      COALESCE(t.compte,'euro') as compte, COALESCE(t.photo_ticket,'') as photo_ticket,
                      e.description as entree_description,
                      e.date as entree_date
               FROM transactions t
               LEFT JOIN entrees_materiel e ON t.entree_id = e.id
               WHERE t.client_id=? ORDER BY t.date DESC""",
            (client_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def get_all_transactions(limit=200):
    """Toutes les transactions avec le nom du client."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT t.*, c.nom as client_nom,
                      COALESCE(t.unite,'piece') as unite,
                      COALESCE(t.compte,'euro') as compte, COALESCE(t.photo_ticket,'') as photo_ticket,
                      e.description as entree_description,
                      e.date as entree_date
               FROM transactions t
               LEFT JOIN clients c ON t.client_id = c.id
               LEFT JOIN entrees_materiel e ON t.entree_id = e.id
               ORDER BY t.date DESC LIMIT ?""",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ===== CORBEILLE (soft-delete : archivage avant suppression) =====
def _txn_columns(conn):
    return [r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()]

def _ensure_corbeille_table(conn):
    cols = set(r[1] for r in conn.execute("PRAGMA table_info(transactions_corbeille)").fetchall())
    if not cols:
        conn.execute("CREATE TABLE transactions_corbeille AS SELECT * FROM transactions WHERE 0")
        conn.execute("ALTER TABLE transactions_corbeille ADD COLUMN deleted_at TEXT")
        conn.execute("ALTER TABLE transactions_corbeille ADD COLUMN client_nom TEXT")
    else:
        if "deleted_at" not in cols:
            conn.execute("ALTER TABLE transactions_corbeille ADD COLUMN deleted_at TEXT")
        if "client_nom" not in cols:
            conn.execute("ALTER TABLE transactions_corbeille ADD COLUMN client_nom TEXT")

def _archive_txn(conn, where, params):
    """Copie vers la corbeille les transactions correspondant a <where> (avant DELETE)."""
    _ensure_corbeille_table(conn)
    cols = _txn_columns(conn)
    collist = ",".join(cols)
    sel = ",".join("t." + c for c in cols)
    now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
    conn.execute(
        "INSERT INTO transactions_corbeille (" + collist + ",deleted_at,client_nom) "
        "SELECT " + sel + ",?,c.nom FROM transactions t "
        "LEFT JOIN clients c ON c.id=t.client_id WHERE " + where,
        (now,) + tuple(params)
    )

def get_corbeille(limit=500):
    with get_conn() as conn:
        _ensure_corbeille_table(conn)
        rows = conn.execute(
            "SELECT * FROM transactions_corbeille ORDER BY deleted_at DESC, id DESC LIMIT ?",
            (int(limit),)
        ).fetchall()
    return [dict(r) for r in rows]

def _reapply_effects_on_restore(conn, row):
    """ Re-applique l'inverse des effets de delete_transaction (stock + SIM)."""
    import re as _re
    notes = row["notes"] or ""
    m = _re.search(r"\[STK ([^\]]*)\]", notes)
    if m:
        for part in m.group(1).split(";"):
            part = part.strip()
            if ":" in part:
                cid_s, delta_s = part.split(":", 1)
                try:
                    conn.execute("UPDATE catalogue SET stock=COALESCE(stock,0)+? WHERE id=?",
                                 (float(delta_s), int(cid_s)))
                except Exception:
                    pass
    elif row["type"] == "debit" and "[CAISSE" in notes:
        cat = conn.execute("SELECT id FROM catalogue WHERE nom=? AND actif=1", (row["motif"],)).fetchone()
        if cat:
            is_sim = conn.execute("SELECT COUNT(*) FROM sim_cards WHERE catalogue_id=?", (cat["id"],)).fetchone()[0] > 0
            if not is_sim:
                conn.execute("UPDATE catalogue SET stock=COALESCE(stock,0)-? WHERE id=?",
                             (row["quantite"] or 0, cat["id"]))
    try:
        for mm in _re.finditer(r"\[SIM puce=([^\|\]]*)\|last4=([^\]]*)\]", notes):
            puce = (mm.group(1) or "").strip()
            sc = conn.execute("SELECT id,catalogue_id FROM sim_cards WHERE puce=? AND statut='stock'", (puce,)).fetchone()
            if sc:
                conn.execute("UPDATE sim_cards SET statut='vendu', transaction_id=?, client_id=? WHERE id=?",
                             (row["id"], row["client_id"], sc["id"]))
                try: _sync_sim_stock(conn, sc["catalogue_id"])
                except Exception: pass
    except Exception:
        pass

def restore_corbeille_item(tid):
    with get_conn() as conn:
        _ensure_corbeille_table(conn)
        row = conn.execute("SELECT * FROM transactions_corbeille WHERE id=?", (tid,)).fetchone()
        if not row:
            return False
        cols = _txn_columns(conn)
        collist = ",".join(cols)
        conn.execute(
            "INSERT INTO transactions (" + collist + ") SELECT " + collist +
            " FROM transactions_corbeille WHERE id=?", (tid,)
        )
        _reapply_effects_on_restore(conn, row)
        conn.execute("DELETE FROM transactions_corbeille WHERE id=?", (tid,))
        conn.commit()
    return True

def purge_corbeille_item(tid):
    with get_conn() as conn:
        _ensure_corbeille_table(conn)
        conn.execute("DELETE FROM transactions_corbeille WHERE id=?", (tid,))
        conn.commit()
    return True

def purge_corbeille_all():
    with get_conn() as conn:
        _ensure_corbeille_table(conn)
        n = conn.execute("SELECT COUNT(*) FROM transactions_corbeille").fetchone()[0]
        conn.execute("DELETE FROM transactions_corbeille")
        conn.commit()
    return n

def delete_transaction(trans_id: int):
    import re as _re
    _ensure_sim_table()
    with get_conn() as conn:
        row = conn.execute("SELECT motif,quantite,type,COALESCE(notes,'') AS notes FROM transactions WHERE id=?", (trans_id,)).fetchone()
        notes = row["notes"] if row else ""
        m = _re.search(r"\[STK ([^\]]*)\]", notes) if row else None
        if m:
            for part in m.group(1).split(";"):
                part = part.strip()
                if ":" in part:
                    cid_s, delta_s = part.split(":", 1)
                    try:
                        cat_id = int(cid_s); delta = float(delta_s)
                        conn.execute("UPDATE catalogue SET stock=COALESCE(stock,0)+? WHERE id=?", (-delta, cat_id))
                    except Exception:
                        pass
        elif row and row["type"] == "debit" and "[CAISSE" in notes:
            cat = conn.execute("SELECT id FROM catalogue WHERE nom=? AND actif=1", (row["motif"],)).fetchone()
            if cat:
                is_sim = conn.execute("SELECT COUNT(*) FROM sim_cards WHERE catalogue_id=?", (cat["id"],)).fetchone()[0] > 0
                if not is_sim:
                    conn.execute("UPDATE catalogue SET stock=COALESCE(stock,0)+? WHERE id=?", (row["quantite"] or 0, cat["id"]))
        for s in conn.execute("SELECT id,catalogue_id FROM sim_cards WHERE transaction_id=? AND statut='vendu'", (trans_id,)).fetchall():
            conn.execute("UPDATE sim_cards SET statut='stock', transaction_id=NULL, client_id=NULL, date_vente=NULL WHERE id=?", (s["id"],))
            _sync_sim_stock(conn, s["catalogue_id"])
        _archive_txn(conn, "t.id=?", (trans_id,))
        conn.execute("DELETE FROM transactions WHERE id=?", (trans_id,))
        conn.commit()
def get_stats_client(client_id: int):
    with get_conn() as conn:
        def q(sql, *a):
            return conn.execute(sql, a).fetchone()[0] or 0

        nb        = q("SELECT COUNT(*) FROM transactions WHERE client_id=?", client_id)
        credit    = q("SELECT COALESCE(SUM(montant_brut),0) FROM transactions WHERE client_id=? AND type='credit'", client_id)
        debit     = q("SELECT COALESCE(SUM(montant_brut),0) FROM transactions WHERE client_id=? AND type='debit'", client_id)
        frais     = q("SELECT COALESCE(SUM(frais),0) FROM transactions WHERE client_id=? AND type='credit'", client_id)
        nb_credit = q("SELECT COUNT(*) FROM transactions WHERE client_id=? AND type='credit'", client_id)
        nb_debit  = q("SELECT COUNT(*) FROM transactions WHERE client_id=? AND type='debit'", client_id)

        # Solde base BRUT : les frais ne sont PAS comptes dans le solde.
        # On rajoute uniquement les frais encore EN ATTENTE (ni payes ni factures).
        # Un frais paye/facture reste sur la transaction (trace) mais ne compte plus
        # dans le solde -> evite le double comptage avec le debit de frais reportes.
        _assoc = q("SELECT COALESCE(associe,0) FROM clients WHERE id=?", client_id)
        _excl_paye = "" if _assoc else (" AND " + excl_paye_clause())
        debit_brut  = q("SELECT COALESCE(SUM(montant_brut),0) FROM transactions WHERE client_id=? AND type='debit'" + _excl_paye, client_id)
        credit_brut = q("SELECT COALESCE(SUM(montant_brut),0) FROM transactions WHERE client_id=? AND type='credit'", client_id)
        try:
            frais_pending = q("SELECT COALESCE(SUM(frais),0) FROM transactions WHERE client_id=? AND type='credit' AND frais>0 AND id NOT IN (SELECT transaction_id FROM frais_dus WHERE statut IN ('paye','facture') AND transaction_id IS NOT NULL)", client_id)
        except Exception:
            frais_pending = frais
        solde_val = round(debit_brut - credit_brut + frais_pending, 2)

    return {
        "nb_transactions": nb,
        "total_credit":    round(credit, 2),
        "total_debit":     round(debit, 2),
        "solde":           solde_val,
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
        rows_soldes = conn.execute(f"""
            SELECT t.client_id,
                   SUM(CASE WHEN t.type='credit' THEN t.montant_net ELSE 0 END) -
                   SUM(CASE WHEN t.type='debit'
                            AND NOT (COALESCE(c.associe,0)=0 AND {is_paye_clause('t.notes')})
                            THEN t.montant_net ELSE 0 END) AS solde
            FROM transactions t LEFT JOIN clients c ON c.id=t.client_id
            GROUP BY t.client_id
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
        compte     = data.get("compte",        row["compte"] if "compte" in row.keys() else "euro")
        unite      = data.get("unite",         row["unite"] if "unite" in row.keys() else "piece")
        brut       = round(quantite * prix_u, 2)
        frais_deduits = int(data.get("frais_deduits", row["frais_deduits"] if "frais_deduits" in row.keys() else 1))
        if type_ == "credit" and frais_deduits:
            frais = round(brut * FEES.get(mode, 0), 2)
        else:
            frais = 0.0
        net        = round(brut - frais, 2)
        conn.execute("""
            UPDATE transactions SET
              type=?, motif=?, quantite=?, prix_unitaire=?,
              montant_brut=?, mode_paiement=?, frais=?, montant_net=?, notes=?, date=?, frais_deduits=?,
              compte=?, unite=?
            WHERE id=?""",
            (type_, motif, quantite, prix_u, brut, mode, frais, net, notes, date, frais_deduits, compte, unite, trans_id)
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM transactions WHERE id=?", (trans_id,)).fetchone()
    return dict(updated)

# ── RAPPELS ──────────────────────────────────────────────────────────────────

def _ensure_rappel_actif():
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

# ── ENTRÉES MATÉRIEL ──────────────────────────────────────────────────────────

def get_entrees(limit=100):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT e.*,
                   COALESCE(e.unite, 'piece') as unite,
                   (SELECT COALESCE(SUM(t.quantite),0) FROM transactions t
                    WHERE t.entree_id=e.id AND t.type='debit') as total_vendu,
                   MAX(0, e.quantite - (SELECT COALESCE(SUM(t.quantite),0) FROM transactions t
                    WHERE t.entree_id=e.id AND t.type='debit')) as stock_restant
            FROM entrees_materiel e
            ORDER BY e.date DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]

def add_entree(description, quantite, prix_achat, date=None, notes="", unite="piece"):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO entrees_materiel (description,quantite,prix_achat,date,notes,unite,stock_restant) VALUES (?,?,?,?,?,?,?)",
            (description, quantite, prix_achat, date or "", notes or "", unite, quantite)
        )
        conn.commit()
        return cur.lastrowid

def update_stock(entree_id, quantite_vendue):
    """Déduit la quantité vendue du stock de l'entrée."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE entrees_materiel
            SET stock_restant = MAX(0, COALESCE(stock_restant, quantite) - ?)
            WHERE id = ?
        """, (quantite_vendue, entree_id))
        conn.commit()

def update_entree(eid, description, quantite, prix_achat, date, notes="", unite="piece"):
    with get_conn() as conn:
        conn.execute(
            "UPDATE entrees_materiel SET description=?,quantite=?,prix_achat=?,date=?,notes=?,unite=? WHERE id=?",
            (description, quantite, prix_achat, date, notes or "", unite, eid)
        )
        conn.commit()

def delete_entree(eid):
    with get_conn() as conn:
        conn.execute("DELETE FROM entrees_materiel WHERE id=?", (eid,))
        conn.commit()

# ── MOTIFS ───────────────────────────────────────────────────────────────────

def ensure_tarifs_table():
    """Crée la table tarifs si elle n existe pas."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS tarifs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article TEXT NOT NULL,
        unite TEXT DEFAULT 'piece',
        prix_unitaire REAL NOT NULL,
        actif INTEGER DEFAULT 1
    )""")
    count = conn.execute("SELECT COUNT(*) FROM tarifs").fetchone()[0]
    if count == 0:
        defaults = [
            ("Blonde", "piece", 20.0),
            ("Tabac", "piece", 25.0),
            ("PotTabac", "piece", 30.0),
            ("Cantine", "piece", 1.0),
        ]
        for a, u, p in defaults:
            conn.execute("INSERT INTO tarifs (article,unite,prix_unitaire) VALUES (?,?,?)", (a,u,p))
    conn.commit()
    conn.close()

def get_tarifs():
    ensure_tarifs_table()
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT * FROM tarifs WHERE actif=1").fetchall()
    result = [{"id":r[0],"article":r[1],"unite":r[2],"prix_unitaire":r[3]} for r in rows]
    conn.close()
    return result

def save_tarif(article, prix):
    ensure_tarifs_table()
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE tarifs SET prix_unitaire=? WHERE article=?", (prix, article))
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    """Récupère un paramètre de configuration."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default
    except: return default

def set_setting(key, value):
    """Enregistre un paramètre de configuration."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings():
    """Retourne tous les paramètres."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    defaults = {
        "devise": "EUR",
        "devise_symbole": "€",
        "frais_pcs": "0.07",
        "frais_paysafecard": "0.05",
        "frais_westernunion": "0.05",
        "alerte_retard_jours": "7",
        "alerte_retard_montant": "0",
        "backup_auto": "1",
    }
    result = dict(defaults)
    result.update({r[0]: r[1] for r in rows})
    return result

def _ensure_motifs_table():
    """Crée la table motifs si elle n existe pas."""
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS motifs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            actif INTEGER DEFAULT 1
        )""")
        count = conn.execute("SELECT COUNT(*) FROM motifs").fetchone()[0]
        if count == 0:
            for m in ["Achat","Bedo","Blonde","Cigarette","Pot","Recharge","Tabac","Autre"]:
                try:
                    conn.execute("INSERT INTO motifs (nom) VALUES (?)", (m,))
                except: pass
        conn.commit()

def get_motifs():
    _ensure_motifs_table()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM motifs WHERE actif=1 ORDER BY nom").fetchall()
    return [dict(r) for r in rows]

def add_motif(nom):
    _ensure_motifs_table()
    with get_conn() as conn:
        exists = conn.execute("SELECT COUNT(*) FROM motifs WHERE nom=?", (nom.strip(),)).fetchone()[0]
        if exists > 0:
            raise ValueError("Article deja existant")
        conn.execute("INSERT INTO motifs (nom) VALUES (?)", (nom.strip(),))
        conn.commit()

def delete_motif(mid):
    with get_conn() as conn:
        conn.execute("DELETE FROM motifs WHERE id=?", (mid,))
        conn.commit()

def update_motif(mid, nom):
    with get_conn() as conn:
        conn.execute("UPDATE motifs SET nom=? WHERE id=?", (nom.strip(), mid))
        conn.commit()

# ── CATALOGUE ─────────────────────────────────────────────────────────────────

def _ensure_catalogue_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS catalogue (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nom           TEXT NOT NULL,
            categorie     TEXT DEFAULT 'Général',
            description   TEXT DEFAULT '',
            prix_vente    REAL DEFAULT 0.0,
            prix_achat    REAL DEFAULT 0.0,
            unite         TEXT DEFAULT 'piece',
            stock_min     REAL DEFAULT 0,
            actif         INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now'))
        )""")
        conn.commit()
    # migration : colonne stock (quantite disponible)
    with get_conn() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(catalogue)").fetchall()}
        if "stock" not in cols:
            conn.execute("ALTER TABLE catalogue ADD COLUMN stock REAL DEFAULT 0")
            conn.commit()
        if "photo" not in cols:
            conn.execute("ALTER TABLE catalogue ADD COLUMN photo TEXT DEFAULT ''")
            conn.commit()
        if "grammes_piece" not in cols:
            conn.execute("ALTER TABLE catalogue ADD COLUMN grammes_piece REAL DEFAULT 0")
            conn.commit()
        if "code_barre" not in cols:
            conn.execute("ALTER TABLE catalogue ADD COLUMN code_barre TEXT DEFAULT ''")
            conn.commit()
        if "date_entree" not in cols:
            conn.execute("ALTER TABLE catalogue ADD COLUMN date_entree TEXT DEFAULT ''")
            conn.commit()

def get_catalogue():
    _ensure_catalogue_table()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM catalogue WHERE actif=1 ORDER BY categorie, nom"
        ).fetchall()
    return [dict(r) for r in rows]

def get_catalogue_item(item_id):
    _ensure_catalogue_table()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE id=?", (item_id,)).fetchone()
    return dict(row) if row else None

def add_catalogue_item(nom, categorie, description, prix_vente, prix_achat, unite, stock_min, stock=0, grammes_piece=0, code_barre='', date_entree=''):
    _ensure_catalogue_table()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO catalogue (nom,categorie,description,prix_vente,prix_achat,unite,stock_min,stock,grammes_piece,code_barre,date_entree)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (nom.strip(), categorie, description, prix_vente, prix_achat, unite, stock_min, stock, grammes_piece, code_barre, date_entree)
        )
        conn.commit()
        return cur.lastrowid

def update_catalogue_item(item_id, nom, categorie, description, prix_vente, prix_achat, unite, stock_min, stock=None, grammes_piece=None, code_barre=None, date_entree=None):
    _ensure_catalogue_table()
    with get_conn() as conn:
        conn.execute(
            """UPDATE catalogue SET nom=?,categorie=?,description=?,prix_vente=?,
               prix_achat=?,unite=?,stock_min=?, stock=COALESCE(?,stock), grammes_piece=COALESCE(?,grammes_piece), code_barre=COALESCE(?,code_barre), date_entree=COALESCE(?,date_entree) WHERE id=?""",
            (nom.strip(), categorie, description, prix_vente, prix_achat, unite, stock_min, stock, grammes_piece, code_barre, date_entree, item_id)
        )
        conn.commit()

def delete_catalogue_item(item_id):
    with get_conn() as conn:
        conn.execute("UPDATE catalogue SET actif=0 WHERE id=?", (item_id,))
        conn.commit()

# ── FACTURES ──────────────────────────────────────────────────────────────────

def _ensure_factures_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS factures (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero          TEXT NOT NULL UNIQUE,
            transaction_id  INTEGER,
            client_id       INTEGER,
            type            TEXT DEFAULT 'vente',
            contenu_html    TEXT,
            date_creation   TEXT DEFAULT (datetime('now')),
            montant_net     REAL DEFAULT 0,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE SET NULL
        )""")
        conn.commit()

def get_factures(client_id=None, limit=100):
    _ensure_factures_table()
    with get_conn() as conn:
        if client_id:
            rows = conn.execute(
                """SELECT f.*, c.nom as client_nom FROM factures f
                   LEFT JOIN clients c ON f.client_id=c.id
                   WHERE f.client_id=? ORDER BY f.date_creation DESC LIMIT ?""",
                (client_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT f.*, c.nom as client_nom FROM factures f
                   LEFT JOIN clients c ON f.client_id=c.id
                   ORDER BY f.date_creation DESC LIMIT ?""",
                (limit,)
            ).fetchall()
    return [dict(r) for r in rows]

def get_facture(facture_id):
    _ensure_factures_table()
    with get_conn() as conn:
        row = conn.execute(
            """SELECT f.*, c.nom as client_nom FROM factures f
               LEFT JOIN clients c ON f.client_id=c.id
               WHERE f.id=?""", (facture_id,)
        ).fetchone()
    return dict(row) if row else None

def get_facture_by_numero(numero):
    _ensure_factures_table()
    with get_conn() as conn:
        row = conn.execute(
            """SELECT f.*, c.nom as client_nom FROM factures f
               LEFT JOIN clients c ON f.client_id=c.id
               WHERE f.numero=?""", (numero,)
        ).fetchone()
    return dict(row) if row else None

def create_facture(transaction_id, client_id, type_, contenu_html, montant_net):
    _ensure_factures_table()
    from datetime import datetime
    now = datetime.now()
    prefix = "FAC" if type_ == "vente" else "BON"
    numero = f"{prefix}-{now.strftime('%Y%m%d')}-{transaction_id:05d}"
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO factures (numero,transaction_id,client_id,type,contenu_html,montant_net)
               VALUES (?,?,?,?,?,?)""",
            (numero, transaction_id, client_id, type_, contenu_html, montant_net)
        )
        conn.commit()
        return cur.lastrowid, numero

def delete_facture(facture_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM factures WHERE id=?", (facture_id,))
        conn.commit()


# -- CATEGORIES DU CATALOGUE --------------------------------------------------
def _ensure_categories_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        n = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if n == 0:
            for c in ["General","Tabac","Cannabis","Boisson","Service","Alimentation"]:
                try: conn.execute("INSERT INTO categories (nom) VALUES (?)", (c,))
                except: pass
        conn.commit()

def get_categories():
    _ensure_categories_table()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY nom").fetchall()
    return [dict(r) for r in rows]

def add_category(nom):
    _ensure_categories_table()
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Nom requis")
    with get_conn() as conn:
        exists = conn.execute("SELECT COUNT(*) FROM categories WHERE nom=?", (nom,)).fetchone()[0]
        if exists:
            raise ValueError("Categorie deja existante")
        cur = conn.execute("INSERT INTO categories (nom) VALUES (?)", (nom,))
        conn.commit()
        return cur.lastrowid

def count_articles_in_category(nom):
    try:
        _ensure_catalogue_table()
    except Exception:
        pass
    with get_conn() as conn:
        try:
            return conn.execute("SELECT COUNT(*) FROM catalogue WHERE categorie=? AND actif=1", (nom,)).fetchone()[0]
        except Exception:
            return 0

def delete_category(cid):
    _ensure_categories_table()
    with get_conn() as conn:
        row = conn.execute("SELECT nom FROM categories WHERE id=?", (cid,)).fetchone()
        if not row:
            return
        nom = row[0]
    used = count_articles_in_category(nom)
    if used > 0:
        raise ValueError("%d article(s) utilisent cette categorie" % used)
    with get_conn() as conn:
        conn.execute("DELETE FROM categories WHERE id=?", (cid,))
        conn.commit()


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


def payer_frais_dus(frais_ids):
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

# -- TYPES DE TABAC -----------------------------------------------------------
def _ensure_types_tabac_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS types_tabac (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            prix REAL DEFAULT 0,
            stock REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        n = conn.execute("SELECT COUNT(*) FROM types_tabac").fetchone()[0]
        if n == 0:
            for nom in ["Paquet de tabac","Paquet de blonde","Pot de tabac"]:
                try: conn.execute("INSERT INTO types_tabac (nom,prix,stock) VALUES (?,0,0)", (nom,))
                except: pass
        conn.commit()

def get_types_tabac():
    _ensure_types_tabac_table()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM types_tabac ORDER BY nom").fetchall()
    return [dict(r) for r in rows]

def add_type_tabac(nom, prix=0):
    _ensure_types_tabac_table()
    nom=(nom or "").strip()
    if not nom: raise ValueError("Nom requis")
    with get_conn() as conn:
        ex=conn.execute("SELECT COUNT(*) FROM types_tabac WHERE nom=?", (nom,)).fetchone()[0]
        if ex: raise ValueError("Type deja existant")
        cur=conn.execute("INSERT INTO types_tabac (nom,prix,stock) VALUES (?,?,0)", (nom, float(prix or 0)))
        conn.commit()
        return cur.lastrowid

def update_type_tabac(tid, nom=None, prix=None, stock=None):
    _ensure_types_tabac_table()
    with get_conn() as conn:
        cur=conn.execute("SELECT * FROM types_tabac WHERE id=?", (tid,)).fetchone()
        if not cur: return
        nom2 = (nom if nom is not None else cur["nom"])
        prix2 = (float(prix) if prix is not None else cur["prix"])
        stock2 = (float(stock) if stock is not None else cur["stock"])
        conn.execute("UPDATE types_tabac SET nom=?,prix=?,stock=? WHERE id=?", (nom2,prix2,stock2,tid))
        conn.commit()

def delete_type_tabac(tid):
    _ensure_types_tabac_table()
    with get_conn() as conn:
        conn.execute("DELETE FROM types_tabac WHERE id=?", (tid,))
        conn.commit()

def adjust_stock_tabac(tid, delta):
    """Ajoute (ou retire si negatif) une quantite au stock d'un type."""
    _ensure_types_tabac_table()
    with get_conn() as conn:
        conn.execute("UPDATE types_tabac SET stock = stock + ? WHERE id=?", (float(delta), tid))
        conn.commit()

def adjust_stock_catalogue(item_id, delta):
    """Ajoute (ou retire si negatif) une quantite au stock d'un article."""
    _ensure_catalogue_table()
    with get_conn() as conn:
        conn.execute("UPDATE catalogue SET stock = COALESCE(stock,0) + ? WHERE id=?", (float(delta), item_id))
        conn.commit()


# -- ASSOCIES -----------------------------------------------------------------
def _ensure_associe_column():
    with get_conn() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(clients)").fetchall()}
        if "associe" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN associe INTEGER DEFAULT 0")
            conn.commit()
        if "photo" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN photo TEXT DEFAULT ''")
            conn.commit()

def get_associes():
    _ensure_associe_column()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, tel, notes, COALESCE(associe,0) as associe FROM clients WHERE associe=1 ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]

# -- PRETS TABAC --------------------------------------------------------------
def _ensure_prets_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS prets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            type_tabac TEXT,
            qte_pretee REAL DEFAULT 0,
            qte_rendre REAL DEFAULT 0,
            date_pret TEXT DEFAULT (datetime('now')),
            date_echeance TEXT,
            statut TEXT DEFAULT 'en_cours',
            date_rendu TEXT,
            notes TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        )""")
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(prets)").fetchall()]
            if "catalogue_id" not in cols:
                conn.execute("ALTER TABLE prets ADD COLUMN catalogue_id INTEGER")
        except Exception:
            pass
        conn.commit()

def add_pret(client_id, type_tabac, qte_pretee, qte_rendre, date_echeance=None, notes=None, catalogue_id=None):
    _ensure_prets_table()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO prets (client_id,type_tabac,qte_pretee,qte_rendre,date_echeance,notes,catalogue_id) VALUES (?,?,?,?,?,?,?)",
            (int(client_id), (type_tabac or "").strip(), float(qte_pretee or 0), float(qte_rendre or 0), date_echeance, notes, (int(catalogue_id) if catalogue_id else None)))
        try:
            if catalogue_id:
                conn.execute("UPDATE catalogue SET stock = COALESCE(stock,0) - ? WHERE id=?", (float(qte_pretee or 0), int(catalogue_id)))
            else:
                conn.execute("UPDATE types_tabac SET stock = stock - ? WHERE nom=?", (float(qte_pretee or 0), (type_tabac or "").strip()))
        except Exception:
            pass
        conn.commit()
        return cur.lastrowid

def get_prets_client(cid, statut=None):
    _ensure_prets_table()
    with get_conn() as conn:
        if statut:
            rows = conn.execute("SELECT * FROM prets WHERE client_id=? AND statut=? ORDER BY (date_echeance IS NULL), date_echeance, id", (int(cid), statut)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM prets WHERE client_id=? ORDER BY (statut='rendu'), (date_echeance IS NULL), date_echeance, id", (int(cid),)).fetchall()
    return [dict(r) for r in rows]

def get_prets_en_cours():
    _ensure_prets_table()
    with get_conn() as conn:
        rows = conn.execute("SELECT p.*, c.nom as client_nom FROM prets p LEFT JOIN clients c ON c.id=p.client_id WHERE p.statut='en_cours' ORDER BY (p.date_echeance IS NULL), p.date_echeance, p.id").fetchall()
    return [dict(r) for r in rows]

def marquer_pret_rendu(pid):
    _ensure_prets_table()
    with get_conn() as conn:
        row = conn.execute("SELECT type_tabac, qte_rendre, catalogue_id FROM prets WHERE id=? AND statut='en_cours'", (int(pid),)).fetchone()
        if row:
            try:
                if row[2]:
                    conn.execute("UPDATE catalogue SET stock = COALESCE(stock,0) + ? WHERE id=?", (float(row[1] or 0), int(row[2])))
                else:
                    conn.execute("UPDATE types_tabac SET stock = stock + ? WHERE nom=?", (float(row[1] or 0), row[0] or ""))
            except Exception:
                pass
        conn.execute("UPDATE prets SET statut='rendu', date_rendu=datetime('now') WHERE id=?", (int(pid),))
        conn.commit()

def delete_pret(pid):
    _ensure_prets_table()
    with get_conn() as conn:
        conn.execute("DELETE FROM prets WHERE id=?", (int(pid),))
        conn.commit()


def reset_client_data(client_id):
    """Efface transactions + frais_dus + prets + factures d'un client."""
    _ensure_frais_dus_table(); _ensure_prets_table()
    with get_conn() as conn:
        _archive_txn(conn, "t.client_id=?", (int(client_id),))
        cur = conn.execute("DELETE FROM transactions WHERE client_id=?", (int(client_id),))
        n = cur.rowcount
        conn.execute("DELETE FROM frais_dus WHERE client_id=?", (int(client_id),))
        conn.execute("DELETE FROM prets WHERE client_id=?", (int(client_id),))
        try:
            conn.execute("DELETE FROM factures WHERE client_id=?", (int(client_id),))
        except Exception:
            pass
        conn.commit()
    return n



# -- CARTES SIM ---------------------------------------------------------------
def _ensure_sim_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS sim_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalogue_id INTEGER,
            numero TEXT NOT NULL,
            last4 TEXT DEFAULT '',
            statut TEXT DEFAULT 'stock',
            transaction_id INTEGER,
            client_id INTEGER,
            date_vente TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        try:
            conn.execute("ALTER TABLE sim_cards ADD COLUMN puk TEXT DEFAULT ''")
        except Exception:
            pass
        conn.commit()

def _sync_sim_stock(conn, catalogue_id):
    if not catalogue_id:
        return
    n = conn.execute("SELECT COUNT(*) FROM sim_cards WHERE catalogue_id=? AND statut='stock'", (catalogue_id,)).fetchone()[0]
    conn.execute("UPDATE catalogue SET stock=? WHERE id=?", (n, catalogue_id))

def add_sim_card(catalogue_id, numero, last4="", puk=""):
    _ensure_sim_table()
    numero = (numero or "").strip()
    if not numero:
        return None
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO sim_cards (catalogue_id,numero,last4,puk,statut) VALUES (?,?,?,?,'stock')",
                           (catalogue_id, numero, (last4 or "").strip(), (puk or "").strip()))
        _sync_sim_stock(conn, catalogue_id)
        conn.commit()
        return cur.lastrowid

def add_sim_cards_bulk(catalogue_id, items):
    _ensure_sim_table()
    n = 0
    with get_conn() as conn:
        for it in (items or []):
            numero = (str(it.get("numero", "")).strip() if isinstance(it, dict) else "")
            last4 = (str(it.get("last4", "")).strip() if isinstance(it, dict) else "")
            puk = (str(it.get("puk", "")).strip() if isinstance(it, dict) else "")
            if not numero:
                continue
            conn.execute("INSERT INTO sim_cards (catalogue_id,numero,last4,puk,statut) VALUES (?,?,?,?,'stock')",
                        (catalogue_id, numero, last4, puk))
            n += 1
        _sync_sim_stock(conn, catalogue_id)
        conn.commit()
    return n

def get_sim_cards(catalogue_id=None, statut=None):
    _ensure_sim_table()
    with get_conn() as conn:
        sql = "SELECT * FROM sim_cards WHERE 1=1"
        a = []
        if catalogue_id is not None:
            sql += " AND catalogue_id=?"; a.append(catalogue_id)
        if statut:
            sql += " AND statut=?"; a.append(statut)
        sql += " ORDER BY id ASC"
        rows = conn.execute(sql, tuple(a)).fetchall()
    return [dict(r) for r in rows]

def delete_sim_card(sim_id):
    _ensure_sim_table()
    with get_conn() as conn:
        row = conn.execute("SELECT catalogue_id FROM sim_cards WHERE id=?", (sim_id,)).fetchone()
        conn.execute("DELETE FROM sim_cards WHERE id=?", (sim_id,))
        if row:
            _sync_sim_stock(conn, row["catalogue_id"])
        conn.commit()
    return True

def mark_sim_sold(sim_id, transaction_id=None, client_id=None, date_vente=None):
    _ensure_sim_table()
    with get_conn() as conn:
        row = conn.execute("SELECT catalogue_id FROM sim_cards WHERE id=?", (sim_id,)).fetchone()
        if not row:
            return None
        conn.execute("UPDATE sim_cards SET statut='vendu', transaction_id=?, client_id=?, date_vente=COALESCE(?,datetime('now')) WHERE id=?",
                    (transaction_id, client_id, date_vente, sim_id))
        _sync_sim_stock(conn, row["catalogue_id"])
        conn.commit()
        return dict(conn.execute("SELECT * FROM sim_cards WHERE id=?", (sim_id,)).fetchone())


def get_rentabilite():
    """Rentabilite par article: investi=(stock+vendu)*prix_achat, recupere=CA des ventes."""
    _ensure_catalogue_table()
    with get_conn() as conn:
        arts = conn.execute(
            "SELECT id,nom,categorie,COALESCE(prix_achat,0) AS prix_achat,"
            "COALESCE(prix_vente,0) AS prix_vente,COALESCE(stock,0) AS stock,"
            "COALESCE(unite,'piece') AS unite FROM catalogue WHERE actif=1 "
            "ORDER BY categorie,nom"
        ).fetchall()
        out = []
        for a in arts:
            r = conn.execute(
                "SELECT COALESCE(SUM(quantite),0) AS q, COALESCE(SUM(CASE WHEN instr(COALESCE(notes,''),'[CAISSE CREDIT]')=0 THEN montant_brut ELSE 0 END),0) AS rev "
                "FROM transactions WHERE type='debit' AND motif=?",
                (a["nom"],)
            ).fetchone()
            qv = r["q"] or 0
            recupere = round(r["rev"] or 0, 2)
            pa = a["prix_achat"] or 0
            investi = round((a["stock"] + qv) * pa, 2)
            benefice = round(recupere - investi, 2)
            rembourse = bool(investi > 0 and recupere >= investi)
            out.append({
                "id": a["id"], "nom": a["nom"], "categorie": a["categorie"],
                "prix_achat": pa, "prix_vente": a["prix_vente"], "stock": a["stock"],
                "qty_vendue": qv, "investi": investi, "recupere": recupere,
                "benefice": benefice, "rembourse": rembourse,
            })
        return out


def delete_factures_by_transaction(transaction_id):
    _ensure_factures_table()
    with get_conn() as conn:
        conn.execute("DELETE FROM factures WHERE transaction_id=?", (transaction_id,))
        conn.commit()


def set_transaction_photo(transaction_id, photo):
    with get_conn() as conn:
        conn.execute("UPDATE transactions SET photo_ticket=? WHERE id=?", (photo, transaction_id))
        conn.commit()
