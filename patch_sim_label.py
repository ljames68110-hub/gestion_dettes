t=open("web/index.html",encoding="utf-8",newline="").read()
R=[]
def do2(label, old, new):
    global t
    if old not in t: R.append(label+": deja"); return
    if t.count(old)==1: t=t.replace(old,new,1); R.append(label+": OK")
    else: R.append(label+": KO("+str(t.count(old))+")")

do2("modal_label",'>Numero de la puce</label>','>Numero de telephone</label>')
do2("modal_ph",'placeholder="Numero de la puce"','placeholder="Numero de telephone"')
do2("modal_4d",'>4 derniers chiffres</label>','>4 derniers chiffres (n. serie)</label>')
do2("modal_sub",'<div class="modal-sub">Renseigne les infos de la puce</div>','<div class="modal-sub">Tel + 4 derniers du n. serie</div>')
do2("cat_ph",'placeholder="Numero de serie"','placeholder="Numero de telephone"')
do2("cat_4ch",'placeholder="4 chiffres"','placeholder="4 ch. serie"')
do2("textarea",'placeholder="Une puce par ligne : numero,4derniers"','placeholder="Une SIM par ligne : telephone,4derniers-serie"')
do2("picker","4 derniers : '+((u.last4||'')||'-')","4 derniers serie : '+((u.last4||'')||'-')")
do2("renderlist","('+((u.last4||'')||'-')+')","(serie '+((u.last4||'')||'-')+')")
do2("detail","'Puce '+_sim.puce+(_sim.last4?(' / 4 derniers '+_sim.last4)","'Tel '+_sim.puce+(_sim.last4?(' / 4 derniers serie '+_sim.last4)")

open("web/index.html","w",encoding="utf-8",newline="").write(t)
for r in R: print(r)

u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.21"' in u: print("ver: deja")
elif u.count('APP_VERSION = "2.20"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.20"','APP_VERSION = "2.21"',1)); print("ver -> 2.21")
else: print("ver KO")
