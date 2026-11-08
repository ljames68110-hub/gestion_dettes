#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_tickets_back.py  (Point 3 - backend)
Bibliotheque de tickets d'encaissement rangee DANS la base (donc chiffree a la
fermeture + envoyee sur le cloud automatiquement).
  - db.py  : table tickets_encaissement + fonctions (ajout/liste/image/suppr/compte)
  - api.py : routes /api/tickets-enc (liste, image, ajout manuel, suppression,
             dossier source, selecteur, import depuis le dossier + suppression source)
L'import lit les sous-dossiers PCS / Transcash / Paysafecard du dossier source,
enregistre chaque image dans la base, PUIS supprime le fichier d'origine.
Idempotent, verifie la syntaxe. A lancer dans le dossier du projet.
"""
import os, sys, py_compile

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)
def eol_of(t): return "\r\n" if "\r\n" in t else "\n"
def L(block, eol): return eol.join(block.split("\n"))

DB_BLOCK = '''

# TICKETS D'ENCAISSEMENT (bibliotheque) -- ne pas dupliquer
def _ensure_tickets_enc_table():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tickets_encaissement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'pcs',
            image TEXT NOT NULL,
            nom_fichier TEXT DEFAULT '',
            montant REAL DEFAULT 0,
            note TEXT DEFAULT '',
            date_ajout TEXT
        )""")

def add_ticket_enc(type_, image, nom_fichier="", montant=0, note=""):
    _ensure_tickets_enc_table()
    t = (type_ or "pcs").strip().lower()
    if t not in ("pcs", "transcash", "paysafecard"):
        t = "pcs"
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets_encaissement (type,image,nom_fichier,montant,note,date_ajout) VALUES (?,?,?,?,?,?)",
            (t, image or "", nom_fichier or "", float(montant or 0), note or "",
             datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
        return cur.lastrowid

def get_tickets_enc(type_=None):
    _ensure_tickets_enc_table()
    with get_conn() as conn:
        if type_ and type_ in ("pcs", "transcash", "paysafecard"):
            rows = conn.execute(
                "SELECT id,type,nom_fichier,montant,note,date_ajout FROM tickets_encaissement WHERE type=? ORDER BY id DESC",
                (type_,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,type,nom_fichier,montant,note,date_ajout FROM tickets_encaissement ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]

def get_ticket_enc_image(tid):
    _ensure_tickets_enc_table()
    with get_conn() as conn:
        row = conn.execute("SELECT image FROM tickets_encaissement WHERE id=?", (int(tid),)).fetchone()
    return row["image"] if row else None

def delete_ticket_enc(tid):
    _ensure_tickets_enc_table()
    with get_conn() as conn:
        conn.execute("DELETE FROM tickets_encaissement WHERE id=?", (int(tid),))
    return True

def count_tickets_enc():
    _ensure_tickets_enc_table()
    with get_conn() as conn:
        rows = conn.execute("SELECT type, COUNT(*) c FROM tickets_encaissement GROUP BY type").fetchall()
    out = {"pcs": 0, "transcash": 0, "paysafecard": 0}
    for r in rows:
        if r["type"] in out:
            out[r["type"]] = r["c"]
    out["tous"] = out["pcs"] + out["transcash"] + out["paysafecard"]
    return out
'''

API_BLOCK = '''

# TICKETS D'ENCAISSEMENT (bibliotheque) -- ne pas dupliquer
_TICKETS_ENC_TYPES = ("pcs", "transcash", "paysafecard")
_TICKETS_ENC_NOMS = {"pcs": "PCS", "transcash": "Transcash", "paysafecard": "Paysafecard"}
_TICKETS_ENC_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}

def _tickets_enc_src_dir():
    return db.get_setting("tickets_src_dir", "")

def _tickets_enc_subfolder(src, t):
    return os.path.join(src, _TICKETS_ENC_NOMS[t])

@app.route("/api/tickets-enc")
@require_auth
def tickets_enc_list():
    t = request.args.get("type") or None
    items = db.get_tickets_enc(t if t in _TICKETS_ENC_TYPES else None)
    return ok({"items": items, "counts": db.count_tickets_enc(), "src": _tickets_enc_src_dir()})

@app.route("/api/tickets-enc/<int:tid>/image")
@require_auth
def tickets_enc_image(tid):
    img = db.get_ticket_enc_image(tid)
    if img is None:
        return err("Ticket introuvable", 404)
    return ok({"image": img})

@app.route("/api/tickets-enc", methods=["POST"])
@require_auth
def tickets_enc_add():
    d = request.json or {}
    img = d.get("image", "")
    if not img:
        return err("Image manquante")
    tid = db.add_ticket_enc(d.get("type", "pcs"), img, d.get("nom_fichier", ""),
                            d.get("montant", 0), d.get("note", ""))
    return ok({"id": tid})

@app.route("/api/tickets-enc/<int:tid>", methods=["DELETE"])
@require_auth
def tickets_enc_delete(tid):
    db.delete_ticket_enc(tid)
    return ok({"deleted": tid})

@app.route("/api/tickets-enc/source", methods=["GET"])
@require_auth
def tickets_enc_source_get():
    return ok({"dir": _tickets_enc_src_dir()})

@app.route("/api/tickets-enc/source", methods=["POST"])
@require_auth
def tickets_enc_source_set():
    d = request.json or {}
    db.set_setting("tickets_src_dir", d.get("dir", "") or "")
    return ok({"dir": _tickets_enc_src_dir()})

@app.route("/api/tickets-enc/source/pick", methods=["POST"])
@require_auth
def tickets_enc_source_pick():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="Choisir le dossier des tickets (PCS / Transcash / Paysafecard)")
        root.destroy()
    except Exception as e:
        return err("Impossible d'ouvrir le selecteur : %s" % e)
    return ok({"dir": path or ""})

@app.route("/api/tickets-enc/import", methods=["POST"])
@require_auth
def tickets_enc_import():
    import base64
    src = _tickets_enc_src_dir()
    if not src or not os.path.isdir(src):
        return err("Dossier source non configure ou introuvable")
    imported = {"pcs": 0, "transcash": 0, "paysafecard": 0}
    deleted = 0
    errors = []
    for t in _TICKETS_ENC_TYPES:
        folder = _tickets_enc_subfolder(src, t)
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            errors.append("%s: %s" % (folder, e)); continue
        try:
            names = sorted(os.listdir(folder))
        except Exception as e:
            errors.append("%s: %s" % (folder, e)); continue
        for name in names:
            fp = os.path.join(folder, name)
            if not os.path.isfile(fp):
                continue
            ext = os.path.splitext(name)[1].lower()
            mime = _TICKETS_ENC_EXT.get(ext)
            if not mime:
                continue
            try:
                with open(fp, "rb") as f:
                    raw = f.read()
                data_url = "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))
                db.add_ticket_enc(t, data_url, name, 0, "")
            except Exception as e:
                errors.append("%s: %s" % (name, e)); continue
            # suppression de la source UNIQUEMENT apres enregistrement reussi
            try:
                os.remove(fp)
                deleted += 1
            except Exception as e:
                errors.append("suppression %s: %s" % (name, e))
            imported[t] += 1
    return ok({"imported": imported, "deleted": deleted, "errors": errors,
               "total": imported["pcs"] + imported["transcash"] + imported["paysafecard"]})
'''

def main():
    for f in ("db.py", "api.py"):
        if not os.path.exists(f):
            print("ERREUR : lance depuis le dossier du projet (%s manquant)" % f); sys.exit(1)

    # ---- db.py ----
    d = read("db.py"); eol = eol_of(d)
    if "tickets_encaissement" in d:
        print("  [=] db.py : deja patche")
    else:
        if not d.endswith(("\n", "\r")): d += eol
        d += L(DB_BLOCK, eol)
        write("db.py", d)
        print("  [+] db.py : table + fonctions tickets_encaissement")

    # ---- api.py ----
    a = read("api.py"); eol = eol_of(a)
    if "/api/tickets-enc" in a:
        print("  [=] api.py : deja patche")
    else:
        if not a.endswith(("\n", "\r")): a += eol
        a += L(API_BLOCK, eol)
        write("api.py", a)
        print("  [+] api.py : routes /api/tickets-enc")

    print("Verification syntaxe...")
    for f in ("db.py", "api.py"):
        try:
            py_compile.compile(f, doraise=True); print("  [ok] %s" % f)
        except py_compile.PyCompileError as e:
            print("  [X] %s : %s" % (f, e)); sys.exit(1)
    print("\nTermine (backend tickets d'encaissement).")

if __name__ == "__main__":
    main()
