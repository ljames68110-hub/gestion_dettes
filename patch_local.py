NL="\r\n"
a=open("api.py",encoding="utf-8",newline="").read()
route=NL.join([
'@app.route("/api/update/apply-local", methods=["POST"])',
'@require_auth',
'def update_apply_local():',
'    """Met a jour depuis un fichier .exe fourni (sans telechargement reseau)."""',
'    if not HAS_UPDATER:',
'        return err("updater non disponible")',
'    data = request.json or {}',
'    b64 = data.get("data") or ""',
'    if not b64:',
'        return err("Aucun fichier recu")',
'    exe = updater.get_current_exe()',
'    if not exe:',
'        return err("Mode dev : pas d\'exe a remplacer")',
'    import base64, tempfile, threading, time',
'    try:',
'        raw = base64.b64decode(b64)',
'        if len(raw) < 1000000:',
'            return err("Fichier trop petit (pas un .exe ?)")',
'        tmp = tempfile.NamedTemporaryFile(suffix=".exe", dir=exe.parent, delete=False)',
'        tmp.write(raw); tmp.close()',
'        updater.apply_update_windows(tmp.name, str(exe))',
'    except Exception as e:',
'        return err("Echec : " + str(e))',
'    def _bye():',
'        time.sleep(2); os._exit(0)',
'    threading.Thread(target=_bye, daemon=True).start()',
'    return ok({"message": "Mise a jour depuis le fichier, redemarrage..."})',
'','',''])
anchor='def start(host="127.0.0.1", port=5000, debug=False):'
if "apply-local" in a: print("api route: deja")
elif a.count(anchor)==1: a=a.replace(anchor, route+anchor,1); print("api route: OK")
else: print("api route: KO", a.count(anchor))
open("api.py","w",encoding="utf-8",newline="").write(a)
import py_compile; py_compile.compile("api.py",doraise=True); print("py_compile api OK")
t=open("web/index.html",encoding="utf-8",newline="").read()
eol="\r\n" if "\r\n" in t else "\n"
btn_o='<button class="btn-cancel" onclick="closeModal(\'update\')">Fermer</button>'
btn_n=btn_o+'<button class="btn-save" id="btnLocalUpdate" onclick="pickLocalUpdate()">\U0001f4c1 Depuis un fichier</button><input type="file" id="updLocalFile" accept=".exe" style="display:none" onchange="applyLocalUpdate(this)">'
if 'id="btnLocalUpdate"' in t: print("html bouton: deja")
elif t.count(btn_o)==1: t=t.replace(btn_o,btn_n,1); print("html bouton: OK")
else: print("html bouton: KO", t.count(btn_o))
F1="function pickLocalUpdate(){var i=document.getElementById('updLocalFile');if(i){i.value='';i.click();}}"
F2="async function applyLocalUpdate(input){if(!input.files||!input.files[0])return;var f=input.files[0];var btn=document.getElementById('btnLocalUpdate');if(btn){btn.textContent='Lecture du fichier...';btn.disabled=true;}try{var b64=await new Promise(function(res,rej){var rd=new FileReader();rd.onload=function(){res(String(rd.result).split(',')[1]);};rd.onerror=function(){rej(new Error('lecture'));};rd.readAsDataURL(f);});if(btn)btn.textContent='Installation...';var r=await api('/api/update/apply-local',{method:'POST',body:{data:b64}});if(r&&r.ok){notify('Installation lancee, redemarrage dans quelques secondes');}else{notify((r&&(r.error||r.message))||'Echec de la mise a jour','error');if(btn){btn.textContent='\U0001f4c1 Depuis un fichier';btn.disabled=false;}}}catch(e){notify('Erreur : '+e,'error');if(btn){btn.textContent='\U0001f4c1 Depuis un fichier';btn.disabled=false;}}}"
anc="/* auto-verification des mises a jour (apres connexion seulement) */"
if "function pickLocalUpdate" in t: print("html funcs: deja")
elif t.count(anc)==1: t=t.replace(anc, F1+eol+F2+eol+anc,1); print("html funcs: OK")
else: print("html funcs: KO", t.count(anc))
open("web/index.html","w",encoding="utf-8",newline="").write(t)
u=open("updater.py",encoding="utf-8",newline="").read()
if 'APP_VERSION = "2.15"' in u: print("ver: deja 2.15")
elif u.count('APP_VERSION = "2.14"')==1: open("updater.py","w",encoding="utf-8",newline="").write(u.replace('APP_VERSION = "2.14"','APP_VERSION = "2.15"',1)); print("ver -> 2.15")
else: print("ver KO")
