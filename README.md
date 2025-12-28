# Horse Racing Prediction API (PMU)

Ce projet implémente une chaîne de traitement complète pour l'analyse et la prédiction des courses de trot. Il a été refactorisé pour suivre les standards de production modernes, avec une séparation stricte entre le **Backend** (Logique métier, ETL, ML) et le **Frontend** (Interface utilisateur).

L'architecture est modulaire :
- **Backend** : FastAPI, SQLAlchemy/Postgres, XGBoost (Python lourd).
- **Frontend** : Streamlit (Python léger), consommation via API REST.

## 📚 Documentation Technique

L'ensemble de la documentation détaillée se trouve dans le dossier [`doc/`](./doc/).

**Général & Projet :**
*   [`00_introduction.md`](./doc/00_introduction.md) : Contexte et vue d'ensemble.
*   [`01_cahier_des_charges.md`](./doc/01_cahier_des_charges.md) : Objectifs et périmètre fonctionnel.
*   [`03_planning.md`](./doc/03_planning.md) : Roadmap et suivi des phases.

**Data & Backend :**
*   [`02_architecture_bdd.md`](./doc/02_architecture_bdd.md) : Modèle de données (SQL) et dictionnaire.
*   [`04_ingestion.md`](./doc/04_ingestion.md) : Stratégie ETL et sources de données.
*   [`05_preparation_donnees_ml.md`](./doc/05_preparation_donnees_ml.md) : Feature Engineering et préparation pour le ML.
*   [`06_api_backend.md`](./doc/06_api_backend.md) : Documentation technique de l'API et des endpoints.

**Interface :**
*   [`07_frontend.md`](./doc/07_frontend.md) : Architecture de l'application Streamlit.

---

## 🏗 Architecture Technique

Le projet est divisé en deux sous-systèmes distincts pour assurer une meilleure maintenabilité et faciliter la conteneurisation (Docker).

### Arborescence du projet

```text
horse-racing-prediction/
├── backend/                # COEUR DU SYSTÈME
│   ├── .env                # Variables d'environnement (BDD)
│   ├── .venv/              # Environnement virtuel dédié Backend
│   ├── requirements.txt    # Dépendances (FastAPI, XGBoost, Pandas...)
│   ├── data/               # Stockage des modèles (.pkl) et exports
│   └── src/
│       ├── cli/            # Scripts d'administration (ETL)
│       ├── api/            # API REST (FastAPI)
│       ├── ml/             # Pipeline Machine Learning
│       └── core/           # Config & Database
│
├── frontend/               # INTERFACE UTILISATEUR
│   ├── .venv/              # Environnement virtuel dédié Frontend
│   ├── requirements.txt    # Dépendances légères (Streamlit, Requests)
│   ├── main.py             # Entrypoint Dashboard
│   └── api_client.py       # Connecteur vers le Backend
│
├── doc/                    # DOCUMENTATION DU PROJET
│   ├── 00_introduction.md
│   ├── ...
│   └── 07_frontend.md
│
└── README.md               # Ce fichier
```

---

## ⚙️ Installation

Ce projet nécessite **deux terminaux** et **deux environnements virtuels** distincts.

### 1. Configuration du Backend

Ouvrez un terminal et naviguez vers le dossier `backend` :

```bash
cd backend
python -m venv .venv

# Activation (Windows)
.venv\Scripts\activate
# Activation (Mac/Linux)
source .venv/bin/activate

# Installation des dépendances lourdes
pip install -r requirements.txt
```

**Configuration de la BDD :**
Créez un fichier `.env` dans le dossier `backend/` :

```ini
DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME
```

### 2. Configuration du Frontend

Ouvrez un **nouveau terminal** et naviguez vers le dossier `frontend` :

```bash
cd frontend
python -m venv .venv

# Activation
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# Installation des dépendances légères
pip install -r requirements.txt
```

---

## 🚀 Utilisation

Voici le guide complet, étape par étape, pour lancer ce projet de zéro en utilisant Docker.

### 1. Démarrer l'Infrastructure

Ouvrez votre terminal à la racine du projet et exécutez :

```bash
docker compose up --build

```

* **Attendez** que le défilement des logs se stabilise et que vous voyiez des messages indiquant que la Base de données, le Backend et le Frontend sont prêts (ex: `Uvicorn running`, `database system is ready to accept connections`).
* **Gardez ce terminal ouvert.** Il affiche les journaux (logs) du serveur.

---

### 2. Peupler la Base de Données (Crucial)

La base de données Docker démarre vide. Nous devons injecter les données des courses d'aujourd'hui.

1. Ouvrez un **Second Terminal**.
2. Exécutez le script ETL **à l'intérieur** du conteneur backend actif (ajustez la date à aujourd'hui, **28122025**) :

```bash
docker exec -it pmu_backend python -m src.cli.etl --date 28122025 --type all

```

* **Attendez** de voir le message : `INFO | ORCHESTRATOR | All jobs completed.`

---

### 3. Utiliser l'Application

Tout est maintenant opérationnel.

* **Frontend (Dashboard) :** [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)
* *Action :* Sélectionnez **2025/12/28** dans la barre latérale. Vérifiez la présence des recommandations "Sniper" en haut de page.


* **Backend (Documentation API) :** [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)
* *Action :* Utilisez `GET /` pour vérifier si le `ml_engine` est bien chargé.

**2. Entraînement du modèle (Machine Learning)**
Le script récupère les données SQL, génère les features et sauvegarde le modèle dans `backend/ml/`.
```bash
python -m src.ml.trainer
```

**3. Démarrer le serveur API**
```bash
# L'API sera accessible sur http://localhost:8000
uvicorn src.api.main:app --reload
```

### B. Terminal 2 : Frontend (Dashboard)

Assurez-vous d'être dans le dossier `frontend/` avec le venv activé. Assurez-vous que l'API Backend tourne dans l'autre terminal.

```bash
# Le dashboard s'ouvrira sur http://localhost:8501
streamlit run main.py
```

---

## 🗺 Roadmap & Avancement

**Phase 1 : Socle de Données (Terminé)**
- [x] Architecture BDD PostgreSQL.
- [x] Pipeline ETL robuste avec gestion d'erreurs.

**Phase 2 : API & Exposition (Terminé)**
- [x] Backend FastAPI structuré.
- [x] Pattern Repository & Schemas Pydantic.

**Phase 3 : Machine Learning (Terminé)**
- [x] Feature Engineering avancé.
- [x] Pipeline d'entraînement automatisé (`src/ml/trainer.py`).
- [x] Intégration du modèle dans l'API.

**Phase 4 : Interface & Architecture (En cours)**
- [x] Dashboard Frontend (Streamlit) connecté à l'API.
- [ ] Dockerisation (Backend Dockerfile & Frontend Dockerfile).
- [ ] Automatisation CI/CD (GitHub Actions).