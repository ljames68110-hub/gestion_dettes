import os, sys, getpass, shutil, filecmp
import crypto_db
DOC  = os.path.expanduser("~/Documents/GestionPerso")
DB   = os.path.join(DOC, "dettes.db")
ENC  = os.path.join(DOC, "dettes.db.enc")
SALT = os.path.join(DOC, "dettes.salt")
if not os.path.exists(DB):
    print("ATTENTION: base introuvable", DB); sys.exit(1)
if os.path.exists(ENC):
    print("Deja chiffree (.enc existe)."); sys.exit(0)
sav = os.path.expanduser("~/sauvegarde_reelle")
os.makedirs(sav, exist_ok=True)
shutil.copy2(DB, os.path.join(sav, "dettes_CORRIGEE.db"))
print("Sauvegarde de la base CORRIGEE: ~/sauvegarde_reelle/dettes_CORRIGEE.db")
pwd  = getpass.getpass("Choisis un mot de passe (NE LE PERDS PAS): ").strip()
pwd2 = getpass.getpass("Confirme le mot de passe: ").strip()
if not pwd or pwd != pwd2:
    print("Annule (vide ou non identique)."); sys.exit(1)
salt = crypto_db.new_salt()
with open(SALT, "wb") as f: f.write(salt)
crypto_db.encrypt_file(DB, ENC, pwd, salt)
crypto_db.decrypt_file(ENC, DB + ".verif", pwd, salt)
ok = filecmp.cmp(DB, DB + ".verif", shallow=False); os.remove(DB + ".verif")
if not ok:
    print("ATTENTION verification echouee - annule"); os.remove(ENC); os.remove(SALT); sys.exit(1)
for f in ("dettes.db", "dettes_backup.db", "dettes.db.avant_corrections.bak"):
    p = os.path.join(DOC, f)
    if os.path.exists(p): os.remove(p)
print("OK: base chiffree. Il ne reste dans Documents\\GestionPerso que:")
for f in sorted(os.listdir(DOC)): print("   ", f)
