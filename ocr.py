# -*- coding: utf-8 -*-
"""Lecture OCR locale d'un ticket (PCS/Paysafecard/Transcash) via Tesseract.
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

def lire_ticket(photo, lang="fra", hint=""):
    if not _OCR_OK:
        return {"ok": False, "error": "OCR indisponible (pytesseract/Pillow manquants)"}
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return {"ok": False, "error": "Tesseract introuvable. Installe-le et garde le chemin C:\\Program Files\\Tesseract-OCR"}
    try:
        img = _preprocess(_to_image(photo))
    except Exception:
        return {"ok": False, "error": "Image illisible"}
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
    lines = [l for l in up.splitlines() if l.strip()]

    # --- type de ticket (indice du mode choisi, sinon detection texte elargie) ---
    hint_l = (hint or "").lower()
    if "transcash" in hint_l:
        typ = "transcash"
    elif "paysafe" in hint_l:
        typ = "paysafecard"
    elif hint_l in ("pcs", "neosurf"):
        typ = "pcs"
    elif "TRANSCASH" in up:
        typ = "transcash"
    elif "PAYSAFE" in up:
        typ = "paysafecard"
    else:
        typ = "pcs"

    # --- passe chiffres dediee (psm 4) pour les codes numeriques nets ---
    druns = []
    if typ in ("paysafecard", "transcash"):
        try:
            dtxt = pytesseract.image_to_string(
                img, lang="eng",
                config="--psm 4 -c tessedit_char_whitelist=0123456789")
            for ln in dtxt.splitlines():
                d = re.sub(r"\D", "", ln)
                if len(d) >= 8:
                    druns.append(d)
        except Exception:
            pass

    # --- serie (commun PCS / PaysafeCard) ---
    serie = ""
    for _ln in lines:
        if re.search(r'S[E\u00c9]RIE', _ln):
            _runs = re.findall(r'[0-9]{6,}', re.sub(r'[ .]', '', _ln))
            if _runs:
                serie = max(_runs, key=len)
                break

    montant = ""
    code = ""

    if typ == "paysafecard":
        # Montant : "Montant: 50.00" (sinon "Classic 100")
        m = re.search(r'MONTANT\s*[:\-]?\s*([0-9]+(?:[.,][0-9]{1,2})?)', up)
        if not m:
            m = re.search(r'CLASSIC\s*([0-9]{2,3})', up)
        if m:
            montant = m.group(1).replace(",", ".")
        # Code : 16 chiffres — passe chiffres PUIS texte principal
        cand = list(druns)
        for _ln in lines:
            _dd = re.sub(r"\D", "", _ln)
            if _dd:
                cand.append(_dd)
        for d in cand:
            if len(d) == 16:
                code = d
                break
        if not code:
            for d in cand:
                if 15 <= len(d) <= 17:
                    code = d
                    break

    elif typ == "transcash":
        # Montant : "Montant credite : 50 EUR" (jamais "Prix de la recharge")
        m = re.search(r'CR[E\u00c9]DIT[E\u00c9]?\s*[:\-]?\s*([0-9]{1,4})', up)
        if m:
            montant = m.group(1)
        # Code : ~12 chiffres apres "VOTRE CODE" (exclut le tel = 10 chiffres)
        for d in druns:
            if 11 <= len(d) <= 14:
                code = d
                break

    else:  # PCS
        # Montant : "Credit: X"
        m = re.search(r'CR[E\u00c9]DIT[E\u00c9]?\s*[:\-]?\s*([0-9O]+(?:[.,][0-9O]{1,2})?)', up)
        if m:
            montant = m.group(1).replace("O", "0").replace(",", ".")
        if not montant:
            _SKIPM = ("POURCENT","COMMISSION","DELA","199","200","MIN","0811","TARIF","CGV")
            for ln in lines:
                if any(b in ln for b in _SKIPM):
                    continue
                mm = re.search(r'([0-9]{1,4}(?:[.,][0-9]{1,2})?)\s*(?:EUROS|EUR|\u20ac)', ln)
                if mm:
                    val = mm.group(1).replace(",", ".")
                    try:
                        if float(val) >= 1:
                            montant = val
                            break
                    except Exception:
                        pass
        # Code : alphanumerique apres SECRET
        _SKIP = ("ESPACE","DERNIERS","CHIFFRES","CARTE","EX","RECH","NUMERO","SMS")
        def good(tok):
            return (8 <= len(tok) <= 12 and tok not in _BL
                    and len(re.findall(r'[A-Z]', tok)) >= 3
                    and re.search(r'[0-9]', tok) and "RECH" not in tok)
        for i, line in enumerate(lines):
            if "SECRET" in line:
                for j in range(i+1, min(i+3, len(lines))):
                    if any(k in lines[j] for k in _SKIP):
                        continue
                    for tok in re.findall(r'\b[A-Z0-9]{8,12}\b', lines[j]):
                        if good(tok):
                            code = tok
                            break
                    if code:
                        break
            if code:
                break

    return {"ok": True, "code": code, "serie": serie, "montant": montant, "type": typ}
