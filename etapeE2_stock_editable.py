#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeE2_stock_editable.py  (CRLF-safe : remplacements 1 ligne + ajout bloc)
Rend le stock modifiable manuellement sur la page Stock :
  - article catalogue : champ editable -> ajuste le stock
  - tabac : champ editable -> met a jour le stock
A lancer dans le dossier projet : python etapeE2_stock_editable.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()

# 1) Cellule stock catalogue -> input editable
old_cat='''+'<td class="mono" style="color:'+(bas?'var(--red)':'var(--green)')+';font-weight:600">'+stock.toFixed(0)+' '+u+'</td>' '''.rstrip()
new_cat='''+'<td><input type="number" value="'+stock.toFixed(0)+'" step="1" onchange="setCatalogueStock('+a.id+','+stock+',this.value)" style="width:80px;text-align:right;padding:4px 6px;border-radius:6px;border:1px solid '+(bas?'var(--red)':'var(--border)')+';background:var(--bg2);color:var(--text)"> '+u+'</td>' '''.rstrip()
if old_cat in html:
    html=html.replace(old_cat,new_cat,1)
    print("1) stock catalogue editable")
elif "setCatalogueStock(" in html:
    print("1) deja editable")
else:
    print("1) ATTENTION cellule stock catalogue non trouvee")

# 2) Cellule stock tabac -> input editable
old_tab='''+'<td class="mono" style="color:'+(stock<=0?'var(--red)':'var(--green)')+';font-weight:600">'+stock.toFixed(0)+' paquet(s)</td>' '''.rstrip()
new_tab='''+'<td><input type="number" value="'+stock.toFixed(0)+'" step="1" onchange="setTabacStock('+t.id+',this.value)" style="width:80px;text-align:right;padding:4px 6px;border-radius:6px;border:1px solid var(--border);background:var(--bg2);color:var(--text)"> paquet(s)</td>' '''.rstrip()
if old_tab in html:
    html=html.replace(old_tab,new_tab,1)
    print("2) stock tabac editable")
elif "setTabacStock(" in html:
    print("2) deja editable")
else:
    print("2) ATTENTION cellule stock tabac non trouvee")

# 3) Fonctions de mise a jour
if "function setCatalogueStock" not in html:
    JS=r"""
<script>
// ===== STOCK : modification manuelle =====
async function setCatalogueStock(id,current,val){
  var nv=parseFloat(val); if(isNaN(nv)){return;}
  var delta=nv-parseFloat(current||0);
  if(delta===0){return;}
  var r=await api('/api/catalogue/'+id+'/adjust-stock',{method:'POST',body:{delta:delta}});
  if(r&&r.ok){notify('Stock mis a jour');loadStockExtra();if(typeof loadCatalogue==='function')loadCatalogue();}
  else notify('Erreur','error');
}
async function setTabacStock(id,val){
  var nv=parseFloat(val); if(isNaN(nv)){return;}
  var r=await api('/api/types-tabac/'+id,{method:'PUT',body:{stock:nv}});
  if(r&&r.ok){notify('Stock tabac mis a jour');loadStockExtra();if(typeof loadTypesTabac==='function')loadTypesTabac();}
  else notify('Erreur','error');
}
</script>
"""
    eol="\r\n" if "\r\n" in html else "\n"
    JS=JS.replace("\n",eol)
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+eol+JS+html[at:]
    print("3) fonctions de modification du stock ajoutees")
else:
    print("3) deja presentes")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
