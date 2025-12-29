# 🏇 Turf Analytics Pro

**Turf Analytics Pro** est une solution complète d'intelligence artificielle dédiée à l'analyse et à la prédiction des courses hippiques (Trot).

Cette plateforme intègre une chaîne de traitement de données (ETL) performante, un moteur de Machine Learning (XGBoost) et une interface utilisateur interactive pour détecter les meilleures opportunités de paris (*Value Betting*) en temps réel.

## 📋 Table des Matières

- [Architecture](#-architecture)
- [Fonctionnalités](#-fonctionnalités)
- [Structure du Projet](#-structure-du-projet)
- [Installation & Démarrage (Docker)](#-installation--démarrage-rapide-docker)
- [🔄 Automatisation (GitHub Actions)](#-automatisation--ci-cd)
- [Installation Manuelle (Développement)](#-installation-manuelle-local)
- [Utilisation de la CLI](#-utilisation-de-la-cli-etl--ml)
- [Tests & Documentation](#-tests--documentation)

---

## 🏗 Architecture

Le projet repose sur une architecture découplée assurant performance et scalabilité :

1.  **Backend (API & Core)** :
    *   **Framework** : FastAPI.
    *   **Base de données** : PostgreSQL (Hébergé sur Supabase).
    *   **Moteur ML** : Pipeline Scikit-Learn / XGBoost avec calibration de probabilités.
    *   **Ingestion** : Orchestrateur ETL multithreadé pour la récupération des données PMU (Programme, Participants, Performances, Rapports).

2.  **Frontend (UI)** :
    *   **Framework** : Streamlit.
    *   **Rôle** : Dashboard de visualisation consommant l'API REST pour afficher les pronostics, les détails des courses et les recommandations de paris ("Sniper").

3.  **DevOps** :
    *   **Conteneurisation** : Docker & Docker Compose.
    *   **CI/CD** : GitHub Actions pour l'ingestion quotidienne automatique.

---

## ✨ Fonctionnalités

*   **Ingestion Automatisée** : Récupération parallèle des données.
*   **Algorithme "Sniper"** : Stratégie de *Value Betting* comparant les probabilités de l'IA aux cotes réelles du marché.
*   **Machine Learning Avancé** : Feature Engineering temporel, gestion des données manquantes et calibration (Isotonic Regression).
*   **Tableau de Bord Interactif** : Navigation par date, analyse des partants et monitoring des opportunités.

---

## 📂 Structure du Projet

```text
project-root/
├── .github/workflows/      # Pipelines CI/CD
│   └── daily_etl.yml       # Workflow d'ingestion journalier
├── backend/                # Services Backend
│   ├── src/
│   │   ├── api/            # API REST (FastAPI)
│   │   ├── cli/            # Scripts d'administration (ETL)
│   │   ├── core/           # Configuration & Base de données
│   │   ├── ingestion/      # Scrapers & Parsers
│   │   └── ml/             # Entraînement & Inférence ML
│   ├── data/               # Stockage des modèles (.pkl)
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/               # Interface Utilisateur
│   ├── app.py              # Point d'entrée Streamlit
│   ├── Dockerfile
│   └── requirements.txt
│
├── doc/                    # Documentation technique
└── docker-compose.yml      # Orchestration des conteneurs
```

---

## 🐳 Installation & Démarrage Rapide (Docker)

C'est la méthode recommandée pour déployer l'application localement.

### 1. Configuration (Secrets)
Le projet se connecte à une base de données persistante (Supabase).
Créez un fichier `.env` dans la racine du projet :

```ini
# ./.env
DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME
```

### 2. Lancer les services
À la racine du projet :

```bash
docker compose up --build -d
```
Cela démarre l'API Backend et le Frontend.

* **Attendez** que le défilement des logs se stabilise et que vous voyiez des messages indiquant que la Base de données, le Backend et le Frontend sont prêts (ex: `Uvicorn running`, `database system is ready to accept connections`).
* **Gardez ce terminal ouvert.** Il affiche les journaux (logs) du serveur.

### 3. Entraînement Initial (Premier Lancement)
Si c'est la première fois que vous lancez le projet et que le modèle (`.pkl`) n'existe pas encore, générez-le directement à l'intérieur du conteneur :

```bash
docker exec -it pmu_backend python -m src.ml.trainer
```
*Cette commande va créer le fichier modèle dans le conteneur, et grâce au volume configuré (`./backend/data:/app/data`), le fichier sera sauvegardé sur votre machine.*

---

### 3. Mise à jour manuelle (Optionnel)
Si vous souhaitez forcer une récupération des données sur un certain jour :

```bash
# Exemple : Récupérer les données d'un jour (29/12/2025)
docker exec -it pmu_backend python -m src.cli.etl --date 29122025 --type all
```

### 4. Accès
*   **Dashboard** : [http://localhost:8501](http://localhost:8501)
*   **API Docs** : [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔄 Automatisation & CI/CD

Ce projet intègre un workflow GitHub Actions (`.github/workflows/daily_etl.yml`) pour assurer la fraîcheur des données sans intervention humaine.

### Fonctionnement du Workflow
*   **Fréquence** : Exécution quotidienne automatique à **06:00 UTC**.
*   **Logique (Fenêtre Glissante)** : À chaque exécution, le script récupère les données de **J-2 à J (Aujourd'hui)**.
    *   *Pourquoi ?* Cela permet de récupérer le programme du jour, mais aussi de mettre à jour les résultats et rapports définitifs des courses de la veille et de l'avant-veille.
*   **Déclenchement Manuel** : Possibilité de lancer le workflow manuellement depuis l'interface GitHub ("Run workflow") en spécifiant une date précise si nécessaire.

### Configuration Requise
Pour que le workflow fonctionne sur votre fork/repository, vous devez configurer le secret suivant dans **Settings > Secrets and variables > Actions** :

| Nom du Secret | Description |
| :--- | :--- |
| `DB_URL` | La chaîne de connexion PostgreSQL (Supabase/Prod). |

---

## 🛠 Installation Manuelle (Local)

Pour le développement sans Docker.

### Partie 1 : Backend

1.  Configurer `backend/.env` avec votre `DB_URL`.
2.  Installer les dépendances :
    ```bash
    cd backend
    python -m venv .venv
    source .venv/bin/activate  # ou .venv\Scripts\activate (Windows)
    pip install -r requirements.txt
    ```

3.  **Entraînement Initial (Premier Lancement)**
    Cette étape est **nécessaire la première fois** pour créer le fichier modèle (`.pkl`) utilisé par l'API pour les prédictions :
    ```bash
    # Assurez-vous d'être dans le dossier backend/
    python3 -m src.ml.trainer
    ```

4.  Lancer l'API :
    ```bash
    uvicorn src.api.main:app --reload
    ```

### Partie 2 : Frontend

Dans un nouveau terminal :
```bash
cd frontend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## 💻 Utilisation de la CLI (Backend)

Le backend expose des outils en ligne de commande pour gérer les données manuellement.

| Action | Commande (depuis `backend/`) | Description |
| :--- | :--- | :--- |
| **Ingestion (Jour)** | `python -m src.cli.etl --date JJMMAAAA --type all` | Récupère tout pour une date spécifique. |
| **Ingestion (Plage)** | `python -m src.cli.etl --range DEBUT FIN --type program` | Récupère les données sur une période. |
| **Entraînement ML** | `python -m src.ml.trainer` | Ré-entraîne le modèle XGBoost sur les données SQL actuelles. |

---

## 🧪 Tests & Documentation

### Tests Unitaires
Les tests sont gérés par `pytest` et couvrent l'ingestion et la logique API.

```bash
cd backend
pytest
```

### Documentation Technique
Détails disponibles dans le dossier [`doc/`](./doc/) :
*   **Architecture BDD** : Modèle relationnel.
*   **API Reference** : Endpoints et schémas.
*   **ML** : Feature engineering et calibration.

---

## 📄 Licence

Ce projet est distribué sous licence MIT. Voir le fichier `LICENSE` pour plus d'informations.