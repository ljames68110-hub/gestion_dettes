t=open("web/index.html",encoding="utf-8",newline="").read()

a_form='</div><div style="width:100px"><label style="font-size:11px;color:var(--text3)">Prix EUR</label><input id="flPrix"'
MOTIF_DIV='<div style="flex:2;min-width:140px"><label style="font-size:11px;color:var(--text3)">Motif (PDF)</label><input id="flMotif" placeholder="Motif (optionnel)" style="width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:14px"></div>'
if 'id="flMotif"' in t: print("form: deja")
elif t.count(a_form)==1: t=t.replace(a_form, '</div>'+MOTIF_DIV+a_form[6:],1); print("form: OK")
else: print("form: KO",t.count(a_form))

a_push="window.posLibreSeq-=1;posCart.push({id:window.posLibreSeq,nom:nom,prixVente:px,prixAchat:px,prix:px,qty:q,unite:'piece',libre:true});"
n_push="window.posLibreSeq-=1;var mtf=((document.getElementById('flMotif')||{}).value||'').trim();posCart.push({id:window.posLibreSeq,nom:nom,prixVente:px,prixAchat:px,prix:px,qty:q,unite:'piece',libre:true,motif:mtf});"
if "libre:true,motif:mtf" in t: print("push: deja")
elif t.count(a_push)==1: t=t.replace(a_push,n_push,1); print("push: OK")
else: print("push: KO",t.count(a_push))

a_enc="type:'debit',motif:l.nom,quantite:l.qty"
n_enc="type:'debit',motif:(l.motif&&l.motif.length?l.motif:l.nom),quantite:l.qty"
if "motif:(l.motif&&l.motif.length?l.motif:l.nom)" in t: print("enc: deja")
elif t.count(a_enc)==1: t=t.replace(a_enc,n_enc,1); print("enc: OK")
else: print("enc: KO",t.count(a_enc))

a_tog="var qq=document.getElementById('flQty');if(qq)qq.value='1';"
n_tog="var qq=document.getElementById('flQty');if(qq)qq.value='1';var mm=document.getElementById('flMotif');if(mm)mm.value='';"
if "getElementById('flMotif');if(mm)" in t: print("tog: deja")
elif t.count(a_tog)==1: t=t.replace(a_tog,n_tog,1); print("tog: OK")
else: print("tog: KO",t.count(a_tog))

open("web/index.html","w",encoding="utf-8",newline="").write(t)
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.19"' in u: print("ver: deja")
elif u.count('APP_VERSION = "2.18"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.18"','APP_VERSION = "2.19"',1)); print("ver -> 2.19")
else: print("ver KO")
