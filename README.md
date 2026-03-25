# Gestion Dettes Premium

Application desktop Windows de gestion de dettes/créances — interface web premium servie par un backend Flask local.

## Architecture

```
gestion_dettes.exe
│
├── main.py          → Point d'entrée : lance Flask + ouvre le navigateur
├── api.py           → Serveur REST Flask (127.0.0.1:5000)
├── db.py            → Accès SQLite (dettes.db)
└── web/
    └── index.html   → Interface premium dark mode
```

**Flux** : `exe` → Flask démarre → navigateur s'ouvre sur `http://127.0.0.1:5000` → l'interface web appelle l'API Flask → Flask lit/écrit dans `dettes.db`.

## Endpoints API

| Méthode | Route | Description |
|---------|-------|-------------|
| GET  | `/api/auth/status` | PIN configuré ? |
| POST | `/api/auth/setup` | Créer le PIN initial |
| POST | `/api/auth/login` | Se connecter (→ token) |
| POST | `/api/auth/logout` | Se déconnecter |
| POST | `/api/auth/change-pin` | Changer le PIN |
| GET  | `/api/dashboard` | Stats globales |
| GET  | `/api/clients` | Liste des clients |
| POST | `/api/clients` | Créer un client |
| GET  | `/api/clients/:id` | Détail client |
| PUT  | `/api/clients/:id` | Modifier un client |
| DELETE | `/api/clients/:id` | Supprimer un client |
| GET  | `/api/clients/:id/stats` | Stats d'un client |
| GET  | `/api/clients/:id/transactions` | Transactions d'un client |
| GET  | `/api/transactions` | Toutes les transactions |
| POST | `/api/transactions` | Créer une transaction |
| DELETE | `/api/transactions/:id` | Supprimer une transaction |
| GET  | `/api/export/csv/:id` | Export CSV client |
| GET  | `/api/export/csv/all` | Export CSV global |

Toutes les routes sauf `/api/auth/status`, `/api/auth/setup` et `/api/auth/login` nécessitent le header `X-Session-Token`.

## Sécurité

- PIN hashé avec SHA-256 + sel aléatoire (stocké dans `dettes.db`, table `auth`)
- Token de session en mémoire (invalide après redémarrage)
- Serveur lié à `127.0.0.1` uniquement (pas accessible depuis le réseau)

## Développement local

```bash
pip install flask flask-cors
python main.py
# → ouvre http://127.0.0.1:5000
```

## Build exe

```bash
pip install pyinstaller
pyinstaller --onefile --name gestion_dettes \
  --add-data "web;web" \
  --add-data "db.py;." \
  --add-data "api.py;." \
  --hidden-import flask \
  --hidden-import flask_cors \
  main.py
```

Le `dettes.db` est créé dans le même dossier que l'exe au premier lancement.

## Structure du projet

```
projet/
├── main.py
├── api.py
├── db.py
├── requirements.txt
├── web/
│   └── index.html       ← interface premium (à créer)
├── latest.json
├── sha256.txt
└── .github/
    └── workflows/
        └── release.yml
```
