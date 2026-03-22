# main.py — Point d'entrée Gestion Dettes Premium
"""
Lance le serveur Flask en arrière-plan puis ouvre l'interface dans le navigateur.
Compatible PyInstaller --onefile (gère le dossier temporaire _MEIPASS).
"""

import sys
import os
import time
import threading
import webbrowser

# ── Résolution des chemins PyInstaller ───────────────────────────────────────

def base_dir() -> str:
    """Retourne le dossier de base : _MEIPASS si frozen, sinon __file__."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS          # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))

# Le dossier de travail (là où dettes.db sera créé) reste à côté de l'exe.
APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
          else os.path.dirname(os.path.abspath(__file__))

os.chdir(APP_DIR)                    # dettes.db se crée ici
sys.path.insert(0, base_dir())       # db.py, api.py, updater.py trouvés dans _MEIPASS

# ── Imports après résolution du path ─────────────────────────────────────────

import db
import api

HOST = "127.0.0.1"
PORT = 5000
URL  = f"http://{HOST}:{PORT}"

# ── Démarrage ────────────────────────────────────────────────────────────────

def _wait_then_open():
    """Attend que Flask soit prêt, puis ouvre le navigateur."""
    import urllib.request
    for _ in range(20):          # 10 secondes max
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"{URL}/api/auth/status", timeout=1)
            break
        except Exception:
            continue
    webbrowser.open(URL)

def main():
    print(f"[DebtManager] Démarrage sur {URL}")
    print(f"[DebtManager] Base de données : {os.path.join(APP_DIR, 'dettes.db')}")

    db.init_db()

    # Initialiser le PIN par défaut "1234" si aucun PIN n'existe encore
    if not db.has_pin():
        db.set_pin("1234")
        print("[DebtManager] PIN par défaut créé : 1234")

    # Ouvrir le navigateur dans un thread séparé
    t = threading.Thread(target=_wait_then_open, daemon=True)
    t.start()

    # Vérifier mise à jour en arrière-plan (silencieux)
    try:
        import updater
        def _notify(remote):
            print(f"[DebtManager] Mise à jour disponible : {remote.get('version')}")
        updater.check_in_background(notify_flask_fn=_notify)
    except ImportError:
        pass

    # Lancer Flask (bloquant)
    api.start(host=HOST, port=PORT, debug=False)

if __name__ == "__main__":
    main()