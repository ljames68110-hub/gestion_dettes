# crypto_db.py — Chiffrement de la base au repos (Fernet + PBKDF2)
import os, base64, hashlib, time, gc
from cryptography.fernet import Fernet
_ITER = 200000

def derive_key(password, salt):
    raw = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITER)
    return base64.urlsafe_b64encode(raw)

def new_salt():
    return os.urandom(16)

def _safe_replace(tmp, dst, data=None, attempts=40, delay=0.25):
    """os.replace resilient. Sous Windows la cible ou le .tmp peut rester tenu
    quelques secondes (antivirus, handle sqlite en cours de liberation) : on
    reessaie, puis en dernier recours on ecrit directement dans la cible."""
    last = None
    for _ in range(attempts):
        try:
            os.replace(tmp, dst)
            return
        except (PermissionError, OSError) as e:
            last = e
            gc.collect()
            time.sleep(delay)
    if data is not None:
        try:
            with open(dst, "wb") as f:
                f.write(data)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            try:
                os.remove(tmp)
            except Exception:
                pass
            return
        except Exception:
            pass
    if last is not None:
        raise last

def encrypt_file(plain_path, enc_path, password, salt):
    with open(plain_path, "rb") as f:
        data = f.read()
    token = Fernet(derive_key(password, salt)).encrypt(data)
    tmp = enc_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(token)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    _safe_replace(tmp, enc_path, data=token)

def decrypt_file(enc_path, plain_path, password, salt):
    with open(enc_path, "rb") as f:
        token = f.read()
    data = Fernet(derive_key(password, salt)).decrypt(token)
    tmp = plain_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    _safe_replace(tmp, plain_path, data=data)
