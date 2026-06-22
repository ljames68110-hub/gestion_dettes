a=open("api.py",encoding="utf-8",newline="").read()
if "def sim_cards_list" in a:
    print("api: deja")
else:
    anchor='def start(host="127.0.0.1", port=5000, debug=False):'
    eol="\r\n" if "\r\n" in a else "\n"
    ROUTES='''@app.route("/api/sim-cards", methods=["GET"])
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


'''
    if a.count(anchor)!=1:
        print("api: KO anchor", a.count(anchor))
    else:
        open("api.py","w",encoding="utf-8",newline="").write(a.replace(anchor, ROUTES.replace("\n",eol)+anchor,1))
        print("api: OK")
