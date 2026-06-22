t=open("web/index.html",encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in t else "\n"
h_o="<th>Qte</th><th>P.U.</th><th>Net</th><th>Notes</th>"
h_n="<th>Qte</th><th>P.U.</th><th>Brut</th><th>Frais</th><th>Net</th><th>Notes</th>"
if "<th>Brut</th><th>Frais</th><th>Net</th>" in t: print("header: deja")
elif t.count(h_o)==1: t=t.replace(h_o,h_n,1); print("header: OK")
else: print("header: KO",t.count(h_o))
brut_line="""    html += '<td class="'+(isV?'vente':'remb')+'">'+(isV?'+':'-')+parseFloat(t.montant_brut||0).toFixed(2)+' EUR</td>';"""
frais_line="""    html += '<td style="color:#c9a84c">'+(parseFloat(t.frais||0)>0?('-'+parseFloat(t.frais||0).toFixed(2)+' EUR'):'-')+'</td>';"""
net_line="""    html += '<td class="'+(isV?'vente':'remb')+'">'+(isV?'+':'-')+(t.montant_net!=null?parseFloat(t.montant_net):(parseFloat(t.montant_brut||0)-parseFloat(t.frais||0))).toFixed(2)+' EUR</td>';"""
GUARD="(parseFloat(t.frais||0)>0?('-'+parseFloat(t.frais||0).toFixed(2)+' EUR'):'-')"
if GUARD in t: print("row: deja")
elif t.count(brut_line)==1: t=t.replace(brut_line, brut_line+eol+frais_line+eol+net_line,1); print("row: OK")
else: print("row: KO",t.count(brut_line))
open("web/index.html","w",encoding="utf-8",newline="").write(t)
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.18"' in u: print("ver: deja")
elif u.count('APP_VERSION = "2.17"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.17"','APP_VERSION = "2.18"',1)); print("ver -> 2.18")
else: print("ver KO")
