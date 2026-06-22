#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_tabac_api2.py  (gere les fins de ligne Windows CRLF)
Insere le calcul des PAQUETS de tabac dans stats-comptes.
A lancer dans le dossier projet : python fix_tabac_api2.py
"""
import io, re
ap="api.py"
api=io.open(ap,encoding="utf-8").read()

if 'result["tabac"]["paquets"]' in api:
    print("API) deja present")
else:
    BLOCK = (
"    # --- Tabac en paquets (par type) ---\n"
"    try:\n"
"        with db.get_conn() as conn:\n"
"            tab_rows = conn.execute(\"\"\"\n"
"                SELECT COALESCE(mode_paiement,'Tabac') as nom, type, COALESCE(SUM(quantite),0) as qte\n"
"                FROM transactions\n"
"                WHERE client_id=? AND COALESCE(compte,'euro')='tabac'\n"
"                GROUP BY COALESCE(mode_paiement,'Tabac'), type\n"
"            \"\"\", (cid,)).fetchall()\n"
"            prix_map = {}\n"
"            try:\n"
"                for t in conn.execute(\"SELECT nom, prix FROM types_tabac\").fetchall():\n"
"                    prix_map[t[\"nom\"]] = t[\"prix\"]\n"
"            except Exception:\n"
"                pass\n"
"        detail = {}\n"
"        for r in tab_rows:\n"
"            nom = r[\"nom\"] or \"Tabac\"\n"
"            d = detail.setdefault(nom, {\"nom\": nom, \"paquets\": 0, \"prix\": prix_map.get(nom, 0)})\n"
"            if r[\"type\"] == \"debit\":\n"
"                d[\"paquets\"] += r[\"qte\"]\n"
"            else:\n"
"                d[\"paquets\"] -= r[\"qte\"]\n"
"        total_p = 0; total_v = 0; details = []\n"
"        for nom, d in detail.items():\n"
"            d[\"paquets\"] = round(d[\"paquets\"], 2)\n"
"            d[\"valeur\"] = round(d[\"paquets\"] * (d[\"prix\"] or 0), 2)\n"
"            if d[\"paquets\"] != 0:\n"
"                total_p += d[\"paquets\"]; total_v += d[\"valeur\"]; details.append(d)\n"
"        result[\"tabac\"][\"paquets\"] = round(total_p, 2)\n"
"        result[\"tabac\"][\"valeur\"] = round(total_v, 2)\n"
"        result[\"tabac\"][\"details\"] = details\n"
"    except Exception:\n"
"        result[\"tabac\"][\"paquets\"] = 0\n"
"        result[\"tabac\"][\"valeur\"] = 0\n"
"        result[\"tabac\"][\"details\"] = []\n"
    )
    # Ancre tolerante CRLF/LF : 'return ok(result)' suivi de la route /stats
    pat=re.compile(r'(    return ok\(result\))(\r?\n)(@app\.route\("/api/clients/<int:cid>/stats"\))')
    if pat.search(api):
        # determiner la fin de ligne utilisee
        eol = "\r\n" if "\r\n" in api else "\n"
        block_eol = BLOCK.replace("\n", eol)
        api2 = pat.sub(lambda m: block_eol + m.group(1) + m.group(2) + m.group(3), api, count=1)
        io.open(ap,"w",encoding="utf-8",newline="").write(api2)
        print("API) calcul des paquets de tabac insere (CRLF gere)")
    else:
        print("API) ATTENTION ancre toujours introuvable")
