Absolument ! Voici une proposition pour le fichier `README.md` de votre projet, rédigé en se basant sur la structure et le contenu des fichiers fournis.

---

# Projet de Prédiction de Courses Hippiques PMU

Ce projet vise à construire un système complet pour la collecte, le stockage et l'analyse des données de courses hippiques du PMU, avec pour objectif final de développer des modèles de machine learning pour prédire les résultats des courses.

## 🎯 Objectif

L'objectif principal est d'automatiser l'ensemble du processus, de l'ingestion des données brutes depuis l'API non officielle du PMU jusqu'à la génération de prédictions sur les performances des chevaux.

## ✨ Fonctionnalités

*   **Ingestion de Données Automatisée** : Scripts pour collecter les données de programme, les participants, les performances historiques et les rapports de paris depuis les points d'accès JSON de l'API PMU.
*   **Base de Données Structurée** : Un schéma de base de données PostgreSQL normalisé et robuste pour stocker de manière cohérente les informations sur les programmes, les réunions, les courses, les chevaux et les résultats.
*   **Architecture Modulaire** : Le code est organisé en modules distincts pour l'interaction avec l'API, l'ingestion des données, la gestion de la base de données et (prochainement) le machine learning.
*   **Scripts d'Inspection** : Utilitaires pour analyser la qualité, la disponibilité et la structure des données brutes avant leur traitement.
*   **Gestion des Dépendances et de l'Environnement** : Utilisation de `requirements.txt` et de fichiers `.env` pour une configuration simple et reproductible.

## 🚀 État d'Avancement du Projet

Le projet est structuré en plusieurs phases. Voici l'état actuel :

1.  **Architecture & Configuration** : ✔️ Terminé
2.  **Création du Schéma de la Base de Données** : ✔️ Terminé
3.  **Analyse des Données Sources (JSON)** : ✔️ Terminé
4.  **Ingestion du Programme du Jour (JSON 1)** : ✔️ Terminé
5.  **Ingestion des Participants (JSON 2)** : ⏳ **Prochaine étape**
6.  **Ingestion des Performances (JSON 3)** : ⏳ En attente
7.  **Ingestion des Rapports (JSON 4)** : ⏳ En attente
8.  **Feature Engineering & Pipeline ML** : ⏳ En attente
9.  **Déploiement (API de prédiction)** : ⏳ En attente

## 🏗️ Architecture

Le flux de données du projet est le suivant :

1.  **Source de données** : Des points d'accès JSON de l'API `online.turfinfo.api.pmu.fr` sont interrogés pour obtenir les données du jour.
2.  **Ingestion** : Les scripts Python dans le répertoire `scripts/` et le module `src/pmu_prediction/ingestion/` récupèrent, transforment et chargent ces données.
3.  **Stockage** : Une base de données PostgreSQL (hébergée sur Supabase, par exemple) stocke les données normalisées selon le schéma défini dans `sql/001_schema_initial.sql`.
4.  **Machine Learning** : Le module `src/pmu_prediction/ml/` sera utilisé pour développer des features, entraîner des modèles et générer des prédictions.
5.  **Prédictions** : Les résultats des modèles seront stockés dans la table `prediction` pour une consultation future.

### Schéma de la Base de Données

Le schéma relationnel est conçu pour séparer logiquement les différentes entités des courses hippiques.

```mermaid
erDiagram
    daily_program {
        SERIAL program_id PK
        DATE program_date
    }
    race_meeting {
        SERIAL meeting_id PK
        INT program_id FK
        INT meeting_number
    }
    race {
        SERIAL race_id PK
        INT meeting_id FK
        INT race_number
    }
    horse {
        SERIAL horse_id PK
        TEXT horse_name
    }
    race_participant {
        SERIAL participant_id PK
        INT race_id FK
        INT horse_id FK
        INT pmu_number
    }
    horse_race_history {
        SERIAL history_id PK
        INT horse_id FK
        DATE race_date
    }
    race_bet {
        SERIAL bet_id PK
        INT race_id FK
        TEXT bet_type
    }
    bet_report {
        SERIAL report_id PK
        INT bet_id FK
        TEXT combination
    }
    prediction {
        SERIAL prediction_id PK
        INT participant_id FK
        TEXT model_version
    }

    daily_program ||--o{ race_meeting : "contient"
    race_meeting ||--o{ race : "possède"
    race ||--o{ race_participant : "inclut"
    horse ||--o{ race_participant : "participe à"
    horse ||--o{ horse_race_history : "a historique de"
    race ||--o{ race_bet : "propose"
    race_bet ||--o{ bet_report : "génère"
    race_participant ||--o{ prediction : "est prédit"
```

## 🛠️ Installation et Configuration

### Prérequis

*   Python 3.8+
*   Un serveur PostgreSQL accessible

### Étapes

1.  **Cloner le dépôt**
    ```bash
    git clone <URL_DU_REPO>
    cd projet
    ```

2.  **Créer et activer un environnement virtuel**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Sur Windows: venv\Scripts\activate
    ```

3.  **Installer les dépendances**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurer les variables d'environnement**
    Créez un fichier `.env` à la racine du projet en vous basant sur un modèle `.env.example` (à créer si manquant). Il doit contenir l'URL de connexion à votre base de données :
    ```env
    # .env
    DB_URL="postgresql://USER:PASSWORD@HOST:PORT/DATABASE"
    ```

5.  **Initialiser la base de données**
    Exécutez le script SQL `sql/001_schema_initial.sql` sur votre base de données PostgreSQL pour créer toutes les tables et relations nécessaires.

## 🚀 Utilisation

Les scripts principaux se trouvent dans le répertoire `scripts/`.

### Ingestion des données

Pour ingérer le programme complet d'une journée donnée, utilisez le script `ingest_programme_day.py`.

**Exemple :**
```bash
python scripts/ingest_programme_day.py --date 05112025
```
Ce script va :
1.  Interroger l'API PMU pour la date spécifiée (au format `JJMMYYYY`).
2.  Peupler les tables `daily_program`, `race_meeting` et `race` avec les données récupérées.
3.  Gérer les mises à jour (logique "upsert") pour éviter les doublons si le script est exécuté plusieurs fois pour la même date.

## 📂 Structure du Dépôt

```
├── .gitignore          # Fichiers et dossiers à ignorer par Git
├── README.md           # Ce fichier
├── requirements.txt    # Dépendances Python du projet
├── doc/                # Documentation (architecture, planning, analyse...)
├── scripts/            # Scripts autonomes (ingestion, inspection...)
├── src/                # Code source principal du projet
│   └── pmu_prediction/ # Package Python
│       ├── db/         # Modules liés à la base de données
│       ├── ingestion/  # Logique d'ingestion des données
│       ├── ml/         # Modules de Machine Learning
│       └── pmu_api/    # Client pour l'API PMU
├── sql/                # Scripts d'initialisation de la BDD
└── tests/              # Tests unitaires et d'intégration
```