# -*- coding: utf-8 -*-
"""Lecture OCR locale d'un ticket (PCS/Paysafecard) via Tesseract.
Pre-remplissage uniquement : l'utilisateur verifie toujours."""
import base64, io, os, re

try:
    import pytesseract
    from PIL import Image, ImageOps, ImageFilter
    _OCR_OK = True
except Exception:
    _OCR_OK = False

# Chemin Tesseract installe sous Windows (installeur UB Mannheim)
_TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if _OCR_OK and os.path.exists(_TESS):
    pytesseract.pytesseract.tesseract_cmd = _TESS

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

def _ocr_text(img, lang):
    try:
        return pytesseract.image_to_string(img, lang=lang, config="--psm 6")
    except Exception:
        return ""

def lire_ticket(photo, lang="fra"):
    if not _OCR_OK:
        return {"ok": False, "error": "OCR indisponible (pytesseract/Pillow manquants)"}
    try:
        img = _preprocess(_to_image(photo))
    except Exception:
        return {"ok": False, "error": "Image illisible"}
    txt = _ocr_text(img, lang) or _ocr_text(img, "eng")
    if not txt.strip():
        return {"ok": False, "error": "Aucun texte detecte (photo trop floue ?)"}
    up = txt.upper()
    lines = up.splitlines()

    # Montant
    montant = ""
    m = re.search(r'CR[E\u00c9]DIT\s*[:\-]?\s*([0-9]+(?:[.,][0-9]{1,2})?)', up)
    if m:
        montant = m.group(1).replace(",", ".")

    # Numero de serie
    serie = ""
    m = re.search(r'(?:N[O0]\.?\s*S[E\u00c9]RIE)\s*[:\-]?\s*([0-9][0-9 ]{6,})', up)
    if m:
        serie = re.sub(r'\s+', '', m.group(1))

    # Code secret : ligne alphanumerique (lettres+chiffres) apres "SECRET"
    _SKIP = ("ESPACE","DERNIERS","CHIFFRES","CARTE","EX","RECH","NUMERO","SMS")
    def good(tok):
        return (8 <= len(tok) <= 12 and tok not in _BL
                and len(re.findall(r'[A-Z]', tok)) >= 3
                and re.search(r'[0-9]', tok) and "RECH" not in tok)
    code = ""
    for i, line in enumerate(lines):
        if "SECRET" in line:
            for j in range(i+1, min(i+3, len(lines))):
                lj = lines[j]
                if any(k in lj for k in _SKIP):
                    continue
                for tok in re.findall(r'\b[A-Z0-9]{8,12}\b', lj):
                    if good(tok):
                        code = tok; break
                if code: break
        if code: break

    return {"ok": True, "code": code, "serie": serie, "montant": montant}
