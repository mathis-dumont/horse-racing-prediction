# Horse Racing Prediction API (PMU)

Ce projet implémente une chaîne de traitement complète pour l'analyse et la prédiction des courses de trot. Il a été refactorisé pour suivre les standards de production (Clean Code, Logging, Typing).

L'architecture est modulaire, séparant l'ingestion de données (ETL), la logique Machine Learning (XGBoost), l'exposition via API (FastAPI) et la visualisation via un Dashboard (Streamlit).

## Documentation Technique

Pour une compréhension approfondie du fonctionnement, référez-vous aux documents situés à la racine :

*   **[`01_cahier_des_charges.md`](./01_cahier_des_charges.md)** : Objectifs et périmètre.
*   **[`02_architecturebdd.md`](./02_architecturebdd.md)** : Schéma SQL et dictionnaire des données.
*   **[`06_api_backend.md`](./06_api_backend.md)** : Documentation de l'API REST et de l'intégration ML.

---

## Architecture Technique

Le projet repose sur une architecture en couches :

1.  **ETL (Extract, Transform, Load)** : Collecte les données hippiques.
2.  **Core ML** : Pipeline scikit-learn/XGBoost encapsulé (Feature Engineering -> Training -> Inference).
3.  **API Backend** : FastAPI avec injection de dépendances.
4.  **Frontend** : Interface utilisateur Streamlit pour la visualisation et l'interaction.

### Arborescence du projet

```text
horse-racing-prediction/
├── data/                   # Stockage des modèles (.pkl) et exports
├── frontend/               # INTERFACE UTILISATEUR (Streamlit)
│   ├── main.py             # Entrypoint Dashboard
│   └── api_client.py       # Client HTTP pour l'API Backend
├── src/
│   ├── cli/                # Scripts d'administration et entrypoints
│   │   └── etl.py          # Orchestrateur d'ingestion 
│   ├── api/                # COUCHE EXPOSITION (FastAPI)
│   │   ├── main.py         # Entrypoint, Lifespan & Routes
│   │   ├── repositories.py # Accès BDD (SQL pur)
│   │   └── schemas.py      # DTOs Pydantic (Validation)
│   ├── ml/                 # COUCHE INTELLIGENCE (Machine Learning)
│   │   ├── features.py     # Feature Engineering (Transformers sklearn)
│   │   ├── loader.py       # Construction du Dataset (SQL complexe)
│   │   ├── trainer.py      # Script d'entraînement (XGBoost)
│   │   └── predictor.py    # Moteur d'inférence (Chargement modèle)
│   └── core/               # Configuration (Database, Env)
├── requirements.txt        # Dépendances Python
└── .env                    # Variables d'environnement
```

---

## Installation

**1. Cloner le dépôt et installer les dépendances :**

```bash
pip install -r requirements.txt
```

**2. Configurer l'environnement :**

Créez un fichier `.env` à la racine contenant la connexion PostgreSQL :

```ini
DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME
```

---

## Utilisation

### A. Ingestion des données (ETL)

Le script d'ingestion est situé dans le module `cli` pour faciliter l'automatisation.

```bash
# Exemple : Ingestion pour une date spécifique
python -m src.cli.etl --date 05122025 --type all
```

### B. Machine Learning (Entraînement)

Le module `src.ml.trainer` se charge de tout : récupération des données SQL, calcul des features (ratios, historiques), entraînement XGBoost et sauvegarde du modèle.

**Lancer un entraînement :**
```bash
python -m src.ml.trainer
```
*Cela générera le fichier `data/model_xgboost.pkl`.*

### C. API Backend (Serveur)

L'API charge le modèle ML au démarrage et sert de backend pour le frontend.

**Démarrer le serveur (Port 8000) :**
```bash
uvicorn src.api.main:app --reload
```

### D. Interface Utilisateur (Frontend)

Le dashboard permet de visualiser les courses et de lancer les prédictions de manière interactive. Assurez-vous que l'API Backend tourne en parallèle.

**Lancer le dashboard :**
```bash
streamlit run frontend/main.py
```
*L'interface sera accessible sur `http://localhost:8501`.*

---

## Roadmap & Avancement

**Phase 1 : Socle de Données (Terminé)**
- [x] Architecture BDD PostgreSQL & Supabase.
- [x] Pipeline ETL robuste avec gestion d'erreurs.

**Phase 2 : API & Exposition (Terminé)**
- [x] Backend FastAPI structuré.
- [x] Pattern Repository & Schemas Pydantic.

**Phase 3 : Machine Learning (Terminé)**
- [x] **Refactoring Code Pro (English, Typing, Logging).**
- [x] Feature Engineering avancé (Rangs relatifs, Ratios gains/courses).
- [x] Pipeline d'entraînement automatisé (`src/ml/trainer.py`).
- [x] Intégration du modèle dans l'API (`src/ml/predictor.py`).

**Phase 4 : Interface & Monitoring (En cours)**
- [x] Dashboard Frontend (Streamlit) pour visualiser les pronostics.
- [ ] Dockerisation complète (Backend + Frontend + DB).
- [ ] Automatisation CI/CD (GitHub Actions) et CRONs pour l'ETL quotidien.
