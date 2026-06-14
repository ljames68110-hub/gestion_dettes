# crypto_db.py — Chiffrement de la base au repos (Fernet + PBKDF2)
import os, base64, hashlib
from cryptography.fernet import Fernet
_ITER = 200000
def derive_key(password, salt):
    raw = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITER)
    return base64.urlsafe_b64encode(raw)
def new_salt():
    return os.urandom(16)
def encrypt_file(plain_path, enc_path, password, salt):
    with open(plain_path, "rb") as f:
        data = f.read()
    token = Fernet(derive_key(password, salt)).encrypt(data)
    tmp = enc_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(token)
    os.replace(tmp, enc_path)
def decrypt_file(enc_path, plain_path, password, salt):
    with open(enc_path, "rb") as f:
        token = f.read()
    data = Fernet(derive_key(password, salt)).decrypt(token)
    tmp = plain_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, plain_path)
