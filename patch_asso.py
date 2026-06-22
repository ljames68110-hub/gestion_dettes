NL="\r\n"
t=open("web/index.html",encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in t else "\n"
PANEL='<div id="posAssociePanel" style="display:none;margin-top:8px;padding:12px;background:var(--bg3);border:1px solid var(--gold);border-radius:var(--radius2)"><div style="font-size:11px;color:var(--gold2);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Comptes associe</div><div style="display:flex;gap:8px;margin-bottom:10px"><div style="flex:1;background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:8px;text-align:center"><div style="font-size:11px;color:var(--text3)">\U0001f4b3 Dette</div><div id="assoDette" style="font-size:16px;font-weight:600;color:var(--red)">0.00 EUR</div></div><div style="flex:1;background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:8px;text-align:center"><div style="font-size:11px;color:var(--text3)">\U0001f4b0 Depot</div><div id="assoDepot" style="font-size:16px;font-weight:600;color:var(--green)">0.00 EUR</div></div></div><button class="btn" style="width:100%;margin-bottom:6px" onclick="toggleRetraitForm()">\U0001f4b8 Retrait (reprendre du depot)</button><div id="posRetraitForm" style="display:none;margin-bottom:6px;flex-direction:column;gap:6px"><input type="number" id="retMontant" step="0.5" min="0" placeholder="Montant retire" style="padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg2);color:var(--text);font-size:14px"><button class="btn primary" style="width:100%" onclick="validerRetrait()">Valider le retrait</button></div><div id="assoReglerWrap" style="display:none"><button class="btn" style="width:100%;border:1px solid var(--gold);color:var(--gold2)" onclick="reglerDetteAssocie()">\u2713 Regler la dette (<span id="assoReglerMontant">0</span> EUR)</button></div></div>'
FUNCS=[
"function renderAssoCards(solde){var dette=solde>0?solde:0;var depot=solde<0?-solde:0;var d=document.getElementById('assoDette');if(d)d.textContent=dette.toFixed(2)+' EUR';var dp=document.getElementById('assoDepot');if(dp)dp.textContent=depot.toFixed(2)+' EUR';var rw=document.getElementById('assoReglerWrap');if(rw)rw.style.display=dette>0?'block':'none';var rm=document.getElementById('assoReglerMontant');if(rm)rm.textContent=dette.toFixed(2);}",
"function toggleRetraitForm(){var f=document.getElementById('posRetraitForm');if(!f)return;var show=(f.style.display==='none'||!f.style.display);f.style.display=show?'flex':'none';if(show){var m=document.getElementById('retMontant');if(m){m.value='';m.focus();}}}",
"async function validerRetrait(){var cid=parseInt((document.getElementById('posClient')||{}).value);if(!cid){notify('Choisis un associe','error');return;}var m=parseFloat(((document.getElementById('retMontant')||{}).value||'0').replace(',','.'))||0;if(m<=0){notify('Montant invalide','error');return;}var body={client_id:cid,type:'debit',motif:'Retrait',quantite:1,unite:'piece',prix_unitaire:m,mode_paiement:'Liquide',notes:'[CAISSE] Retrait associe',compte:'euro'};var _d=(document.getElementById('posDate')||{}).value;if(_d)body.date=_d;try{var r=await api('/api/transactions',{method:'POST',body:body});if(r&&r.ok){notify('Retrait enregistre : '+m.toFixed(2)+' EUR');var f=document.getElementById('posRetraitForm');if(f)f.style.display='none';onPosClientChange();}else{notify('Echec retrait','error');}}catch(e){notify('Erreur retrait','error');}}",
"async function reglerDetteAssocie(){var cid=parseInt((document.getElementById('posClient')||{}).value);if(!cid){notify('Choisis un associe','error');return;}var dette=(typeof posDette!=='undefined'&&posDette>0)?posDette:0;if(dette<=0){notify('Aucune dette a regler','error');return;}if(!confirm('Regler la dette de '+dette.toFixed(2)+' EUR ?'))return;var body={client_id:cid,type:'credit',motif:'Reglement dette',quantite:1,unite:'piece',prix_unitaire:dette,mode_paiement:'Liquide',notes:'[CAISSE] Reglement dette associe',frais_deduits:0,compte:'euro'};var _d=(document.getElementById('posDate')||{}).value;if(_d)body.date=_d;try{var r=await api('/api/transactions',{method:'POST',body:body});if(r&&r.ok){notify('Dette reglee');onPosClientChange();}else{notify('Echec','error');}}catch(e){notify('Erreur','error');}}",
]
FUNCBLOB=eol.join(FUNCS)
E=[
("payzone",'<div class="pos-pay">','<div class="pos-pay" id="posPayZone">','id="posPayZone"'),
("panel",'onclick="validerDepot()">Valider le depot</button></div></div>','onclick="validerDepot()">Valider le depot</button></div></div>'+PANEL,'id="posAssociePanel"'),
("onclient",
 "if(posIsAssocie){if(_rrow)_rrow.style.display='none';if(_albl)_albl.style.display='none';if(_dz)_dz.style.display='block';}else{if(_rrow)_rrow.style.display='flex';if(_albl)_albl.style.display='flex';if(_dz){_dz.style.display='none';var _df=document.getElementById('posDepotForm');if(_df)_df.style.display='none';}}",
 "if(posIsAssocie){if(_rrow)_rrow.style.display='none';if(_albl)_albl.style.display='none';if(_dz)_dz.style.display='block';var _ap=document.getElementById('posAssociePanel');if(_ap)_ap.style.display='block';var _pz=document.getElementById('posPayZone');if(_pz)_pz.style.display='none';}else{if(_rrow)_rrow.style.display='flex';if(_albl)_albl.style.display='flex';if(_dz){_dz.style.display='none';var _df=document.getElementById('posDepotForm');if(_df)_df.style.display='none';}var _ap=document.getElementById('posAssociePanel');if(_ap)_ap.style.display='none';var _pz=document.getElementById('posPayZone');if(_pz)_pz.style.display='';}",
 "getElementById('posAssociePanel')"),
("solde",
 "posDette = (res&&res.ok&&res.data)?(parseFloat(res.data.solde)||0):0;",
 "posDette = (res&&res.ok&&res.data)?(parseFloat(res.data.solde)||0):0;if(posIsAssocie&&typeof renderAssoCards==='function')renderAssoCards(posDette);",
 "renderAssoCards(posDette)"),
("funcs",
 "/* auto-verification des mises a jour (apres connexion seulement) */",
 FUNCBLOB+eol+"/* auto-verification des mises a jour (apres connexion seulement) */",
 "function renderAssoCards"),
]
for name,o,n,guard in E:
    if guard in t: print(name,": deja"); continue
    if t.count(o)==1: t=t.replace(o,n,1); print(name,": OK")
    else: print(name,": KO",t.count(o))
open("web/index.html","w",encoding="utf-8",newline="").write(t)
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.16"' in u: print("ver: deja")
elif u.count('APP_VERSION = "2.15"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.15"','APP_VERSION = "2.16"',1)); print("ver -> 2.16")
else: print("ver KO")
