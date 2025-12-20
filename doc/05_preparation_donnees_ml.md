# Documentation technique : préparation des données pour l'apprentissage automatique

Ce document décrit la méthode de transformation des données brutes stockées dans la base postgresql en un jeu de données exploitable par des algorithmes d'apprentissage automatique. Les opérations sont réparties dans deux scripts python distincts : `export.py` pour l'extraction et `data_preparation.py` pour le traitement.

## 1. Vue d'ensemble du flux de données

Le pipeline de préparation suit quatre étapes logiques :
1.  **source** : base de données relationnelle contenant les tables normalisées.
2.  **extraction** : exécution de requêtes sql et génération de fichiers csv intermédiaires.
3.  **transformation** : calcul d'agrégats statistiques et encodage numérique.
4.  **sortie** : génération d'un fichier csv unique consolidé.

---

## 2. Extraction des données (`export.py`)

Ce module assure l'interface avec la base de données via la bibliothèque `sqlalchemy`. Il génère deux jeux de données distincts pour séparer les participants de leur historique.

### 2.1. Jeu de données des participants
La requête principale (`QUERY_MAIN`) construit la table de référence pour l'entraînement. Chaque ligne correspond à la participation d'un cheval à une course.
*   **jointures** : le script associe les tables `race_participant`, `race`, `race_meeting`, `daily_program` et `horse`.
*   **enrichissement** : les identifiants numériques sont complétés par les libellés textuels via les tables `lookup_shoeing` (déferrage) et `racing_actor` (jockey, entraîneur).
*   **variables cibles** :
    *   `finish_rank` : rang d'arrivée officiel.
    *   `is_winner` : variable binaire calculée (valeur 1 si le rang est 1, sinon 0).
*   **filtre** : seules les courses ayant un résultat définitif sont extraites.

### 2.2. Jeu de données de l'historique
La requête secondaire (`QUERY_HISTORY`) extrait les performances passées depuis la table `horse_race_history`.
*   **contenu** : date, discipline, distance, allocation, place, réduction kilométrique et distance parcourue.
*   **objectif** : ces données brutes servent de base au calcul des indicateurs de performance dans l'étape suivante.

---

## 3. Transformation et ingénierie des caractéristiques (`data_preparation.py`)

Ce module charge les fichiers csv générés et applique les transformations mathématiques nécessaires.

### 3.1. Calcul des statistiques historiques
Le script agrège les données de l'historique par cheval (`groupby`) pour créer de nouvelles variables synthétiques :
*   `career_races` : nombre total de courses enregistrées.
*   `avg_rank` : moyenne arithmétique des places obtenues.
*   `avg_speed` : moyenne de la réduction kilométrique (vitesse).
*   `best_speed` : meilleure performance chronométrique (minimum de la réduction kilométrique).
*   `hist_earnings` : somme totale des allocations remportées.

### 3.2. Gestion des données manquantes
Le script applique des règles de gestion pour les valeurs nulles :
*   **vitesse** : imputation d'une valeur par défaut (1.20) lorsque la réduction kilométrique est absente.
*   **historique vide** : attribution de la valeur 0 pour les gains et le nombre de courses si le cheval n'a pas d'historique connu.
*   **nettoyage** : suppression des lignes du jeu de données principal où le rang d'arrivée (`finish_rank`) est manquant.

### 3.3. Encodage des variables catégorielles
Les variables textuelles sont converties en valeurs numériques via la méthode `LabelEncoder` :
*   **périmètre** : concerne les colonnes `racetrack_code`, `discipline`, `track_type`, `terrain_label`, `sex` et `shoeing_status`.
*   **méthode** : chaque modalité unique est remplacée par un entier (ex: 0, 1, 2...).
*   **résultat** : création de nouvelles colonnes avec le suffixe `_encoded`.

---

## 4. Structure du fichier de sortie

Le fichier final `dataset_ready_for_ml.csv` regroupe les colonnes sélectionnées pour l'entraînement :

*   **métadonnées** : `program_date`, `race_id`, `horse_id`.
*   **cibles** : `finish_rank` (classement), `is_winner` (victoire).
*   **caractéristiques contextuelles** : `distance_m`, `declared_runners_count`.
*   **caractéristiques du participant** : `age`, `career_winnings`.
*   **caractéristiques calculées (historique)** : `career_races`, `avg_rank`, `avg_speed`, `hist_earnings`.
*   **caractéristiques encodées** : `racetrack_code_encoded`, `discipline_encoded`, `shoeing_status_encoded`.

---

## 5. Exécution

La procédure nécessite l'exécution séquentielle des commandes suivantes à la racine du projet :

1.  extraction des données :
    ```bash
    python scripts/export.py
    ```
2.  préparation du fichier d'entraînement :
    ```bash
    python scripts/data_preparation.py
    ```