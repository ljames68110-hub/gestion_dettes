import os, sys, json, urllib.request, urllib.error, getpass, re
REPO = "ljames68110-hub/gestion_dettes"
API  = "https://api.github.com"
ASSET = "GestionPerso.exe"
HERE = os.path.dirname(os.path.abspath(__file__))

def read_version():
    txt = open(os.path.join(HERE, "updater.py"), encoding="utf-8", errors="replace").read()
    m = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', txt)
    if not m: print("APP_VERSION introuvable dans updater.py"); sys.exit(1)
    return m.group(1)

def req(method, url, token, data=None, ctype=None):
    h = {"Authorization":"Bearer "+token, "Accept":"application/vnd.github+json",
         "X-GitHub-Api-Version":"2022-11-28", "User-Agent":"gp-publisher"}
    if ctype: h["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r) as resp:
            b = resp.read()
            return resp.status, (json.loads(b) if b else {})
    except urllib.error.HTTPError as e:
        b = e.read()
        try: b = json.loads(b)
        except: pass
        return e.code, b

def main():
    version = read_version(); tag = "v"+version
    print("Version a publier:", version, "  (tag", tag+")")
    exe = os.path.join(HERE, "dist", ASSET)
    if not os.path.exists(exe): print("Introuvable:", exe); sys.exit(1)
    print("Fichier:", exe, "(", round(os.path.getsize(exe)/1048576,1), "Mo )")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token: token = getpass.getpass("Colle ton token GitHub: ").strip()
    if not token or token == "ton_token": print("Token invalide."); sys.exit(1)

    st, rel = req("GET", f"{API}/repos/{REPO}/releases/tags/{tag}", token)
    if st == 200:
        print("Release existante reutilisee.")
    elif st == 404:
        payload = json.dumps({"tag_name":tag, "target_commitish":"main",
            "name":"Gestion Perso "+version, "body":"Version "+version,
            "draft":False, "prerelease":False}).encode()
        st2, rel = req("POST", f"{API}/repos/{REPO}/releases", token, data=payload, ctype="application/json")
        if st2 not in (200,201): print("Echec creation release:", st2, rel); sys.exit(1)
        print("Release creee.")
    elif st == 401:
        print("401 - token refuse (il faut le droit Contents: Read and write)."); sys.exit(1)
    else:
        print("Erreur:", st, rel); sys.exit(1)

    for a in rel.get("assets", []):
        if a.get("name") == ASSET:
            req("DELETE", f"{API}/repos/{REPO}/releases/assets/{a['id']}", token)
            print("Ancien .exe remplace.")
    rel_id = rel["id"]
    with open(exe, "rb") as f: data = f.read()
    url = "https://uploads.github.com/repos/%s/releases/%d/assets?name=%s" % (REPO, rel_id, ASSET)
    st3, res = req("POST", url, token, data=data, ctype="application/octet-stream")
    if st3 in (200,201):
        print("\nOK ! Release", version, "publiee.")
        print("Lien:", res.get("browser_download_url",""))
        print("Ton appli installee proposera la maj au prochain lancement.")
    else:
        print("Echec upload:", st3, res); sys.exit(1)

if __name__ == "__main__":
    main()
