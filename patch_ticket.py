t=open("web/index.html",encoding="utf-8",newline="").read()
R=[]
def do(label, old, new, guard):
    global t
    if guard in t: R.append(label+": deja"); return
    if t.count(old)==1: t=t.replace(old,new,1); R.append(label+": OK")
    else: R.append(label+": KO("+str(t.count(old))+")")

a1='<div id="posTabacQtyWrap"'
F1='<div id="posTicketWrap" style="display:none;margin-top:8px"><label style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:1px">Code du ticket</label><input id="posTicketCode" placeholder="Code PCS / Paysafecard" style="width:100%;padding:8px 10px;margin-top:4px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px"></div>'
do("field_pos", a1, F1+a1, 'id="posTicketCode"')
a2='<div id="depInfo"'
F2='<div id="depTicketWrap" style="display:none;margin-top:8px"><label style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:1px">Code du ticket</label><input id="depTicketCode" placeholder="Code PCS / Paysafecard" style="width:100%;padding:8px 10px;margin-top:4px;border-radius:8px;border:1px solid var(--border);background:var(--bg2);color:var(--text);font-size:14px"></div>'
do("field_dep", a2, F2+a2, 'id="depTicketCode"')
do("oc_pos", 'posModeChanged();updatePosTotals()', 'posModeChanged();updatePosTotals();posTicketToggle()', 'updatePosTotals();posTicketToggle()')
do("oc_dep", 'id="depMode" onchange="majDepotInfo()"', 'id="depMode" onchange="majDepotInfo();depTicketToggle()"', 'majDepotInfo();depTicketToggle()')
a_js="/* auto-verification des mises a jour (apres connexion seulement) */"
JS=("""function _isVoucher(v){return v==='PCS'||v==='Paysafecard';}
function posTicketToggle(){var w=document.getElementById('posTicketWrap');var v=_isVoucher((document.getElementById('posMode')||{}).value);if(w)w.style.display=v?'block':'none';if(!v){var c=document.getElementById('posTicketCode');if(c)c.value='';}}
function depTicketToggle(){var w=document.getElementById('depTicketWrap');var v=_isVoucher((document.getElementById('depMode')||{}).value);if(w)w.style.display=v?'block':'none';if(!v){var c=document.getElementById('depTicketCode');if(c)c.value='';}}
""").replace("\n","\r\n")
do("jsfuncs", a_js, JS+a_js, "function posTicketToggle()")
do("def_tag", "var mode=document.getElementById('posMode').value;", "var mode=document.getElementById('posMode').value;var _posTicketRaw=((document.getElementById('posTicketCode')||{}).value||'').trim();var _posTicketTag=_posTicketRaw?(' [TICKET code='+_posTicketRaw+']'):'';", "var _posTicketRaw=")
do("notes_vente", "+_simSel[i].last4+']'):''),frais_deduits:0", "+_simSel[i].last4+']'):'')+((modeVente==='PCS'||modeVente==='Paysafecard')?_posTicketTag:''),frais_deduits:0", "?_posTicketTag:''),frais_deduits:0")
do("notes_remb", "(posIsAssocie?'[CAISSE] Depot associe':'[CAISSE] Remboursement dette'),frais_deduits:", "(posIsAssocie?'[CAISSE] Depot associe':'[CAISSE] Remboursement dette')+((mode==='PCS'||mode==='Paysafecard')?_posTicketTag:''),frais_deduits:", "?_posTicketTag:''),frais_deduits:(")
do("def_dep", "value||'Liquide';var body={client_id:cid,type:'credit',motif:'Depot'", "value||'Liquide';var _depTicket=((md==='PCS'||md==='Paysafecard')?(((document.getElementById('depTicketCode')||{}).value||'').trim()):'');var _depTicketTag=_depTicket?(' [TICKET code='+_depTicket+']'):'';var body={client_id:cid,type:'credit',motif:'Depot'", "var _depTicket=")
do("notes_dep", "notes:'[CAISSE] Depot associe',frais_deduits:1", "notes:'[CAISSE] Depot associe'+_depTicketTag,frais_deduits:1", "Depot associe'+_depTicketTag")
a_parse=r"""_notesC=_notesC.replace(_sm[0],'').replace(/\s{2,}/g,' ').trim();}"""
n_parse=r"""_notesC=_notesC.replace(_sm[0],'').replace(/\s{2,}/g,' ').trim();}var _tk=null;var _tm=_notesC.match(/\[TICKET code=([^\]]*)\]/);if(_tm){_tk=_tm[1];_notesC=_notesC.replace(_tm[0],'').replace(/\s{2,}/g,' ').trim();}"""
do("parse_tk", a_parse, n_parse, "_notesC.match(/\\[TICKET")
do("row_tk", "+(_notesC&&_notesC.trim()?drRow('Notes',_notesC,'var(--text3)'):'')", "+(_tk?drRow('Code ticket',_tk,'var(--gold2)'):'')+(_notesC&&_notesC.trim()?drRow('Notes',_notesC,'var(--text3)'):'')", "drRow('Code ticket'")

open("web/index.html","w",encoding="utf-8",newline="").write(t)
for r in R: print(r)
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.22"' in u: print("ver: deja")
elif u.count('APP_VERSION = "2.21"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.21"','APP_VERSION = "2.22"',1)); print("ver -> 2.22")
else: print("ver KO")
