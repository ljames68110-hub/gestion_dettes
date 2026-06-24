# -*- coding: utf-8 -*-
"""Lecture OCR locale d'un ticket (PCS/Paysafecard) via Tesseract.
Pre-remplissage uniquement : l'utilisateur verifie toujours."""
import base64, io, os, re, shutil

try:
    import pytesseract
    from PIL import Image, ImageOps, ImageFilter
    _OCR_OK = True
except Exception:
    _OCR_OK = False

# Localisation de tesseract.exe (plusieurs emplacements possibles + PATH)
_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
]
if _OCR_OK:
    _found = next((c for c in _CANDIDATES if os.path.exists(c)), None) or shutil.which("tesseract")
    if _found:
        pytesseract.pytesseract.tesseract_cmd = _found

_BL = {"INFORMATIONS","JOIGNABLE","SEULEMENT","UNIQUEMENT","RECHARGEZ","DERNIERS",
       "CHIFFRES","TRANSACTION","REMBOURSABLE","TRANSFERABLE","EXCLUSIVEMENT",
       "UTILISABLE","ENREGISTRE","ELECTRONIQUE","COMMISSIONS","VERIFIER","MONAVATE"}

def _to_image(photo):
    if "," in photo:
        photo = photo.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(photo)))

def _preprocess(img):
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    w, h = g.size
    g = g.resize((w*2, h*2), Image.LANCZOS).filter(ImageFilter.SHARPEN)
    return g

def lire_ticket(photo, lang="fra"):
    if not _OCR_OK:
        return {"ok": False, "error": "OCR indisponible (pytesseract/Pillow manquants)"}
    # Tesseract est-il joignable ?
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return {"ok": False, "error": "Tesseract introuvable. Installe-le et garde le chemin C:\\Program Files\\Tesseract-OCR"}
    try:
        img = _preprocess(_to_image(photo))
    except Exception:
        return {"ok": False, "error": "Image illisible"}
    # OCR : francais puis repli anglais, en capturant la vraie erreur
    txt, err = "", ""
    for lg in (lang, "eng"):
        try:
            txt = pytesseract.image_to_string(img, lang=lg, config="--psm 6")
            if txt.strip():
                break
        except Exception as e:
            err = str(e)
    if not txt.strip():
        if err:
            return {"ok": False, "error": ("Tesseract: " + err)[:140]}
        return {"ok": False, "error": "Aucun texte detecte (photo trop floue ?)"}

    up = txt.upper()
    lines = up.splitlines()

    montant = ""
    m = re.search(r'CR[E\u00c9]DIT\s*[:\-]?\s*([0-9]+(?:[.,][0-9]{1,2})?)', up)
    if m:
        montant = m.group(1).replace(",", ".")

    serie = ""
    m = re.search(r'(?:N[O0]\.?\s*S[E\u00c9]RIE)\s*[:\-]?\s*([0-9][0-9 ]{6,})', up)
    if m:
        serie = re.sub(r'\s+', '', m.group(1))

    _SKIP = ("ESPACE","DERNIERS","CHIFFRES","CARTE","EX","RECH","NUMERO","SMS")
    def good(tok):
        return (8 <= len(tok) <= 12 and tok not in _BL
                and len(re.findall(r'[A-Z]', tok)) >= 3
                and re.search(r'[0-9]', tok) and "RECH" not in tok)
    code = ""
    for i, line in enumerate(lines):
        if "SECRET" in line:
            for j in range(i+1, min(i+3, len(lines))):
                if any(k in lines[j] for k in _SKIP):
                    continue
                for tok in re.findall(r'\b[A-Z0-9]{8,12}\b', lines[j]):
                    if good(tok):
                        code = tok; break
                if code: break
        if code: break

    return {"ok": True, "code": code, "serie": serie, "montant": montant}
