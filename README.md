# Projet de prédiction des résultats de courses hippiques

Ce projet implémente une chaîne de traitement pour l'analyse et la prédiction des courses de trot en France. 

L'architecture est conçue pour être évolutive : elle sert actuellement de socle de données et commence à intégrer les pipelines de préparation pour le Machine Learning.

## Documentation Technique

Pour une compréhension approfondie du fonctionnement, référez-vous aux documents situés à la racine :

*   **[`01_cahier_des_charges.md`](./01_cahier_des_charges.md)** : Objectifs, périmètre fonctionnel et contraintes.
*   **[`02_architecturebdd.md`](./02_architecturebdd.md)** : Schéma relationnel SQL, dictionnaire des données et diagramme Mermaid.
*   **[`04_ingestion_etl.md`](./04_ingestion_etl.md)** : Détails du pipeline d'ingestion, stratégies de cache et gestion des erreurs.
*   **[`05_preparation_donnes_ml.md`](./05_preparation_donnes_ml.md)** : Méthodologie d'extraction, feature engineering et construction du dataset d'entraînement.
*   **[`06_api_backend.md`](./06_api_backend.md)** : Documentation de l'API REST, architecture Repository et évolution vers le ML.

---

## Architecture Technique

Le projet repose sur une séparation stricte des responsabilités :

1.  **ETL (Extract, Transform, Load)** : Scripts Python orientés objet pour la collecte des données.
2.  **Base de Données** : PostgreSQL et Supabase.
3.  **Machine Learning Pipeline** : Scripts dédiés à l'extraction SQL et à la transformation des données (Feature Engineering).
4.  **API Backend** : FastAPI avec une architecture en couches pour exposer les données.

```text
horse-racing-prediction/
├── failures/               # Stockage temporaire des JSON en erreur (Fallback)
├── sql/                    # Scripts d'initialisation de la BDD
├── scripts/                # Pipelines ML & Utilitaires
│   ├── export.py           # Extraction BDD -> CSV
│   └── data_preparation.py # Nettoyage & Feature Engineering
├── src/
│   ├── api/                # Backend FastAPI
│   │   ├── main.py         # Points d'entrée (Routes)
│   │   ├── repositories.py # Accès aux données (SQL)
│   │   └── schemas.py      # Validation Pydantic (DTOs)
│   ├── core/               # Configuration et DB
│   └── ingestion/          # Logique d'ingestion
├── etl.py                  # Script pour l'ingestion
├── requirements.txt        # Dépendances Python
└── .env                    # Variables d'environnement
```

---

## ⚙️ Installation

**1. Cloner le dépôt et installer les dépendances :**

```bash
pip install -r requirements.txt
```

**2. Configurer l'environnement :**

Créez un fichier `.env` à la racine contenant la connexion PostgreSQL à Supabase :

```ini
DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME
```

**3. Initialiser la base de données :**

Exécutez le script SQL pour créer les tables :

---

## Utilisation

### A. Ingestion des données (ETL)

Le script `etl.py` pilote l'alimentation de la base.

**Mise à jour quotidienne (Cron) :**
```bash
# Ingestion complète pour une date spécifique (format JJMMAAAA)
python etl.py --date 05122025 --type all
```

**Ingestion sur une période donnée :**
```bash
# Ingestion sur une période donnée
python etl.py --range 01012023 31122023 --type all
```

### B. Préparation Machine Learning

Ces scripts transforment les données brutes de la base en un fichier CSV prêt pour l'entraînement des modèles (`dataset_ready_for_ml.csv`).

**1. Extraction des données :**
Génère les CSV bruts (participants et historique) depuis PostgreSQL.
```bash
python scripts/export.py
```

**2. Feature Engineering :**
Calcule les agrégats (statistiques historiques, encodage) et nettoie les données.
```bash
python scripts/data_preparation.py
```

### C. API Backend

L'API sert actuellement de couche d'accès aux données et évoluera pour servir les prédictions.

**Démarrer le serveur :**
```bash
uvicorn src.api.main:app --reload
```

**Documentation interactive :**
Accédez à **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** pour explorer les endpoints.

---

## Roadmap & Avancement

**Phase 1 : Socle de Données (Terminé)**
- [x] Architecture BDD PostgreSQL
- [x] Pipeline d'ingestion (ETL) robuste (Gestion erreurs, Retry, Cache RAM)
- [x] Ingestion historique (Performance & Rapports)

**Phase 2 : API & Exposition (Terminé)**
- [x] Backend FastAPI
- [x] Pattern Repository pour l'accès aux données
- [x] Documentation automatique

**Phase 3 : Machine Learning (En cours)**
- [x] Scripts d'extraction des données (SQL -> CSV)
- [x] Feature Engineering (Calcul statistiques & Encodage)
- [ ] Entraînement des modèles
- [ ] Évaluation et sérialisation du meilleur modèle

**Phase 4 : Interface Utilisateur (À venir)**
- [ ] Intégration du moteur d'inférence dans l'API (`POST /predict`)
- [ ] Dashboard de visualisation