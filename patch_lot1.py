t=open("web/index.html",encoding="utf-8",newline="").read()
R=[]
po='<option value="Paysafecard">Paysafecard</option>'
pn='<option value="Paysafecard">Paysafecard</option><option value="Transcash">Transcash</option>'
if 'value="Transcash"' in t: R.append("transcash: deja")
elif t.count(po)==2: t=t.replace(po,pn); R.append("transcash: OK (x2)")
else: R.append("transcash: KO("+str(t.count(po))+")")

vo="function _isVoucher(v){return v==='PCS'||v==='Paysafecard';}"
vn="function _isVoucher(v){return v==='PCS'||v==='Paysafecard'||v==='Transcash'||v==='WesternUnion';}"
if "v==='Transcash'" in t: R.append("voucher: deja")
elif t.count(vo)==1: t=t.replace(vo,vn,1); R.append("voucher: OK")
else: R.append("voucher: KO")

if "max-width:780px" in t: R.append("modal_w: deja")
elif t.count("max-width:520px")==1: t=t.replace("max-width:520px","max-width:780px",1); R.append("modal_w: OK")
else: R.append("modal_w: KO("+str(t.count('max-width:520px'))+")")

a_js="/* auto-verification des mises a jour (apres connexion seulement) */"
ZJS="function zoomTile(el){var im=el.parentNode.querySelector('img');if(im&&typeof openPhotoLightbox==='function')openPhotoLightbox(im.src);}\r\n"
if "function zoomTile(" in t: R.append("zoomfn: deja")
elif t.count(a_js)==1: t=t.replace(a_js, ZJS+a_js,1); R.append("zoomfn: OK")
else: R.append("zoomfn: KO")

to="(it.photo?'<img src=\"'+it.photo+'\">':'<span class=\"pprod-ph\">\U0001F4E6</span>')"
tn="(it.photo?'<img src=\"'+it.photo+'\"><span onclick=\"event.stopPropagation();zoomTile(this)\" style=\"position:absolute;top:6px;left:6px;background:rgba(0,0,0,0.6);color:#fff;border-radius:6px;padding:1px 7px;font-size:14px;cursor:pointer;z-index:3\">&#128269;</span>':'<span class=\"pprod-ph\">\U0001F4E6</span>')"
if "zoomTile(this)" in t: R.append("zoombtn: deja")
elif t.count(to)==1: t=t.replace(to,tn,1); R.append("zoombtn: OK")
else: R.append("zoombtn: KO("+str(t.count(to))+")")

open("web/index.html","w",encoding="utf-8",newline="").write(t)
for r in R: print(r)
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.23"' in u: print("ver: deja")
elif u.count('APP_VERSION = "2.22"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.22"','APP_VERSION = "2.23"',1)); print("ver -> 2.23")
else: print("ver KO")
