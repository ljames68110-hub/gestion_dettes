NL="\r\n"
# ---------- db.py ----------
d=open("db.py",encoding="utf-8",newline="").read(); box=[d]
def rep(tag,o,n,guard):
    if guard in box[0]: print(tag,": deja"); return
    if box[0].count(o)==1: box[0]=box[0].replace(o,n,1); print(tag,": OK")
    else: print(tag,": KO",box[0].count(o))
rep("db ensure",
 NL.join(['            conn.execute("ALTER TABLE clients ADD COLUMN associe INTEGER DEFAULT 0")','            conn.commit()']),
 NL.join(['            conn.execute("ALTER TABLE clients ADD COLUMN associe INTEGER DEFAULT 0")','            conn.commit()','        if "photo" not in cols:',"            conn.execute(\"ALTER TABLE clients ADD COLUMN photo TEXT DEFAULT ''\")",'            conn.commit()']),
 "ALTER TABLE clients ADD COLUMN photo")
rep("db add_client",
 NL.join(['def add_client(nom, email=None, tel=None, notes=None, associe=0):','    _ensure_associe_column()','    with get_conn() as conn:','        cur = conn.execute(','            "INSERT INTO clients (nom,email,tel,notes,associe) VALUES (?,?,?,?,?)",','            (nom, email or "", tel or "", notes or "", int(associe or 0))','        )']),
 NL.join(['def add_client(nom, email=None, tel=None, notes=None, associe=0, photo=None):','    _ensure_associe_column()','    with get_conn() as conn:','        cur = conn.execute(','            "INSERT INTO clients (nom,email,tel,notes,associe,photo) VALUES (?,?,?,?,?,?)",','            (nom, email or "", tel or "", notes or "", int(associe or 0), photo or "")','        )']),
 "associe=0, photo=None")
rep("db update_client",
 NL.join(['def update_client(client_id: int, nom=None, email=None, tel=None, notes=None):','    with get_conn() as conn:','        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()','        if not row:','            return False','        conn.execute(','            "UPDATE clients SET nom=?,email=?,tel=?,notes=? WHERE id=?",','            (nom or row["nom"], email or row["email"],','             tel or row["tel"], notes or row["notes"], client_id)','        )']),
 NL.join(['def update_client(client_id: int, nom=None, email=None, tel=None, notes=None, photo=None):','    _ensure_associe_column()','    with get_conn() as conn:','        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()','        if not row:','            return False','        conn.execute(','            "UPDATE clients SET nom=?,email=?,tel=?,notes=?,photo=? WHERE id=?",','            (nom or row["nom"], email or row["email"],','             tel or row["tel"], notes or row["notes"],','             (photo if photo is not None else row["photo"]), client_id)','        )']),
 "notes=None, photo=None")
rep("db get_clients",
 '"SELECT id, nom, email, tel, notes, COALESCE(associe,0) as associe FROM clients ORDER BY nom"',
 '"SELECT id, nom, email, tel, notes, COALESCE(associe,0) as associe, COALESCE(photo,\'\') as photo FROM clients ORDER BY nom"',
 "as photo FROM clients")
open("db.py","w",encoding="utf-8",newline="").write(box[0])
import py_compile; py_compile.compile("db.py",doraise=True); print("py_compile db OK")
# ---------- api.py ----------
a=open("api.py",encoding="utf-8",newline="").read(); abox=[a]
def repa(tag,o,n,guard):
    if guard in abox[0]: print(tag,": deja"); return
    if abox[0].count(o)==1: abox[0]=abox[0].replace(o,n,1); print(tag,": OK")
    else: print(tag,": KO",abox[0].count(o))
repa("api create",
 NL.join(['    cid = db.add_client(','        nom=nom,','        email=data.get("email", ""),','        tel=data.get("tel", ""),','        notes=data.get("notes", ""),','    )']),
 NL.join(['    cid = db.add_client(','        nom=nom,','        email=data.get("email", ""),','        tel=data.get("tel", ""),','        notes=data.get("notes", ""),','        photo=data.get("photo", ""),','    )']),
 'photo=data.get("photo"')
repa("api update",
 'if not db.update_client(cid, **{k: data.get(k) for k in ("nom","email","tel","notes")}):',
 'if not db.update_client(cid, **{k: data.get(k) for k in ("nom","email","tel","notes","photo")}):',
 '"notes","photo"')
open("api.py","w",encoding="utf-8",newline="").write(abox[0])
py_compile.compile("api.py",doraise=True); print("py_compile api OK")
# ---------- version 2.13 -> 2.14 ----------
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.14"' in u: print("ver: deja 2.14")
elif u.count('APP_VERSION = "2.13"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.13"','APP_VERSION = "2.14"',1)); print("ver -> 2.14")
else: print("ver KO")
