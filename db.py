# db.py
import sqlite3
from datetime import datetime

DB_FILE = "dettes.db"

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    """Crée les tables si elles n'existent pas."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            email TEXT,
            tel TEXT,
            notes TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            motif TEXT,
            quantite INTEGER DEFAULT 1,
            prix_unitaire REAL DEFAULT 0.0,
            montant_brut REAL,
            mode_paiement TEXT,
            frais REAL DEFAULT 0.0,
            montant_net REAL,
            date TEXT,
            reference TEXT,
            notes TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            montant REAL,
            date_paiement TEXT,
            mode_paiement TEXT,
            note TEXT,
            FOREIGN KEY(transaction_id) REFERENCES transactions(id)
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS auth (
            id INTEGER PRIMARY KEY,
            pw_hash BLOB,
            salt BLOB,
            kdf_params TEXT
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_client ON transactions(client_id)")
        conn.commit()

def add_client(nom, email=None, tel=None, notes=None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO clients (nom,email,tel,notes) VALUES (?,?,?,?)",
                    (nom, email, tel, notes))
        conn.commit()
        return cur.lastrowid

def get_clients():
    with get_conn() as conn:
        cur = conn.cursor()
        return cur.execute("SELECT id, nom FROM clients ORDER BY nom").fetchall()

def get_client(client_id):
    with get_conn() as conn:
        cur = conn.cursor()
        return cur.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()

def add_transaction(client_id, type_, motif, quantite, prix_unitaire, mode_paiement, frais, montant_brut, montant_net, reference=None, notes=None):
    date = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""INSERT INTO transactions
            (client_id,type,motif,quantite,prix_unitaire,montant_brut,mode_paiement,frais,montant_net,date,reference,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, type_, motif, quantite, prix_unitaire, montant_brut, mode_paiement, frais, montant_net, date, reference, notes))
        conn.commit()
        return cur.lastrowid

def get_transactions(client_id):
    with get_conn() as conn:
        cur = conn.cursor()
        return cur.execute("""SELECT id, date, type, motif, quantite, prix_unitaire, montant_brut, mode_paiement, frais, montant_net, reference, notes
                              FROM transactions WHERE client_id=? ORDER BY date DESC""", (client_id,)).fetchall()

def get_stats(client_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions WHERE client_id=?", (client_id,))
        nb = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(montant_net),0) FROM transactions WHERE client_id=? AND type='credit'", (client_id,))
        total_encaisse = cur.fetchone()[0] or 0.0
        cur.execute("SELECT COALESCE(SUM(frais),0) FROM transactions WHERE client_id=? AND type='credit'", (client_id,))
        total_frais = cur.fetchone()[0] or 0.0
        cur.execute("SELECT COUNT(*) FROM transactions WHERE client_id=? AND type='credit'", (client_id,))
        nb_credits = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM transactions WHERE client_id=? AND type='debit'", (client_id,))
        nb_debits = cur.fetchone()[0]
        return {
            "nb_transactions": nb,
            "total_encaisse": total_encaisse,
            "total_frais": total_frais,
            "nb_credits": nb_credits,
            "nb_debits": nb_debits
        }
