#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeE_page_stock.py  (CRLF-safe)
Ajoute a la page Stock :
  - tableau Stock articles (catalogue) avec alerte stock bas
  - tableau Stock tabac (paquets + prix)
A lancer dans le dossier projet : python etapeE_page_stock.py
"""
import io, re
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
orig=len(html)

# 1) Ajouter les 2 sections HTML apres le tableau des entrees (CRLF-safe via \s*)
if 'id="stockCatalogueTbody"' not in html:
    pat=re.compile(r'(<tbody id="stockTbody"></tbody>\s*</table>\s*</div>)')
    m=pat.search(html)
    if m:
        sections=('\n        <div class="table-wrap" style="margin-top:16px">\n'
                  '          <div class="table-header"><span>📦 Stock articles (catalogue)</span></div>\n'
                  '          <table>\n'
                  '            <thead><tr><th>Article</th><th>Categorie</th><th>Stock</th><th>Statut</th></tr></thead>\n'
                  '            <tbody id="stockCatalogueTbody"></tbody>\n'
                  '          </table>\n'
                  '        </div>\n'
                  '        <div class="table-wrap" style="margin-top:16px">\n'
                  '          <div class="table-header"><span>🚬 Stock tabac</span></div>\n'
                  '          <table>\n'
                  '            <thead><tr><th>Type</th><th>Stock</th><th>Prix</th></tr></thead>\n'
                  '            <tbody id="stockTabacTbody"></tbody>\n'
                  '          </table>\n'
                  '        </div>')
        eol="\r\n" if "\r\n" in html else "\n"
        sections=sections.replace("\n",eol)
        html=html[:m.end()]+sections+html[m.end():]
        print("1) sections catalogue + tabac ajoutees a la page Stock")
    else:
        print("1) ATTENTION tableau entrees (stockTbody) non trouve")
else:
    print("1) sections deja presentes")

# 2) Appeler loadStockExtra() au debut de loadStock (1 ligne, CRLF-safe)
old_fn="async function loadStock() {"
new_fn="async function loadStock() {loadStockExtra();"
if old_fn in html and "loadStockExtra()" not in html.split("async function loadStock() {")[1][:60]:
    html=html.replace(old_fn,new_fn,1)
    print("2) loadStock appelle loadStockExtra")
else:
    print("2) deja present ou introuvable")

# 3) Definir loadStockExtra (nouveau bloc script)
if "function loadStockExtra" not in html:
    JS=r"""
<script>
// ===== STOCK : articles catalogue + tabac =====
async function loadStockExtra(){
  try{
    var rc=await api('/api/catalogue');
    var cat=(rc&&rc.ok)?rc.data:[];
    var tb=document.getElementById('stockCatalogueTbody');
    if(tb){
      tb.innerHTML='';
      if(!cat.length){tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:16px">Aucun article</td></tr>';}
      else cat.forEach(function(a){
        var u=a.unite==='gramme'?'g':a.unite==='litre'?'L':'pcs';
        var stock=parseFloat(a.stock||0);var smin=parseFloat(a.stock_min||0);
        var bas=stock<=smin;
        var tr=document.createElement('tr');
        tr.innerHTML='<td style="color:var(--text);font-weight:500">'+a.nom+'</td>'
          +'<td style="color:var(--text3)">'+(a.categorie||'')+'</td>'
          +'<td class="mono" style="color:'+(bas?'var(--red)':'var(--green)')+';font-weight:600">'+stock.toFixed(0)+' '+u+'</td>'
          +'<td>'+(bas?'🔴 Bas':'🟢 OK')+'</td>';
        tb.appendChild(tr);
      });
    }
  }catch(e){}
  try{
    var rt=await api('/api/types-tabac');
    var tt=(rt&&rt.ok)?rt.data:[];
    var tb2=document.getElementById('stockTabacTbody');
    if(tb2){
      tb2.innerHTML='';
      if(!tt.length){tb2.innerHTML='<tr><td colspan="3" style="text-align:center;color:var(--text3);padding:16px">Aucun type</td></tr>';}
      else tt.forEach(function(t){
        var stock=parseFloat(t.stock||0);
        var tr=document.createElement('tr');
        tr.innerHTML='<td style="color:var(--text);font-weight:500">🚬 '+t.nom+'</td>'
          +'<td class="mono" style="color:'+(stock<=0?'var(--red)':'var(--green)')+';font-weight:600">'+stock.toFixed(0)+' paquet(s)</td>'
          +'<td class="mono">'+fmt(parseFloat(t.prix||0))+'</td>';
        tb2.appendChild(tr);
      });
    }
  }catch(e){}
}
</script>
"""
    eol="\r\n" if "\r\n" in html else "\n"
    JS=JS.replace("\n",eol)
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+eol+JS+html[at:]
    print("3) fonction loadStockExtra ajoutee")
else:
    print("3) deja presente")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE === (%+d caracteres)" % (len(html)-orig))
