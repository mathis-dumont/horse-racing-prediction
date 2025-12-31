# Prédiction des courses hippiques par machine learning

Ce projet vise à concevoir une plateforme complète de traitement de données et de prédiction des courses hippiques (Trot), basée sur des techniques de Machine Learning (XGBoost).

Il couvre l’ensemble de la chaîne :
- ingestion automatisée des données (ETL),
- stockage et historisation (PostgreSQL),
- entraînement et déploiement d’un modèle prédictif,
- exposition des résultats via une API REST et une interface utilisateur.

---

## Objectifs du projet

* Centraliser et historiser les données PMU (programmes, partants, performances, rapports)
* Générer des **probabilités calibrées de victoire**
* Détecter des **edges mathématiques exploitables**
* Fournir une **UI claire et rapide** pour l’analyse quotidienne
* Assurer une **exécution automatisée et reproductible** (CI/CD & CRON)

---

## Installation & Démarrage

Ce projet est conçu pour être lancé rapidement via **Docker** (recommandé). Une installation locale manuelle est également possible pour le développement spécifique.

### Prérequis

Avant de commencer, assurez-vous d'avoir installé les outils suivants sur votre machine :

*   **Docker** & **Docker Compose** (Indispensable pour la méthode recommandée).
*   **Make** (Pour utiliser les raccourcis d'automatisation).
Parfait 👍
Voici **l’intégration propre** de l’installation de `make` **directement dans ton README**, au **bon endroit**, avec un **ton académique clair**.

Tu peux **remplacer ta section “Prérequis” actuelle** par celle-ci.

---

Voici la version **mise à jour et bien structurée** de ta section **Prérequis**, avec le Makefile intégré et un ton clair pour un projet de cours :

---

## Prérequis

Avant de commencer, assurez-vous d’avoir installé les outils suivants sur votre machine :

### Docker

* **Docker** & **Docker Compose**
  Indispensable pour la méthode recommandée (exécution via conteneurs).

---

### Make

Le projet utilise un **Makefile** comme point d’entrée unique pour :

* lancer les services Docker,
* exécuter les tests,
* déclencher les pipelines ETL et Machine Learning.

L’outil `make` doit donc être installé sur votre machine.

#### Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install make
```

#### macOS

Installez les outils de développement Apple (inclut `make`) :

```bash
xcode-select --install
```

#### Windows

Deux solutions sont possibles :

**Option 1 – WSL (recommandé)**
Installez Ubuntu via le Microsoft Store, puis :

```bash
sudo apt update
sudo apt install make
```

**Option 2 – Git Bash**
Installez *Git for Windows*, puis vérifiez que `make` est disponible :

```bash
make --version
```

---

### Python et base de données (installation locale uniquement)

Ces prérequis sont nécessaires **uniquement si vous n’utilisez pas Docker** :

* **Python 3.12+**
* **PostgreSQL**

---

### Configuration

1.  **Clonage du projet :**
    ```bash
    git clone <url-du-repo>
    cd <nom-du-projet>
    ```

2.  **Variables d'environnement :**
    Le projet nécessite un fichier `.env` à la racine pour fonctionner (connexion BDD)
    
    Créez un fichier `.env` à la racine et renseignez les variables suivantes :
    ```ini
    # Exemple de configuration .env
    DB_URL=postgresql://user:password@host.docker.internal:5432/nom_de_la_bdd
    ```
    > **Note :** Si le mot de passe de la base de données supabase ne vous a pas été fourni, vous devez faire tourner votre base de données PostgreSQL sur votre machine hôte, utilisez `host.docker.internal` comme hôte dans `DB_URL` pour que le conteneur Docker puisse l'atteindre.

---

### Méthode 1 : Démarrage rapide avec Docker (Recommandé)

L'utilisation du `Makefile` simplifie grandement l'interaction avec Docker Compose.

**1. Construction des images**
Compilez les images Docker pour le backend et le frontend.
```bash
make build
# Ou pour forcer une reconstruction sans cache : make build-nc
```

**2. Lancement des services**
Démarre les conteneurs en arrière-plan (mode détaché).
```bash
make up
```

**3. Initialisation des données (ETL & ML)**
Une fois les conteneurs lancés, vous devez peupler la base de données et entraîner le modèle.

*   **Entraînement du modèle (Training) :**
    Entraîne le modèle XGBoost sur les données présentes en base.
    ```bash
    make train
    ```

*   **Optionnel :** Ingestion des données (ETL) :
    Télécharge et insère les programmes, participants et rapports pour la date du jour.
    ```bash
    make ingest
    ```
    *Ceci est optionnel, car la base de données est hébergée sur supabase, et est peuplée tous les jours par un CRON."

**4. Accès à l'application**
*   **Frontend (Interface Utilisateur) :** [http://localhost:8501](http://localhost:8501)
*   **Backend (API Documentation) :** [http://localhost:8000/docs](http://localhost:8000/docs)

**Commandes utiles :**
*   `make logs` : Affiche les logs en temps réel.
*   `make down` : Arrête les conteneurs.
*   `make clean` : Arrêt complet, suppression des volumes et nettoyage des caches Python (`__pycache__`).

---

### Méthode 2 : Installation et lancement en Local (Sans Docker)

Si vous devez développer sans Docker, suivez ces étapes. Vous aurez besoin de deux terminaux.

#### Prérequis spécifiques
*   Assurez-vous que votre la base de données PostgreSQL est accessible dans le .env. (cf configuration partie Docker).

#### 1. Backend (API)

Dans un **premier terminal** :

```bash
cd backend

# Création et activation de l'environnement virtuel
python3.12 -m venv .venv
source .venv/bin/activate  # Sur Windows: .venv\Scripts\activate

# Installation des dépendances
pip install -r requirements.txt

# Configuration du PYTHONPATH (Important pour les imports absolus 'src.*')
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Lancement du serveur API
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend (Streamlit)

Dans un **second terminal** :

```bash
cd frontend

# Création et activation de l'environnement virtuel
python3.12 -m venv .venv
source .venv/bin/activate

# Installation des dépendances
pip install -r requirements.txt

# Configuration du PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Lancement de l'application
streamlit run app.py --server.port 8501
```

---

## Automatisation & CI/CD (GitHub Actions)

Le projet intègre une **automatisation complète** via **GitHub Actions**, garantissant la mise à jour des données dans la base de données.

### 1. Ingestion quotidienne (CRON)

Un workflow GitHub Actions est exécuté **quotidiennement** pour :

* Récupérer automatiquement les données PMU du jour
* Mettre à jour la base **Supabase (PostgreSQL)**
* Garantir une base toujours synchronisée sans intervention manuelle

Cette automatisation explique pourquoi l’étape `make ingest` est optionnelle.

---

## Architecture & Fonctionnement

Ce projet repose sur une architecture **Microservices-lite**, séparant clairement responsabilités et flux de données.

### Vue d’ensemble

1. **Frontend (Streamlit)**

   * Dashboard interactif
   * Aucune connexion directe à la base
   * Communication exclusive via API REST

2. **Backend (FastAPI)**

   * Exposition des endpoints métier
   * Chargement du modèle ML en mémoire au démarrage

3. **Data & ML Pipeline**

   * **ETL** : ingestion multithreadée des données PMU
   * **Training** : génération d’un modèle XGBoost
   * **Inference** : prédictions temps réel via API

---

## Tests & Qualité du Code

Le projet inclut des commandes pour exécuter les tests unitaires et d'intégration via Docker, garantissant un environnement isolé.

```bash
# Lancer les tests Backend (Pytest)
make test-backend

# Lancer les tests Frontend (Pytest + Mocking)
make test-frontend

# Lancer tous les tests
make test-all
```

---

## Structure du Projet

L'organisation des fichiers suit les standards de l'industrie pour assurer maintenabilité et scalabilité.

```bash
.
├── Makefile                # Orchestrateur des commandes (Entry point)
├── docker-compose.yml      # Configuration des services Docker
├── .env                    # Variables d'environnement (Non versionné)
│
├── backend/                # API & Logique ML
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   ├── api/            # Routes FastAPI, Schemas (Pydantic), Repositories
│   │   ├── core/           # Config globale, Database Manager
│   │   ├── ingestion/      # ETL (Programmes, Participants, Rapports)
│   │   ├── ml/             # Feature Engineering, Training, Prediction
│   │   └── cli/            # Scripts en ligne de commande (ex: etl.py)
│   └── tests/              # Tests unitaires et d'intégration (Pytest)
│
├── frontend/               # Interface Streamlit
│   ├── Dockerfile
│   ├── app.py              # Point d'entrée de l'application
│   ├── ui/                 # Composants visuels (Sidebar, Grids, Analysis)
│   ├── state/              # Gestion d'état de session
│   ├── api/                # Client HTTP interne vers le Backend
│   └── tests/              # Tests End-to-End et UI
│
└── data/                   # modèle ML (.pkl) et dumps locaux
```

---

## Fonctionnalités Principales

### 1. Programme & Cotes

* Réunions et courses par date
* Partants, drivers, entraîneurs
* Cotes live

### 2. Prédictions IA

* Probabilités calibrées (0–100 %)
* Ranking prédictif
* Feature engineering (forme, musique, déferrage…)

### 3. Module “Sniper”

Stratégie automatisée de **Value Betting** :

* Comparaison IA vs marché
* Détection d’edges positifs
* Filtres stricts (cotes, edge min, liquidité)

---

## Bonnes pratiques & Ops

### Gestion des erreurs Docker
Si vous rencontrez des erreurs de permissions (ex: `Permission denied: '__pycache__'`) dues à la création de fichiers par Docker (root) sur votre système hôte, utilisez la commande :

```bash
make clean
# Cette commande arrête les conteneurs et force la suppression des caches avec sudo
```

### Ajouter une nouvelle dépendance
Si vous ajoutez une librairie dans `backend/requirements.txt` ou `frontend/requirements.txt`, vous devez reconstruire les images :

```bash
make build
```

---

## Documentation API

Une fois le backend lancé, la documentation interactive (Swagger UI) est disponible automatiquement. Elle permet de tester les endpoints et de voir les schémas de données attendus.

*   **URL Locale :** `http://localhost:8000/docs`
*   **Schéma JSON :** `http://localhost:8000/openapi.json`

---

## Contribution

1. Créez une branche (`feature/ma-feature`)
2. Implémentez + testez (`make test-all`)
3. Committez
4. Ouvrez une Pull Request

---