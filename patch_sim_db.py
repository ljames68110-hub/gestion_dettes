d=open("db.py",encoding="utf-8",newline="").read()
if "def add_sim_card" in d:
    print("db: deja")
else:
    eol="\r\n" if "\r\n" in d else "\n"
    BLOCK='''

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
        conn.commit()

def _sync_sim_stock(conn, catalogue_id):
    if not catalogue_id:
        return
    n = conn.execute("SELECT COUNT(*) FROM sim_cards WHERE catalogue_id=? AND statut='stock'", (catalogue_id,)).fetchone()[0]
    conn.execute("UPDATE catalogue SET stock=? WHERE id=?", (n, catalogue_id))

def add_sim_card(catalogue_id, numero, last4=""):
    _ensure_sim_table()
    numero = (numero or "").strip()
    if not numero:
        return None
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO sim_cards (catalogue_id,numero,last4,statut) VALUES (?,?,?,'stock')",
                           (catalogue_id, numero, (last4 or "").strip()))
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
            if not numero:
                continue
            conn.execute("INSERT INTO sim_cards (catalogue_id,numero,last4,statut) VALUES (?,?,?,'stock')",
                        (catalogue_id, numero, last4))
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
'''
    open("db.py","w",encoding="utf-8",newline="").write(d+BLOCK.replace("\n",eol))
    print("db: OK")
