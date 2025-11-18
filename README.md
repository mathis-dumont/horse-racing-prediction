# Projet de prédiction des résultats de courses hippiques françaises

Ce projet vise à construire un système complet pour la collecte de données, l'analyse et la prédiction des résultats des courses hippiques françaises, en s'appuyant sur l'API non officielle du PMU.

## Fonctionnalités

* Récupération automatisée des JSON PMU (programme, participants, performances, rapports).
* Ingestion fiable dans une base PostgreSQL.
* Analyse et inspection des données brutes.
* Préparation du Machine Learning (features, entraînement, prédictions).
* Documentation claire du projet et du schéma de données.

---

## Structure du projet

```
projet/
│
├── scripts/                # Scripts d'ingestion et d’inspection des données brutes
├── src/pmu_prediction/     # Code principal (API, ingestion, DB, ML)
│   ├── pmu_api/            # Client HTTP et gestion des URLs
│   ├── ingestion/          # Ingestion JSON 1–4 dans PostgreSQL
│   ├── db/                 # Connexion et gestion DB
│   └── ml/                 # Feature engineering, training, prédiction
├── sql/                    # Schéma SQL initial
├── doc/                    # Documentation projet (cahier des charges, architecture BDD…)
├── tests/                  # Tests unitaires
├── requirements.txt        # Dépendances
└── README.md               # Ce fichier
```

---

## Objectif du projet

L’objectif est de construire un pipeline complet permettant de :

1. **Collecter automatiquement** les données PMU (programme, participants, performances, rapports).
2. **Stocker proprement** ces données dans une base PostgreSQL normalisée.
3. **Entraîner des modèles de Machine Learning** capables d’estimer :

   * probabilité de victoire d’un cheval,
   * probabilité de top 3.
4. **Exposer les prédictions** via une API et les afficher via une interface web.

Les sources de données utilisées sont :

| JSON   | Description             | Exemple d’URL                                           |
| ------ | ----------------------- | ------------------------------------------------------- |
| JSON 1 | Programme du jour       | `/rest/client/1/programme/{date}`                       |
| JSON 2 | Participants            | `/rest/client/61/programme/{date}/R{}/C{}/participants` |
| JSON 3 | Performances détaillées | `/performances-detaillees/pretty`                       |
| JSON 4 | Rapports définitifs     | `/rapports-definitifs`                                  |

Plus de détails dans la documentation du dossier `doc/`.

---

## Installation

```bash
pip install -r requirements.txt
```

Créer un fichier `.env` :

```
DB_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
```

---

## Ingestion des données

Exemple : ingestion du programme (JSON 1)

```bash
python scripts/ingest_programme_day.py --date 05112025
```

Scripts d'analyse disponibles pour chaque JSON (participants, performances, rapports…).

---

## Machine Learning

Modules dans :

```
src/pmu_prediction/ml/
```

Incluent :

* `features.py`
* `training.py`
* `predict.py`

Prédictions stockées dans la table `prediction`.

---

## Documentation

Disponible dans `doc/` :

* Cahier des charges
* Architecture BDD
* Planning
* Annexes

---

## Roadmap (résumé)

* ✔ Schéma SQL & ingestion JSON 1
* ⬜ Ingestion JSON 2–3–4
* ⬜ Historique complet
* ⬜ Feature engineering
* ⬜ Modèles ML
* ⬜ API + interface web