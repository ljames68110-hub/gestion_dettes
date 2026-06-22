import re
t=open("web/index.html",encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in t else "\n"
R=[]
def do(label, old, new, guard, n=1):
    global t
    if guard in t: R.append(label+": deja"); return
    if t.count(old)==n: t=t.replace(old,new); R.append(label+": OK"+("(x%d)"%n if n>1 else ""))
    else: R.append(label+": KO("+str(t.count(old))+")")

do("getCartTotal", "t+=l.prix*l.qty;", "t+=(l.gratuit?0:l.prix)*l.qty;", "(l.gratuit?0:l.prix)*l.qty", 1)
do("sub", "var sub=l.prix*l.qty;", "var sub=(l.gratuit?0:l.prix)*l.qty;", "var sub=(l.gratuit?0", 2)
do("price", "'+l.prix.toFixed(2)+' EUR</span></div>", "'+(l.gratuit?'Gratuit':l.prix.toFixed(2)+' EUR')+'</span></div>", "?'Gratuit':l.prix.toFixed", 2)
gold='\'+sub.toFixed(2)+\'</div><button class="ldel" onclick="posRemove(\'+l.id+\')">x</button>'
gnew='\'+sub.toFixed(2)+\'</div>\'+\'<button onclick="posToggleGratuit(\'+l.id+\')" style="border:1px solid var(--border);border-radius:6px;padding:2px 8px;font-size:11px;cursor:pointer;margin-right:4px;background:transparent;color:\'+(l.gratuit?\'var(--gold2)\':\'var(--text3)\')+\'">\'+(l.gratuit?\'Gratuit\':\'Offrir\')+\'</button>\'+\'<button class="ldel" onclick="posRemove(\'+l.id+\')">x</button>'
do("giftbtn", gold, gnew, "posToggleGratuit(", 2)

a_js="/* auto-verification des mises a jour (apres connexion seulement) */"
JS=("""function posToggleGratuit(id){var l=posCart.find(function(x){return x.id===id;});if(!l)return;l.gratuit=!l.gratuit;renderPosCart();updatePosTotals();}
async function getConsoPersoClient(){var f=(clientsCache||[]).find(function(c){return (c.nom||'').toLowerCase()==='conso perso';});if(f)return f.id;var r=await api('/api/clients',{method:'POST',body:{nom:'Conso perso'}});if(r&&r.ok&&r.data){if(typeof loadClients==='function'){try{await loadClients();}catch(e){}}return r.data.id;}return null;}
""").replace("\n","\r\n")
do("jsfuncs", a_js, JS+a_js, "function posToggleGratuit(", 1)

do("checkbox", '<button class="pos-cashout" id="posCashout"', '<label style="display:flex;align-items:center;gap:8px;margin:8px 0;font-size:13px;color:var(--text3);cursor:pointer"><input type="checkbox" id="posConsoPerso" onchange="updatePosTotals()"> Conso perso (pour moi, 0 EUR, sort du stock)</label><button class="pos-cashout" id="posCashout"', 'id="posConsoPerso"', 1)

a_cid="var cid=parseInt(document.getElementById('posClient').value);"+eol+"  if(!cid){notify('Choisis un client','error');return;}"
n_cid="var cid=parseInt(document.getElementById('posClient').value);"+eol+"  var _conso=!!((document.getElementById('posConsoPerso')||{}).checked);if(_conso){cid=await getConsoPersoClient();if(!cid){notify('Erreur client Conso perso','error');return;}}"+eol+"  if(!cid){notify('Choisis un client','error');return;}"
do("cidcheck", a_cid, n_cid, "var _conso=", 1)

do("prix", "prix_unitaire:Math.round(l.prix*facteurReduc*100)/100", "prix_unitaire:((l.gratuit||_conso)?0:Math.round(l.prix*facteurReduc*100)/100)", "(l.gratuit||_conso)?0", 1)
do("notes", "?_posTicketTag:''),frais_deduits:0", "?_posTicketTag:'')+(l.gratuit?' [GRATUIT]':'')+(_conso?' [CONSO PERSO]':''),frais_deduits:0", "[GRATUIT]':'')+(_conso", 1)
do("reset", "posCart=[];var _pr=", "posCart=[];var _cpx=document.getElementById('posConsoPerso');if(_cpx)_cpx.checked=false;var _pr=", "var _cpx=document.getElementById('posConsoPerso')", 2)

open("web/index.html","w",encoding="utf-8",newline="").write(t)
for r in R: print(r)
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.24"' in u: print("ver: deja")
else:
    u2=re.sub(r'APP_VERSION = "2\.2[0-3]"','APP_VERSION = "2.24"',u,count=1)
    if u2!=u: open("updater.py","w",encoding="utf-8",newline="").write(u2); print("ver -> 2.24")
    else: print("ver KO")
