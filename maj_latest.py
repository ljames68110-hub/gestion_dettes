import re, json
src = open("updater.py", encoding="utf-8").read()
v = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', src).group(1).lstrip("v")
tag = "v" + v
data = {"version": tag,
        "asset_url": "https://github.com/ljames68110-hub/gestion_dettes/releases/download/" + tag + "/GestionPerso.exe",
        "sha256": None}
open("latest.json", "w", encoding="utf-8").write(json.dumps(data, indent=2))
print("latest.json ->", tag)
