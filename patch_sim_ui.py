t=open("web/index.html",encoding="utf-8",newline="").read()
R=[]
def do(label, old, new, guard):
    global t
    if guard in t: R.append(label+": deja"); return
    if t.count(old)==1: t=t.replace(old,new,1); R.append(label+": OK")
    else: R.append(label+": KO("+str(t.count(old))+")")

a_modal='<div class="modal-bg" id="modalDetail" onclick="if(event.target===this)closeModal(\'detail\')">'
MSIM=('<div class="modal-bg" id="modalSim" onclick="if(event.target===this)simAnnuler()">'
'<div class="modal" style="max-width:420px"><div class="modal-title">Carte SIM</div>'
'<div class="modal-sub">Renseigne les infos de la puce</div><div style="margin:16px 0">'
'<label style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:1px">Numero de la puce</label>'
'<input id="simPuce" placeholder="Numero de la puce" style="width:100%;padding:10px 12px;margin:6px 0 14px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px">'
'<label style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:1px">4 derniers chiffres</label>'
'<input id="simLast4" inputmode="numeric" maxlength="4" placeholder="1234" style="width:100%;padding:10px 12px;margin:6px 0 0;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px">'
'</div><div class="modal-actions"><button class="btn" onclick="simAnnuler()">Annuler</button>'
'<button class="btn primary" onclick="simValider()">Valider</button></div></div></div>')
MPICK=('<div class="modal-bg" id="modalSimPick" onclick="if(event.target===this)simPickAnnuler()">'
'<div class="modal" style="max-width:460px"><div class="modal-title">Choisir la puce vendue</div>'
'<div class="modal-sub" id="simPickTitle"></div>'
'<div id="simPickList" style="margin:16px 0;max-height:340px;overflow-y:auto"></div>'
'<div class="modal-actions"><button class="btn" onclick="simPickAnnuler()">Annuler</button>'
'<button class="btn" onclick="simPickManuel()">Saisie manuelle</button></div></div></div>')
do("modals", a_modal, MSIM+MPICK+a_modal, 'id="modalSim"')

a_panel='<div class="form-group full"><label>Description</label><input type="text" id="catDescription" placeholder="Description courte..."></div>'
PANEL=('<div id="catSimPanel" class="form-group full" style="display:none;border-top:1px solid var(--border);margin-top:8px;padding-top:12px">'
'<label style="color:var(--gold2)">Puces SIM en stock</label>'
'<div id="catSimList" style="max-height:160px;overflow-y:auto;margin:6px 0"></div>'
'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end">'
'<div style="flex:2;min-width:140px"><input id="catSimNumero" placeholder="Numero de serie" style="width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text)"></div>'
'<div style="width:90px"><input id="catSimLast4" maxlength="4" inputmode="numeric" placeholder="4 chiffres" style="width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text)"></div>'
'<button class="btn primary" type="button" onclick="addSimUnit()">Ajouter</button></div>'
'<details style="margin-top:8px"><summary style="cursor:pointer;font-size:12px;color:var(--text3)">Ajouter plusieurs (liste collee)</summary>'
'<textarea id="catSimBulk" rows="4" placeholder="Une puce par ligne : numero,4derniers" style="width:100%;margin-top:6px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-family:DM Mono,monospace;font-size:12px"></textarea>'
'<button class="btn" type="button" onclick="addSimBulk()" style="margin-top:6px">Importer la liste</button></details></div>')
do("panel", a_panel, a_panel+PANEL, 'id="catSimPanel"')

a_js="/* auto-verification des mises a jour (apres connexion seulement) */"
JS=("""function askSimInfo(){return new Promise(function(resolve){var m=document.getElementById('modalSim');var p=document.getElementById('simPuce'),l=document.getElementById('simLast4');if(p)p.value='';if(l)l.value='';window._simResolve=resolve;if(m)m.classList.add('open');setTimeout(function(){if(p)p.focus();},60);});}
function simValider(){var p=((document.getElementById('simPuce')||{}).value||'').trim();var l=((document.getElementById('simLast4')||{}).value||'').trim();if(!p){notify('Numero de puce requis','error');return;}var m=document.getElementById('modalSim');if(m)m.classList.remove('open');if(window._simResolve){window._simResolve({puce:p,last4:l});window._simResolve=null;}}
function simAnnuler(){var m=document.getElementById('modalSim');if(m)m.classList.remove('open');if(window._simResolve){window._simResolve(null);window._simResolve=null;}}
function pickSim(units,nom){return new Promise(function(resolve){var m=document.getElementById('modalSimPick');var box=document.getElementById('simPickList');var ttl=document.getElementById('simPickTitle');if(ttl)ttl.textContent=(nom||'Carte SIM');window._simPickResolve=resolve;window._simPickUnits=units||[];var h='';(units||[]).forEach(function(u){h+='<div onclick="simPickChoose('+u.id+')" style="cursor:pointer;padding:12px 14px;border:1px solid var(--border);border-radius:10px;margin-bottom:8px;background:var(--bg3)"><div style="font-family:DM Mono,monospace;font-size:14px;color:var(--text)">'+(u.numero||'')+'</div><div style="font-size:12px;color:var(--text3)">4 derniers : '+((u.last4||'')||'-')+'</div></div>';});if(!(units||[]).length)h='<div style="color:var(--text3);padding:10px">Aucune puce en stock</div>';if(box)box.innerHTML=h;if(m)m.classList.add('open');});}
function simPickChoose(id){var u=(window._simPickUnits||[]).find(function(x){return x.id===id;});var m=document.getElementById('modalSimPick');if(m)m.classList.remove('open');if(window._simPickResolve){window._simPickResolve(u?{sim_id:u.id,puce:u.numero,last4:u.last4||''}:null);window._simPickResolve=null;}}
function simPickManuel(){var m=document.getElementById('modalSimPick');if(m)m.classList.remove('open');var r=window._simPickResolve;window._simPickResolve=null;askSimInfo().then(function(info){if(r)r(info);});}
function simPickAnnuler(){var m=document.getElementById('modalSimPick');if(m)m.classList.remove('open');if(window._simPickResolve){window._simPickResolve(null);window._simPickResolve=null;}}
function simPanelRefresh(id){var panel=document.getElementById('catSimPanel');if(!panel)return;var nom=((document.getElementById('catNom')||{}).value||'');if(!id||!/sim|puce/i.test(nom)){panel.style.display='none';return;}panel.style.display='block';loadSimUnits(id);}
async function loadSimUnits(id){var box=document.getElementById('catSimList');if(box)box.innerHTML='<div style="color:var(--text3);font-size:12px">Chargement...</div>';try{var r=await api('/api/sim-cards?catalogue_id='+id+'&statut=stock');var u=(r&&r.ok&&r.data&&r.data.cards)?r.data.cards:[];renderSimList(u);}catch(e){if(box)box.innerHTML='';}}
function renderSimList(units){var box=document.getElementById('catSimList');if(!box)return;if(!units.length){box.innerHTML='<div style="color:var(--text3);font-size:12px">Aucune puce en stock</div>';return;}var h='';units.forEach(function(u){h+='<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border:1px solid var(--border);border-radius:8px;margin-bottom:6px"><span style="font-family:DM Mono,monospace;font-size:13px">'+(u.numero||'')+' <span style="color:var(--text3)">('+((u.last4||'')||'-')+')</span></span><button class="btn" type="button" style="padding:2px 8px" onclick="deleteSimUnit('+u.id+')">x</button></div>';});box.innerHTML=h;}
async function addSimUnit(){var id=parseInt((document.getElementById('catId')||{}).value);if(!id){notify('Enregistre l article d abord','error');return;}var num=((document.getElementById('catSimNumero')||{}).value||'').trim();var l4=((document.getElementById('catSimLast4')||{}).value||'').trim();if(!num){notify('Numero requis','error');return;}var r=await api('/api/sim-cards',{method:'POST',body:{catalogue_id:id,numero:num,last4:l4}});if(r&&r.ok){document.getElementById('catSimNumero').value='';document.getElementById('catSimLast4').value='';loadSimUnits(id);if(typeof loadCatalogue==='function')loadCatalogue();notify('Puce ajoutee');}else notify('Erreur','error');}
async function addSimBulk(){var id=parseInt((document.getElementById('catId')||{}).value);if(!id){notify('Enregistre l article d abord','error');return;}var raw=((document.getElementById('catSimBulk')||{}).value||'');var lines=raw.split(String.fromCharCode(10));var items=[];for(var k=0;k<lines.length;k++){var clean=lines[k].split(String.fromCharCode(9)).join(',');var p=clean.split(/[,;]/);var numero=(p[0]||'').trim();var last4=(p[1]||'').trim();if(numero)items.push({numero:numero,last4:last4});}if(!items.length){notify('Liste vide','error');return;}var r=await api('/api/sim-cards',{method:'POST',body:{catalogue_id:id,items:items}});if(r&&r.ok){document.getElementById('catSimBulk').value='';loadSimUnits(id);if(typeof loadCatalogue==='function')loadCatalogue();notify(((r.data&&r.data.added)||0)+' puce(s) ajoutee(s)');}else notify('Erreur','error');}
async function deleteSimUnit(sid){var id=parseInt((document.getElementById('catId')||{}).value);var r=await api('/api/sim-cards/'+sid,{method:'DELETE'});if(r&&r.ok){loadSimUnits(id);if(typeof loadCatalogue==='function')loadCatalogue();}else notify('Erreur','error');}
""").replace("\n","\r\n")
do("jsfuncs", a_js, JS+a_js, "function askSimInfo()")

a_oe="document.getElementById('catModalTitle').textContent='Modifier l article';document.getElementById('btnDeleteCat').style.display='inline-flex';document.getElementById('modalCatalogue').classList.add('open');}"
do("hook_edit", a_oe, a_oe[:-1]+"simPanelRefresh(id);}", "simPanelRefresh(id);}")
a_on="document.getElementById('catModalTitle').textContent='Nouvel article';document.getElementById('btnDeleteCat').style.display='none';document.getElementById('modalCatalogue').classList.add('open');}"
do("hook_new", a_on, a_on[:-1]+"simPanelRefresh(0);}", "simPanelRefresh(0);}")

a_loop="// 1) Ventes (articles du panier)"
DET="var _simSel={};for(var _si=0;_si<posCart.length;_si++){var _sl=posCart[_si];if(!/sim|puce/i.test(_sl.nom||''))continue;var _picked=null,_units=[];if(_sl.id&&_sl.id>0){try{var _ur=await api('/api/sim-cards?catalogue_id='+_sl.id+'&statut=stock');_units=(_ur&&_ur.ok&&_ur.data&&_ur.data.cards)?_ur.data.cards:[];}catch(e){_units=[];}}if(_units.length){_picked=await pickSim(_units,_sl.nom);}else{_picked=await askSimInfo();}if(!_picked){btn.disabled=false;btn.textContent='Encaisser';notify('Vente annulee','error');return;}_simSel[_si]=_picked;}"
do("detect", a_loop, DET+a_loop, "var _simSel={};")
a_notes="+'Vente caisse',frais_deduits:0"
n_notes="+'Vente caisse'+(_simSel[i]?(' [SIM puce='+_simSel[i].puce+'|last4='+_simSel[i].last4+']'):''),frais_deduits:0"
do("notes", a_notes, n_notes, "[SIM puce='+_simSel[i].puce")
a_succ="if(r&&r.ok){ok++;if(r.data&&r.data.id)venteTids.push(r.data.id);}else fail++;}catch(e){fail++;}"
n_succ="if(r&&r.ok){ok++;if(r.data&&r.data.id)venteTids.push(r.data.id);if(_simSel[i]&&_simSel[i].sim_id&&r.data&&r.data.id){try{await api('/api/sim-cards/'+_simSel[i].sim_id+'/sold',{method:'POST',body:{transaction_id:r.data.id,client_id:cid,date:_posDate}});}catch(e){}}}else fail++;}catch(e){fail++;}"
do("marksold", a_succ, n_succ, "/sold',{method:'POST'")

a_cur="currentDetailId=id;"
PARSE=r"""currentDetailId=id;var _sim=null,_notesC=(t.notes||'');var _sm=_notesC.match(/\[SIM puce=([^|\]]*)\|last4=([^\]]*)\]/);if(_sm){_sim={puce:_sm[1],last4:_sm[2]};_notesC=_notesC.replace(_sm[0],'').replace(/\s{2,}/g,' ').trim();}"""
do("parse", a_cur, PARSE, "var _sim=null,_notesC=")
a_row="(t.notes&&t.notes.trim()?drRow('Notes',t.notes,'var(--text3)'):'')"
n_row="(_sim?drRow('Carte SIM','Puce '+_sim.puce+(_sim.last4?(' / 4 derniers '+_sim.last4):''),'var(--gold2)'):'')+(_notesC&&_notesC.trim()?drRow('Notes',_notesC,'var(--text3)'):'')"
do("detailrow", a_row, n_row, "drRow('Carte SIM'")

open("web/index.html","w",encoding="utf-8",newline="").write(t)
for r in R: print(r)

u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.20"' in u: print("ver: deja")
elif u.count('APP_VERSION = "2.19"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.19"','APP_VERSION = "2.20"',1)); print("ver -> 2.20")
else: print("ver KO")
