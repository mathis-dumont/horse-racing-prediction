# Architecture et fonctionnement du pipeline d'ingestion (ETL)

## 1. Vue d'ensemble

Le module d'ingestion adopte une architecture orientée objet (POO) modulaire et performante. Il se situe dans le répertoire `src/ingestion/` et a pour responsabilité d'extraire les données de l'API PMU, de les transformer et de les charger dans la base de données PostgreSQL.

L'architecture repose sur une classe de base et des classes enfants spécialisées pour chaque type de données (programme, participants, performances, rapports).

## 2. Structure du code

Le code est organisé comme suit :

*   **`src/ingestion/base.py`** : contient la classe abstraite `BaseIngestor`. Elle gère la session HTTP, les stratégies de réessai (retry), la connexion à la base de données via le singleton `DatabaseManager` et la sauvegarde des fichiers JSON en cas d'échec (fallback).
*   **`src/ingestion/program.py`** : gère l'initialisation de la journée (tables `daily_program`, `race_meeting`, `race`).
*   **`src/ingestion/participants.py`** : gère l'insertion des chevaux, jockeys, entraîneurs et la table de liaison `race_participant`.
*   **`src/ingestion/performances.py`** : gère l'historique de carrière des chevaux (`horse_race_history`). C'est le module le plus critique en termes de volume.
*   **`src/ingestion/rapports.py`** : gère les résultats de paris (`race_bet`, `bet_report`).
*   **`etl.py`** : script CLI (Command Line Interface) faisant office de point d'entrée pour lancer les processus.

## 3. Stratégies d'optimisation

Le pipeline intègre plusieurs mécanismes pour garantir la performance et la fiabilité.

### 3.1. Parallélisme contrôlé
L'ingestion des détails de course (participants, performances, rapports) utilise `concurrent.futures.ThreadPoolExecutor`. Cela permet de traiter plusieurs courses simultanément (défini par `MAX_WORKERS` dans la configuration), réduisant le temps d'attente lié aux entrées/sorties réseau (I/O bound).

### 3.2. Système de cache en mémoire (RAM)
Pour limiter les appels répétitifs à la base de données, les modules `participants.py` et `performances.py` chargent les entités référentielles en mémoire au démarrage.
*   **Fonctionnement** : au lancement, le script charge l'ensemble des `horse_id` et `horse_name` dans un dictionnaire Python.
*   **Gain** : évite d'exécuter un `SELECT` pour vérifier l'existence de chaque cheval avant insertion.
*   **Sécurité** : l'accès au cache est protégé par un `threading.Lock` pour éviter les conflits d'écriture entre les threads.

### 3.3. Idempotence
Toutes les requêtes SQL d'insertion utilisent la clause `ON CONFLICT DO NOTHING`. Cela permet de relancer le script sur une journée déjà traitée sans générer de doublons ni d'erreurs d'intégrité.

### 3.4. Gestion des erreurs
En cas d'échec d'insertion ou de parsing, le JSON brut est sauvegardé localement dans le dossier `failures/`. Cela assure qu'aucune donnée n'est définitivement perdue et permet un débogage ultérieur.

## 4. Flux de données détaillé

### Étape 1 : Programme (`ProgramIngestor`)
Ce module s'exécute en séquentiel. Il récupère l'arbre complet de la journée (Réunions -> Courses) et peuple les tables structurelles. Il est impératif d'exécuter cette étape en premier pour satisfaire les clés étrangères.

### Étape 2 : Participants (`ParticipantsIngestor`)
Ce module itère sur toutes les courses créées à l'étape 1.
1.  **Pré-chargement** : chargement des caches (chevaux, acteurs, types de déferrage).
2.  **Traitement** : pour chaque cheval, le script vérifie son existence en cache ou le crée en base, puis lie le cheval à la course via `race_participant`.
3.  **Normalisation** : les entités comme les types d'incidents ou les statuts de déferrage sont normalisées à la volée.

### Étape 3 : Performances (`PerformancesIngestor`)
Ce module gère le plus gros volume de données ("la musique" du cheval).
1.  **Batch Insert** : utilisation de `psycopg2.extras.execute_values` pour insérer tout l'historique d'un cheval en une seule transaction SQL, réduisant la latence réseau.
2.  **Filtrage** : seules les données pertinentes (discipline, distance, réduction kilométrique) sont conservées.

### Étape 4 : Rapports (`RapportsIngestor`)
Récupère les rapports définitifs pour calculer les cibles d'apprentissage (gagnant, placé). Il distingue les types de paris (`race_bet`) et leurs résultats chiffrés (`bet_report`).

## 5. Utilisation via CLI

L'exécution se fait via le script `etl.py` à la racine du projet.

**Exemple d'ingestion complète pour un jour :**
```bash
python etl.py --date 05122025 --type all
```

**Exemple d'ingestion sur une plage de dates (rattrapage historique) :**
```bash
python etl.py --range 01112025 30112025 --type all
```

