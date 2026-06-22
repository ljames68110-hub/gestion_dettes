# chiffrer_base.py — Active le chiffrement de la base (a lancer UNE fois)
"""
Cree dettes.db.enc + dettes.salt a partir de dettes.db, avec un mot de passe.
Fait une sauvegarde et verifie l'aller-retour avant de valider.
A lancer dans le dossier projet : python chiffrer_base.py
"""
import os, sys, getpass, shutil, filecmp
import crypto_db

DB, ENC, SALT = "dettes.db", "dettes.db.enc", "dettes.salt"

if not os.path.exists(DB):
    print("ATTENTION : dettes.db introuvable ici"); sys.exit(1)
if os.path.exists(ENC):
    print("Deja chiffree (dettes.db.enc existe). Rien a faire."); sys.exit(0)

shutil.copy2(DB, "dettes.db.avant_chiffrement.bak")
print("Sauvegarde : dettes.db.avant_chiffrement.bak")

pwd  = getpass.getpass("Choisis un mot de passe (NE LE PERDS PAS) : ").strip()
pwd2 = getpass.getpass("Confirme le mot de passe : ").strip()
if not pwd:
    print("Mot de passe vide. Annule."); sys.exit(1)
if pwd != pwd2:
    print("Les deux saisies different. Annule."); sys.exit(1)

salt = crypto_db.new_salt()
with open(SALT, "wb") as f:
    f.write(salt)
crypto_db.encrypt_file(DB, ENC, pwd, salt)

# verification aller-retour
crypto_db.decrypt_file(ENC, "dettes_verif.tmp", pwd, salt)
same = filecmp.cmp(DB, "dettes_verif.tmp", shallow=False)
os.remove("dettes_verif.tmp")
if not same:
    print("ATTENTION : verification echouee — chiffrement annule")
    for f in (ENC, SALT):
        if os.path.exists(f): os.remove(f)
    sys.exit(1)

print("OK : dettes.db.enc + dettes.salt crees et verifies.")
print("Le fichier en clair dettes.db sera efface a la prochaine FERMETURE de l'appli.")
print("Lance l'appli (python main.py), entre ton mot de passe, teste, puis ferme.")
