# Documentation Technique : Pipeline d'Ingestion de Données (ETL)

Ce document détaille l'architecture, le fonctionnement et les choix techniques des scripts d'ingestion (ETL) situés dans le répertoire `scripts/`. Ce pipeline a pour objectif d'alimenter une base de données PostgreSQL distante à partir de l'API publique du PMU.

## 1. Principes d'Architecture

L'architecture du projet repose sur quatre piliers fondamentaux pour garantir robustesse, performance et discrétion :

*   **Idempotence & Intégrité** : Les scripts sont conçus pour être exécutés plusieurs fois sans altérer l'intégrité des données. L'utilisation systématique de la clause SQL `ON CONFLICT DO NOTHING` prévient la création de doublons.
*   **Simulation de Trafic (Stealth Mode)** : Afin de contourner les limitations d'accès (Rate Limiting / WAF), chaque requête HTTP injecte des en-têtes imitant un navigateur réel (`User-Agent`, `Referer`). De plus, une temporisation aléatoire (`random.uniform`) est appliquée pour éviter les signatures temporelles robotiques.
*   **Parallélisme Contrôlé** : L'ingestion massive utilise le multithreading (`ThreadPoolExecutor`). Cela permet de traiter plusieurs courses simultanément tout en limitant le nombre de connexions concurrentes (`MAX_WORKERS`) pour ne pas saturer l'API source ou le pool de connexions de la base de données.
*   **Optimisation Réseau (Batch Processing)** : Face à une base de données distante, la latence réseau (Network Round-Trip) est le facteur limitant principal. Les scripts traitant de gros volumes de données regroupent les insertions (Bulk Inserts) pour minimiser les allers-retours.

---

## 2. Détail des Modules ETL

L'exécution des scripts doit respecter un ordre séquentiel strict pour satisfaire les contraintes de clés étrangères (Foreign Keys) de la base de données.

### Étape 1 : Architecture de la Journée (`ingest_programme_day.py`)
*Ce script est le point d'entrée obligatoire du pipeline.*

*   **Source** : API PMU (JSON 1 - Programme).
*   **Mode d'exécution** : Séquentiel (Single-thread).
*   **Fonction** : Il établit le squelette relationnel de la journée (Réunions → Courses). Il ne récupère que les métadonnées structurelles.
*   **Tables cibles** : `daily_program`, `race_meeting`, `race`.
*   **Commande** :
    ```bash
    python scripts/ingest_programme_day.py --date 05112025
    ```

### Étape 2 : Acteurs de la Course (`ingest_participants_day.py`)
*   **Source** : API PMU (JSON 2 - Participants).
*   **Mode d'exécution** : Parallèle (Multithreading).
*   **Fonction** : Récupère la liste des partants pour toutes les courses initialisées à l'étape 1.
*   **Tables cibles** : `horse`, `race_participant`.
*   **Commande** :
    ```bash
    python scripts/ingest_participants_day.py --date 05112025
    ```

### Étape 3 : Historique et Performances (`ingest_performances_day.py`)
*Module critique à forte volumétrie.*

Ce script est le plus complexe du pipeline car il gère le "Big Data" hippique (l'historique complet de chaque cheval).

*   **Source** : API PMU (JSON 3 - Performances Détaillées).
*   **Mode d'exécution** : Hybride (Parallèle + **Batch Insert**).
*   **Problématique Technique** :
    L'historique des performances génère une quantité exponentielle de données. Une seule course de 16 partants, où chaque cheval possède un historique de 50 courses, représente **800 enregistrements** à insérer.
    Dans un contexte de base de données distante (Cloud/Remote), une insertion ligne par ligne (row-by-row) provoquerait un goulot d'étranglement majeur dû à la latence réseau (800 allers-retours TCP pour une seule course).
*   **Solution Implémentée** :
    1.  **Agrégation en Mémoire** : Le worker récupère et transforme toutes les données d'une course en mémoire.
    2.  **Insertion par Lot (Batch)** : Utilisation de `psycopg2.extras.execute_values` pour envoyer l'intégralité des données d'une course en **une seule transaction SQL**. Cela divise le temps de traitement par un facteur 100 à 1000 selon la latence.
    3.  **Thread-Safe Caching** : Un cache local (`HORSE_CACHE`) partagé entre les threads (sécurisé par `threading.Lock`) évite de re-interroger la base pour des IDs de chevaux déjà connus.
*   **Tables cibles** : `horse`, `horse_race_history`.
*   **Commande** :
    ```bash
    python scripts/ingest_performances_day.py --date 05112025
    ```

### Étape 4 : Résultats et Rapports (`ingest_rapports_day.py`)
*   **Source** : API PMU (JSON 4 - Rapports Définitifs).
*   **Mode d'exécution** : Parallèle (Multithreading).
*   **Fonction** : Récupère les rapports de gains (Cotes, Gagnants, Placés) nécessaires au calcul des cibles (Target) pour le Machine Learning.
*   **Tables cibles** : `race_bet`, `bet_report`.
*   **Commande** :
    ```bash
    python scripts/ingest_rapports_day.py --date 05112025
    ```

---

## 3. Orchestration et Automatisation

Pour faciliter l'exploitation quotidienne et la reprise d'historique (Backfilling), deux scripts d'orchestration sont disponibles.

### A. Ingestion Quotidienne : `ingest_full_day.py`
Ce script pilote exécute séquentiellement les modules 1 à 4 pour une date donnée. Il gère la propagation des erreurs : si le programme (Étape 1) échoue, le processus s'arrête immédiatement.

**Usage standard :**
```bash
python scripts/ingest_full_day.py --date 05112025
```

### B. Reprise d'Historique : `ingest_range.py`
Permet l'ingestion massive sur une plage de dates. Il itère sur chaque jour et appelle `ingest_full_day.py`.

**Usage Backfill :**
```bash
python scripts/ingest_range.py --start 01112025 --end 30112025
```

---

## 4. Guide de Dépannage (Troubleshooting)

| Code / Erreur | Cause Probable | Action Recommandée |
| :--- | :--- | :--- |
| **HTTP 403 (Forbidden)** | Détection de bot par l'API. | Vérifier les headers `User-Agent`. Augmenter la temporisation (`random.uniform(0.5, 1.0)`). |
| **HTTP 204 (No Content)** | Course étrangère ou annulée. | **Comportement normal**. Le script ignore logiquement les courses sans données JSON (fréquent sur R7/R8). |
| **"Found 0 races"** | Désynchronisation du pipeline. | Le script `ingest_programme_day.py` n'a pas été exécuté ou a échoué pour cette date. Le relancer. |
| **TimeoutError / SSL** | Instabilité de la connexion réseau. | Relancer le script. Grâce à l'idempotence, il reprendra le travail sans dupliquer les données. |

## 5. Configuration de Performance

Les paramètres suivants peuvent être ajustés dans les en-têtes des scripts Python (`MAX_WORKERS`, `time.sleep`) selon la capacité de la machine hôte et de la base de données.

*   **Profil "Production" (Recommandé)** :
    *   `MAX_WORKERS = 12`
    *   `sleep = random.uniform(0.1, 0.3)`
    *   *Compromis idéal entre vitesse d'ingestion et discrétion.*

*   **Profil "Safe" (En cas de ban IP)** :
    *   `MAX_WORKERS = 4`
    *   `sleep = random.uniform(0.5, 1.5)`
    *   *Très lent, mais indétectable.*