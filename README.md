# Projet de prédiction des résultats de courses hippiques françaises

Ce projet vise à construire un système complet pour la collecte de données, l'analyse et la prédiction des résultats des courses hippiques françaises, en s'appuyant sur l'API publique du PMU.

Le projet utilise une **architecture Orientée Objet (OOP)** stricte et expose désormais ses données via une **API REST (FastAPI)**.

## 🚀 Fonctionnalités Clés

*   **Architecture Modulaire** : Code structuré en classes avec une séparation claire des responsabilités (ETL vs API).
*   **Backend API Modern** :
    *   **FastAPI** : Framework asynchrone haute performance.
    *   **Repository Pattern** : Isolation totale des requêtes SQL (pas de SQL dans les contrôleurs).
    *   **Pydantic** : Validation stricte des données et sérialisation automatique (DTOs).
*   **Performance & Optimisation** :
    *   **Multithreading** : Ingestion parallèle contrôlée (Workers).
    *   **Cache In-Memory** : Chargement des entités en RAM pour réduire les I/O BDD.
    *   **Singleton Database** : Gestion centralisée du pool de connexions PostgreSQL.
*   **Robustesse** : Retry automatique, gestion des Deadlocks et Fallback JSON local.

---

## 📂 Structure du projet

```text
horse-racing-prediction/
├── failures/               # Dossier de sauvegarde automatique (Fallback JSON)
├── src/
│   ├── api/                # Couche API (Backend)
│   │   ├── main.py         # Point d'entrée FastAPI (Routes)
│   │   ├── repositories.py # Logique d'accès aux données (SQL)
│   │   └── schemas.py      # Modèles de données Pydantic (DTOs)
│   ├── core/               # Cœur du système
│   │   ├── config.py       # Configuration centralisée
│   │   └── database.py     # Gestionnaire BDD Singleton
│   └── ingestion/          # Logique métier (ETL)
│   │   ├── base.py         # Classe abstraite (ABC)
│   │   ├── program.py      # Ingestion Programme & Réunions
│   │   ├── participants.py # Ingestion Participants & Chevaux
│   │   ├── performances.py # Ingestion Historique & Performances
│   │   └── rapports.py     # Ingestion Paris & Rapports
├── main.py                 # Point d'entrée de l'ETL (CLI)
├── requirements.txt        # Dépendances Python
└── .env                    # Variables d'environnement
```

---

## ⚙️ Installation

1. **Cloner le dépôt et installer les dépendances :**

```bash
pip install -r requirements.txt
```

2. **Configurer l'environnement :**

Créez un fichier `.env` à la racine contenant votre chaîne de connexion PostgreSQL :

```ini
DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME
```

3. **Initialiser la base de données :**

Assurez-vous que les scripts SQL (`sql/01_schema.sql`) ont été exécutés.

---

## 💻 Utilisation

### A. Ingestion des données (ETL)

Utilisez `main.py` pour télécharger et stocker les données.

```bash
# 1. Ingestion complète d'une journée (Recommandé)
python main.py --date 05112025 --type all

# 2. Ingestion module par module
python main.py --date 05112025 --type program
python main.py --date 05112025 --type participants
```

### B. Lancement de l'API (Backend)

Le projet expose une API REST pour consulter les données ingérées.

1. **Démarrer le serveur (Mode développement) :**

```bash
uvicorn src.api.main:app --reload
```

2. **Accéder à la documentation interactive (Swagger UI) :**

Ouvrez votre navigateur sur : **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

Vous pourrez y tester les endpoints suivants :
*   `GET /races/{date_code}` : Liste des courses pour une date donnée.
*   `GET /races/{race_id}/participants` : Liste des partants et cotes pour une course.

---

## 🗺 Roadmap & Avancement

**Ingestion des données (ETL)**
- [x] Refactoring Architecture OOP (Clean Code)
- [x] Optimisation Cache RAM (Réduction I/O)
- [x] Ingestion JSON 1 (Programme)
- [x] Ingestion JSON 2 (Participants & Chevaux)
- [x] Ingestion JSON 3 (Historique complet & Performances)
- [x] Ingestion JSON 4 (Rapports & Paris)

**Machine Learning & Application**
- [ ] Construction du Dataset unifié (Feature Engineering)
- [ ] Entraînement des modèles (Victory & Top 3)
- [x] API de lecture (FastAPI & Repository Pattern)
- [ ] API de prédiction (Inférence modèle)
- [ ] Interface Web de visualisation