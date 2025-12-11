# Projet de prédiction des résultats de courses hippiques françaises

Ce projet vise à construire un système complet pour la collecte de données, l'analyse et la prédiction des résultats des courses hippiques françaises, en s'appuyant sur l'API publique du PMU.

## Fonctionnalités

*   **Collecte exhaustive** : Récupération des Programmes (JSON 1), Participants (JSON 2), Performances détaillées/Musique (JSON 3) et Rapports (JSON 4).
*   **Ingestion performante** : Scripts optimisés utilisant le **multithreading** et l'insertion par lots (batch processing) pour gérer la volumétrie importante des historiques.
*   **Orchestration** : Scripts permettant l'ingestion d'une journée complète ou d'une plage de dates (reprise d'historique).
*   **Stockage structuré** : Base de données PostgreSQL normalisée pour faciliter l'analyse ML.
*   **Discrétion** : Gestion des délais et des en-têtes HTTP pour simuler un comportement humain (Stealth Mode).

---

## Structure du projet

```text
horse-racing-prediction/
├── scripts/                # Scripts d'ingestion (ETL) et d'inspection
│   ├── ingest_full_day.py       # Orchestrateur pour une journée complète
│   ├── ingest_range.py          # Orchestrateur pour une période (historique)
│   ├── ingest_*.py              # Scripts unitaires par type de données (programme, perfs...)
│   └── inspect_*.py             # Scripts d'analyse exploratoire des JSON
├── src/pmu_prediction/     # Code applicatif (API, ML, Core)
│   ├── pmu_api/            # Client HTTP
│   ├── ingestion/          # Logique métier d'ingestion
│   ├── db/                 # Connexion DB
│   └── ml/                 # Machine Learning (Features, Training, Predict)
├── sql/                    # Scripts d'initialisation de la BDD
├── doc/                    # Documentation technique et fonctionnelle
├── tests/                  # Tests unitaires
├── requirements.txt        # Dépendances Python
└── README.md               # Ce fichier
```

---

## Installation

1. **Cloner le dépôt et installer les dépendances :**

```bash
pip install -r requirements.txt
```

2. **Configurer l'environnement :**

Créez un fichier `.env` à la racine du projet :

```ini
DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME
```

3. **Initialiser la base de données :**

Exécutez les scripts SQL dans l'ordre pour créer les tables et les contraintes :

1. `sql/01_schema_initial.sql`
2. `sql/02_add_constraints.sql`

---

## Utilisation

### 1. Ingestion d'une journée complète
Pour récupérer le programme, les participants, les performances et les rapports d'une date spécifique :

```bash
python scripts/ingest_full_day.py --date 05112025
```

### 2. Ingestion d'une période (Historique)
Pour récupérer des données sur plusieurs jours consécutifs (ex: pour constituer le dataset d'entraînement) :

```bash
python scripts/ingest_range.py --start 01112025 --end 05112025
```

### 3. Scripts unitaires (Debugging)
Il est possible de lancer l'ingestion étape par étape :

*   **Programme** : `python scripts/ingest_programme_day.py --date DDMMYYYY`
*   **Participants** : `python scripts/ingest_participants_day.py --date DDMMYYYY`
*   **Performances** : `python scripts/ingest_performances_day.py --date DDMMYYYY`
*   **Rapports** : `python scripts/ingest_rapports_day.py --date DDMMYYYY`

---

## Documentation

Une documentation détaillée est disponible dans le dossier `doc/` :

*   **01_cahier_des_charges.md** : Objectifs et périmètre.
*   **02_architecture_bdd.md** : Schéma relationnel et dictionnaire des données.
*   **04_scripts_ingestion.md** : Détails techniques sur le pipeline ETL.

---

## 🗺 Roadmap & Avancement

**Ingestion des données (ETL)**
- [x] Schéma SQL initial & Contraintes
- [x] Ingestion JSON 1 (Programme)
- [x] Ingestion JSON 2 (Participants & Chevaux)
- [x] Ingestion JSON 3 (Historique complet & Performances)
- [x] Ingestion JSON 4 (Rapports & Paris)
- [x] Orchestrateur de reprise d'historique (Batch range)

**Machine Learning & Application**
- [ ] Construction du Dataset unifié (Feature Engineering)
- [ ] Entraînement des modèles (Victory & Top 3)
- [ ] API de prédiction (FastAPI)
- [ ] Interface Web de visualisation
