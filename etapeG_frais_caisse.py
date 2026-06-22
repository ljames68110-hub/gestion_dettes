#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeG_frais_caisse.py  (CRLF-safe)
Affiche les frais en direct dans la caisse pour les remboursements PCS/Paysafecard,
et rend le choix "j'absorbe / le client paie" explicite.
A lancer dans le dossier projet : python etapeG_frais_caisse.py
"""
import io, re
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in html else "\n"

# 1) Zone d'info frais sous la case "j'absorbe" (regex CRLF-safe)
if 'id="posFraisInfo"' not in html:
    pat=re.compile(r"(J'absorbe les frais sur le remboursement\s*</label>)")
    m=pat.search(html)
    if m:
        info='<div id="posFraisInfo" style="display:none;font-size:11px;color:var(--gold2);margin-top:6px;padding:6px 8px;background:var(--bg2);border-radius:6px;border:1px solid var(--gold);line-height:1.5"></div>'
        html=html[:m.end()]+eol+'                '+info+html[m.end():]
        print("1) zone info frais ajoutee")
    else:
        print("1) ATTENTION label j'absorbe non trouve")
else:
    print("1) deja present")

# 2) posMode declenche aussi le recalcul (pour mettre a jour les frais)
old_sel='<select class="pos-mode" id="posMode" onchange="posModeChanged()">'
new_sel='<select class="pos-mode" id="posMode" onchange="posModeChanged();updatePosTotals()">'
if old_sel in html:
    html=html.replace(old_sel,new_sel,1)
    print("2) posMode recalcule les frais")
elif 'posModeChanged();updatePosTotals()' in html:
    print("2) deja present")
else:
    print("2) ATTENTION select posMode non trouve")

# 3) updatePosTotals appelle updatePosFrais (1 ligne)
old_line="var el=document.getElementById('posTotal'); if(el)el.textContent=venteTotal.toFixed(2)+' EUR'+(reduc>0?' (-'+reduc.toFixed(2)+')':'');"
new_line=old_line+"updatePosFrais();"
if old_line in html and "updatePosFrais();" not in html:
    html=html.replace(old_line,new_line,1)
    print("3) updatePosTotals appelle updatePosFrais")
elif "updatePosFrais();" in html:
    print("3) deja present")
else:
    print("3) ATTENTION ligne posTotal non trouvee")

# 4) Definir updatePosFrais
if "function updatePosFrais" not in html:
    JS=r"""
<script>
// ===== CAISSE : affichage des frais de remboursement =====
function updatePosFrais(){
  var info=document.getElementById('posFraisInfo'); if(!info)return;
  var remb=(typeof getRemb==='function')?getRemb():0;
  var mode=(document.getElementById('posMode')||{}).value||'';
  var rate=(typeof FEES!=='undefined'&&FEES[mode])?FEES[mode]:0;
  if(remb>0 && rate>0){
    var frais=Math.round(remb*rate*100)/100;
    var jAbsorbe=document.getElementById('posRembFrais')?document.getElementById('posRembFrais').checked:true;
    info.style.display='block';
    info.innerHTML='Frais '+mode+' ('+(rate*100).toFixed(0)+'%) sur '+remb.toFixed(2)+' EUR = <strong>'+frais.toFixed(2)+' EUR</strong><br>'
      +(jAbsorbe
        ? '✅ Tu absorbes les frais : le client est credite de <strong>'+remb.toFixed(2)+' EUR</strong>'
        : '⚠️ Le client paie les frais : credite de <strong>'+(remb-frais).toFixed(2)+' EUR</strong> (tu gardes '+frais.toFixed(2)+' EUR)');
  }else{
    info.style.display='none';
    info.innerHTML='';
  }
}
</script>
"""
    JS=JS.replace("\n",eol)
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+eol+JS+html[at:]
    print("4) fonction updatePosFrais ajoutee")
else:
    print("4) deja presente")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
