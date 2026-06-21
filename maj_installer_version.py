import re
u = open("updater.py", encoding="utf-8", newline="").read()
m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', u)
if not m:
    print("version introuvable dans updater.py")
else:
    ver = m.group(1)
    s = open("installer.iss", encoding="utf-8", newline="").read()
    if '#define AppVersion "' not in s:
        print("ligne AppVersion introuvable dans installer.iss")
    else:
        new = re.sub(r'(#define AppVersion ")[^"]*(")', lambda mm: mm.group(1)+ver+mm.group(2), s, count=1)
        open("installer.iss", "w", encoding="utf-8", newline="").write(new)
        print("installer.iss AppVersion ->", ver)
