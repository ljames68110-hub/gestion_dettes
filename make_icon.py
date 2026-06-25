# Convertit une image (png/jpg) en app_icon.ico multi-tailles.
# Usage : python make_icon.py mon_logo.png
import sys
from PIL import Image
src = sys.argv[1] if len(sys.argv) > 1 else "logo.png"
img = Image.open(src).convert("RGBA")
img.save("app_icon.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("app_icon.ico cree depuis", src)
