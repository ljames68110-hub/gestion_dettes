import re, json, hashlib, os

src = open("updater.py", encoding="utf-8").read()
v = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', src).group(1).lstrip("v")
tag = "v" + v

# sha256 de l'exe fraichement builde (IMPORTANT: lancer maj_latest.py APRES pyinstaller)
sha = None
exe = os.path.join("dist", "GestionPerso.exe")
if os.path.exists(exe):
    h = hashlib.sha256()
    with open(exe, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    sha = h.hexdigest()
    print("sha256:", sha)
else:
    print("ATTENTION: dist/GestionPerso.exe absent -> sha256 = null (as-tu build AVANT de lancer maj_latest ?)")

data = {"version": tag,
        "asset_url": "https://github.com/ljames68110-hub/gestion_dettes/releases/download/" + tag + "/GestionPerso.exe",
        "sha256": sha}
open("latest.json", "w", encoding="utf-8").write(json.dumps(data, indent=2))
print("latest.json ->", tag, "(sha256", "present" if sha else "null", ")")
