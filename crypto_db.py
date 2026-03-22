# crypto_db.py — Chiffrement AES-256 de la base de données
"""
La base dettes.db est chiffrée sur le disque (dettes.db.enc).
Au démarrage : déchiffrée dans un fichier temporaire sécurisé.
À l'arrêt : rechiffrée automatiquement, temp supprimé.
Clé dérivée du PIN via PBKDF2-SHA256 (100 000 itérations).
"""

import os
import sys
import struct
import hashlib
import hmac
import tempfile
import shutil
import atexit

# AES-256-CBC via module 'cryptography' (standard)
# Fallback sur implémentation pure Python si absent
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes, padding
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("[Crypto] 'cryptography' absent — chiffrement désactivé")

# ── Constantes ───────────────────────────────────────────────────────────────
MAGIC    = b"GPERSO1"   # signature fichier chiffré
KDF_ITER = 100_000      # itérations PBKDF2
SALT_LEN = 32
IV_LEN   = 16
HMAC_LEN = 32

_temp_db_path  = None   # chemin du fichier temporaire déchiffré
_enc_db_path   = None   # chemin du fichier chiffré
_crypto_key    = None   # clé AES en mémoire

# ── Dérivation de clé ─────────────────────────────────────────────────────────

def derive_key(pin: str, salt: bytes) -> bytes:
    """Dérive une clé AES-256 depuis le PIN avec PBKDF2-SHA256."""
    if HAS_CRYPTO:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                         iterations=KDF_ITER, backend=default_backend())
        return kdf.derive(pin.encode())
    else:
        # Fallback hashlib pur Python
        return hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, KDF_ITER, dklen=32)

# ── Chiffrement / Déchiffrement ───────────────────────────────────────────────

def encrypt_data(data: bytes, key: bytes) -> bytes:
    """Chiffre des données avec AES-256-CBC + HMAC-SHA256."""
    salt = os.urandom(SALT_LEN)
    iv   = os.urandom(IV_LEN)

    if HAS_CRYPTO:
        padder = padding.PKCS7(128).padder()
        padded = padder.update(data) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        enc    = cipher.encryptor()
        ciphertext = enc.update(padded) + enc.finalize()
    else:
        raise RuntimeError("Module 'cryptography' requis pour le chiffrement")

    # HMAC pour intégrité
    mac = hmac.new(key, salt + iv + ciphertext, hashlib.sha256).digest()
    return MAGIC + salt + iv + mac + ciphertext

def decrypt_data(data: bytes, key: bytes) -> bytes:
    """Déchiffre des données AES-256-CBC + vérifie HMAC."""
    if not data.startswith(MAGIC):
        raise ValueError("Fichier non chiffré ou corrompu")

    pos        = len(MAGIC)
    salt       = data[pos:pos+SALT_LEN];       pos += SALT_LEN
    iv         = data[pos:pos+IV_LEN];          pos += IV_LEN
    mac_stored = data[pos:pos+HMAC_LEN];        pos += HMAC_LEN
    ciphertext = data[pos:]

    # Vérifier intégrité
    mac_calc = hmac.new(key, salt + iv + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac_stored, mac_calc):
        raise ValueError("Intégrité échouée — PIN incorrect ou fichier corrompu")

    if HAS_CRYPTO:
        cipher    = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        dec       = cipher.decryptor()
        padded    = dec.update(ciphertext) + dec.finalize()
        unpadder  = padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
    else:
        raise RuntimeError("Module 'cryptography' requis")

# ── Gestion fichier chiffré ───────────────────────────────────────────────────

def is_encrypted(db_path: str) -> bool:
    """Vérifie si le fichier est chiffré."""
    enc_path = db_path + ".enc"
    if not os.path.exists(enc_path):
        return False
    with open(enc_path, 'rb') as f:
        return f.read(len(MAGIC)) == MAGIC

def encrypt_db(db_path: str, key: bytes):
    """Chiffre le fichier db_path → db_path.enc et supprime le clair."""
    if not os.path.exists(db_path):
        return
    with open(db_path, 'rb') as f:
        data = f.read()
    enc_data = encrypt_data(data, key)
    enc_path = db_path + ".enc"
    with open(enc_path, 'wb') as f:
        f.write(enc_data)
    # Écraser le fichier clair (secure delete basique)
    _secure_delete(db_path)
    print(f"[Crypto] Base chiffrée → {enc_path}")

def decrypt_db_to_temp(db_path: str, key: bytes) -> str:
    """
    Déchiffre db_path.enc vers un fichier temporaire sécurisé.
    Retourne le chemin du fichier temporaire.
    """
    enc_path = db_path + ".enc"
    if not os.path.exists(enc_path):
        # Pas encore chiffré — retourner le chemin original
        return db_path

    with open(enc_path, 'rb') as f:
        enc_data = f.read()

    plain_data = decrypt_data(enc_data, key)

    # Créer un fichier temp dans le même dossier (pour SQLite WAL)
    tmp_dir  = os.path.dirname(db_path)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db", dir=tmp_dir, prefix=".gp_tmp_")
    os.close(tmp_fd)

    with open(tmp_path, 'wb') as f:
        f.write(plain_data)

    print(f"[Crypto] Base déchiffrée → temp {tmp_path}")
    return tmp_path

def _secure_delete(path: str):
    """Écrase un fichier avec des zéros avant suppression."""
    if not os.path.exists(path):
        return
    size = os.path.getsize(path)
    with open(path, 'wb') as f:
        f.write(b'\x00' * size)
    os.remove(path)

# ── Session chiffrée ──────────────────────────────────────────────────────────

def open_encrypted_session(db_path: str, pin: str) -> str:
    """
    Ouvre une session chiffrée.
    - Dérive la clé depuis le PIN
    - Déchiffre la base vers un fichier temporaire
    - Enregistre le rechiffrement automatique à l'arrêt
    Retourne le chemin du fichier temporaire à utiliser comme DB_FILE.
    """
    global _temp_db_path, _enc_db_path, _crypto_key

    # Dériver la clé
    # Le sel est stocké dans le fichier .enc ou généré la première fois
    enc_path = db_path + ".enc"
    if os.path.exists(enc_path):
        # Lire le sel existant
        with open(enc_path, 'rb') as f:
            f.read(len(MAGIC))  # skip magic
            salt = f.read(SALT_LEN)
    else:
        salt = os.urandom(SALT_LEN)

    _crypto_key   = derive_key(pin, salt)
    _enc_db_path  = db_path
    _temp_db_path = decrypt_db_to_temp(db_path, _crypto_key)

    # Enregistrer rechiffrement automatique à l'arrêt
    atexit.register(_close_session)

    return _temp_db_path

def _close_session():
    """Appelé automatiquement à l'arrêt — rechiffre et nettoie."""
    global _temp_db_path, _enc_db_path, _crypto_key
    if _temp_db_path and _enc_db_path and _crypto_key:
        if _temp_db_path != _enc_db_path:  # fichier temp différent de l'original
            try:
                print("[Crypto] Rechiffrement de la base...")
                # Rechiffrer depuis le temp
                encrypt_db(_temp_db_path, _crypto_key)
                # Renommer .enc vers le bon nom
                tmp_enc = _temp_db_path + ".enc"
                final_enc = _enc_db_path + ".enc"
                if os.path.exists(tmp_enc):
                    shutil.move(tmp_enc, final_enc)
                print("[Crypto] Base rechiffrée OK")
            except Exception as e:
                print(f"[Crypto] ERREUR rechiffrement : {e}")
        _temp_db_path = None
        _enc_db_path  = None
        _crypto_key   = None

def migrate_existing_db(db_path: str, pin: str):
    """
    Migration : chiffre une base existante non chiffrée.
    Appelé une seule fois lors de la première utilisation.
    """
    if not os.path.exists(db_path):
        return  # rien à migrer
    enc_path = db_path + ".enc"
    if os.path.exists(enc_path):
        return  # déjà chiffré

    print("[Crypto] Migration : chiffrement de la base existante...")
    salt = os.urandom(SALT_LEN)
    key  = derive_key(pin, salt)
    encrypt_db(db_path, key)
    print("[Crypto] Migration terminée")
