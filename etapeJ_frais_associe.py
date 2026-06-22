#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etapeJ_frais_associe.py  (CRLF-safe, web/index.html)
Reglage "Frais associes automatiques" :
  - Parametres : case a cocher (defaut ON = l'associe paie toujours, sans question)
  - Caisse : si associe + automatique -> frais a sa charge sans demander
             si automatique desactive -> la caisse demande (case visible)
A lancer dans le dossier projet : python etapeJ_frais_associe.py
"""
import io
p="web/index.html"
html=io.open(p,encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in html else "\n"

# 1) Carte reglage dans Parametres
grid_anchor='<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:900px">'
if 'id="setAssocieFraisAuto"' not in html and grid_anchor in html:
    card=('<div class="card" style="grid-column:1/-1"><div class="card-title">🤝 Frais des associés</div>'
          '<label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:14px;color:var(--text2)">'
          '<input type="checkbox" id="setAssocieFraisAuto" onchange="saveAssocieFraisAuto()" style="width:auto;margin:0"> '
          "Mode automatique : l'associé paie toujours ses frais (sans me demander)</label>"
          '<div style="font-size:12px;color:var(--text3);margin-top:8px">Si décoché, la caisse te demandera à chaque fois (case « j\'absorbe ? ») pour les associés.</div></div>')
    html=html.replace(grid_anchor, grid_anchor+card, 1)
    print("1) carte reglage Frais associes ajoutee")
elif 'id="setAssocieFraisAuto"' in html:
    print("1) deja present")
else:
    print("1) ATTENTION grille Parametres non trouvee")

# 2) initSettings charge le reglage
is_old="function initSettings(){loadAssocies();loadTypesTabac();"
is_new="function initSettings(){loadAssocieFraisAuto();loadAssocies();loadTypesTabac();"
if is_old in html:
    html=html.replace(is_old,is_new,1)
    print("2) initSettings charge le reglage")
elif "loadAssocieFraisAuto()" in html.split("function initSettings(){")[1][:120] if "function initSettings(){" in html else False:
    print("2) deja present")
else:
    print("2) ATTENTION initSettings non trouve")

# 3) initCaisse charge le reglage (pour l'avoir en caisse)
ic_old="function initCaisse(){"
ic_new="function initCaisse(){loadAssocieFraisAuto();"
if ic_old in html and "loadAssocieFraisAuto()" not in html.split("function initCaisse(){")[1][:120]:
    html=html.replace(ic_old,ic_new,1)
    print("3) initCaisse charge le reglage")
elif "function initCaisse(){" in html and "loadAssocieFraisAuto()" in html.split("function initCaisse(){")[1][:120]:
    print("3) deja present")
else:
    print("3) ATTENTION initCaisse non trouve")

# 4) posEncaisser : forcer frais a la charge de l'associe si automatique
fee_old="var jAbsorbe=document.getElementById('posRembFrais')?document.getElementById('posRembFrais').checked:true;var fraisDeduits=jAbsorbe?0:1;"
fee_new="var jAbsorbe=document.getElementById('posRembFrais')?document.getElementById('posRembFrais').checked:true;var fraisDeduits=(posIsAssocie&&window.associeFraisAuto)?1:(jAbsorbe?0:1);"
if fee_old in html:
    html=html.replace(fee_old,fee_new,1)
    print("4) posEncaisser : frais associe automatiques")
elif "(posIsAssocie&&window.associeFraisAuto)?1:(jAbsorbe?0:1)" in html:
    print("4) deja present")
else:
    print("4) ATTENTION ligne frais posEncaisser non trouvee")

# 5) updatePosFrais : gerer le cas associe automatique
upf_anchor="var info=document.getElementById('posFraisInfo'); if(!info)return;"
if upf_anchor in html and "_isAssoc" not in html:
    inject=(upf_anchor
            +"var _isAssoc=(typeof posIsAssocie!=='undefined'&&posIsAssocie&&window.associeFraisAuto);"
            +"var _cb=document.getElementById('posRembFrais');"
            +"if(_cb){if(_isAssoc){_cb.checked=false;_cb.disabled=true;}else{_cb.disabled=false;}}"
            +"if(_isAssoc){var _rb=(typeof getRemb==='function')?getRemb():0;var _md=(document.getElementById('posMode')||{}).value||'';var _rt=(typeof FEES!=='undefined'&&FEES[_md])?FEES[_md]:0;"
            +"if(_rb>0&&_rt>0){var _fr=Math.round(_rb*_rt*100)/100;info.style.display='block';info.innerHTML='Associé : frais à sa charge (automatique)<br>Frais '+_md+' ('+(_rt*100).toFixed(0)+'%) = <strong>'+_fr.toFixed(2)+' EUR</strong><br>Crédité de <strong>'+(_rb-_fr).toFixed(2)+' EUR</strong>';}"
            +"else{info.style.display='none';info.innerHTML='';}return;}")
    html=html.replace(upf_anchor,inject,1)
    print("5) updatePosFrais gere l'associe automatique")
elif "_isAssoc" in html:
    print("5) deja present")
else:
    print("5) ATTENTION updatePosFrais non trouve")

# 6) JS : etat global + load/save du reglage
if "function loadAssocieFraisAuto" not in html:
    JS=r"""
<script>
// ===== REGLAGE FRAIS ASSOCIES =====
window.associeFraisAuto = true;
async function loadAssocieFraisAuto(){
  try{
    var res=await api('/api/settings');
    var data=(res&&res.ok)?res.data:null;
    var v='1';
    if(data){
      if(Array.isArray(data)){var f=data.find(function(x){return x.key==='associe_frais_auto';});if(f)v=String(f.value);}
      else if(data.associe_frais_auto!==undefined&&data.associe_frais_auto!==null){v=String(data.associe_frais_auto);}
    }
    window.associeFraisAuto=(v!=='0');
    var cb=document.getElementById('setAssocieFraisAuto');
    if(cb)cb.checked=window.associeFraisAuto;
  }catch(e){window.associeFraisAuto=true;}
}
async function saveAssocieFraisAuto(){
  var cb=document.getElementById('setAssocieFraisAuto');
  var val=(cb&&cb.checked)?'1':'0';
  window.associeFraisAuto=(val!=='0');
  try{await api('/api/settings',{method:'POST',body:{associe_frais_auto:val}});if(typeof notify==='function')notify('Reglage enregistre');}catch(e){if(typeof notify==='function')notify('Erreur','error');}
}
</script>
"""
    JS=JS.replace("\n",eol)
    pos=html.rfind("</script>")
    at=pos+len("</script>")
    html=html[:at]+eol+JS+html[at:]
    print("6) JS load/save reglage ajoute")
else:
    print("6) deja present")

io.open(p,"w",encoding="utf-8",newline="").write(html)
print("Balises script : %d / %d" % (html.count("<script>"),html.count("</script>")))
print("=== TERMINE ===")
