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

def req(method, url, token, data=None, ctype=None, timeout=30):
    h = {"Authorization":"Bearer "+token, "Accept":"application/vnd.github+json",
         "X-GitHub-Api-Version":"2022-11-28", "User-Agent":"gp-publisher"}
    if ctype: h["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            b = resp.read()
            return resp.status, (json.loads(b) if b else {})
    except urllib.error.HTTPError as e:
        b = e.read()
        try: b = json.loads(b)
        except: pass
        return e.code, b
    except (TimeoutError, OSError) as e:
        return 0, {"_timeout": True, "error": str(e)}

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
    print("Upload de l'exe en cours (%.1f Mo)... patiente 1-2 min, c'est normal." % (len(data)/1048576))
    st3, res = req("POST", url, token, data=data, ctype="application/octet-stream", timeout=300)
    if st3 in (200,201):
        print("\nOK ! Release", version, "publiee.")
        print("Lien:", res.get("browser_download_url",""))
        _maj_latest_json(token, version, res.get("browser_download_url",""), exe)
        print("Ton appli installee proposera la maj au prochain lancement.")
    elif isinstance(res, dict) and res.get("_timeout"):
        print("\nUpload trop long (timeout). La release existe deja : relance simplement")
        print("'python publier_release.py' -- il remplacera l'exe sans tout refaire.")
        sys.exit(1)
    else:
        print("Echec upload:", st3, res); sys.exit(1)


def _maj_latest_json(token, version, asset_url, exe_path):
    """Met a jour latest.json a la racine du depot (repli de l'updater) via
    l'API GitHub Contents. Non bloquant : un echec n'annule pas la publication."""
    import base64, hashlib
    try:
        h = hashlib.sha256()
        with open(exe_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        sha = h.hexdigest()
        contenu = json.dumps({"version": version, "asset_url": asset_url, "sha256": sha},
                             ensure_ascii=False, indent=2) + "\n"
        b64 = base64.b64encode(contenu.encode("utf-8")).decode("ascii")
        # sha du fichier existant (pour le remplacer) -- None si absent
        st, cur = req("GET", f"{API}/repos/{REPO}/contents/latest.json?ref=main", token)
        payload = {"message": "maj latest.json " + version,
                   "content": b64, "branch": "main"}
        if st == 200 and isinstance(cur, dict) and cur.get("sha"):
            payload["sha"] = cur["sha"]
        data = json.dumps(payload).encode()
        st2, res = req("PUT", f"{API}/repos/{REPO}/contents/latest.json", token,
                       data=data, ctype="application/json")
        if st2 in (200, 201):
            print("latest.json mis a jour (" + version + ", repli updater OK).")
        else:
            print("Avertissement : latest.json non mis a jour :", st2, res)
    except Exception as e:
        print("Avertissement : latest.json non mis a jour :", e)

if __name__ == "__main__":
    main()
