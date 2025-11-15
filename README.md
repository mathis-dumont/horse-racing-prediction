# Projet de Prédiction de Courses Hippiques via l'API PMU

Ce document décrit la méthodologie pour collecter, traiter et exploiter les données de l'API PMU afin de construire un modèle de Machine Learning pour prédire les résultats des courses hippiques.

## 1. Vue d'ensemble des Sources de Données

Notre stratégie repose sur l'agrégation de données provenant de quatre endpoints API distincts pour chaque course. Chaque endpoint fournit un ensemble spécifique d'informations utiles.

### Liens de l'API (Exemple pour la course R1C1 du 05/11/2025)

1.  **Programme du Jour** :
    ```
    https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025
    ```
    *   **Rôle** : Fournit le contexte général de toutes les réunions et courses de la journée.

2.  **Participants de la Course** :
    ```
    https://online.turfinfo.api.pmu.fr/rest/client/61/programme/05112025/R1/C1/participants
    ```    
    *   **Rôle** : Donne le profil détaillé de chaque cheval participant à une course spécifique au jour J.

3.  **Performances Détaillées (Musique)** :
    ```
    https://online.turfinfo.api.pmu.fr/rest/client/61/programme/05112025/R1/C1/performances-detaillees/pretty
    ```
    *   **Rôle** : Contient l'historique de performance complet pour chaque participant de la course. C'est la source la plus riche pour le feature engineering.

4.  **Rapports Définitifs** :
    ```
    https://online.turfinfo.api.pmu.fr/rest/client/1/programme/05112025/R1/C1/rapports-definitifs
    ```
    *   **Rôle** : Fournit les résultats financiers (rapports) de la course une fois terminée. Essentiel pour définir les cibles de rentabilité et pour le backtesting.

## 2. Structure du Dataset Final

L'objectif est de créer un unique tableau de données (DataFrame) où **chaque ligne représente un seul cheval dans une seule course**. Ce format "plat" est idéal pour les algorithmes de Machine Learning.

La structure d'une ligne sera la suivante :

`[FEATURES DE LA COURSE] + [FEATURES DU PARTICIPANT] + [FEATURES DE SON HISTORIQUE] + [CIBLES]`

## 3. Détail des Features à Extraire par Endpoint

### 3.1. Programme du Jour (Contexte de la Course)

Ces caractéristiques décrivent le contexte de la compétition. Elles seront identiques pour chaque cheval de la même course.

| Raw Feature Name | Source dans le JSON | Utilité |
| :--- | :--- | :--- |
| `race_hippodrome` | `reunions.hippodrome.libelleCourt` | Aptitude du cheval à une piste spécifique. |
| `race_date` | `programme.date` | Pour des analyses saisonnières. |
| `race_distance` | `reunions.courses.distance` | **Fondamental.** Aptitude du cheval à la distance. |
| `race_discipline` | `reunions.courses.discipline` | **Fondamental.** Plat, Attelé, Haies... |
| `race_specialite` | `reunions.courses.specialite` | Précise la discipline (ex: Trot Monté). |
| `race_corde` | `reunions.courses.corde` | Corde à gauche ou à droite. Certains chevaux ont une préférence marquée. |
| `race_allocation` | `reunions.courses.montantPrix` | **Très important.** Indicateur du niveau de la course. |
| `race_nb_partants` | `reunions.courses.nombreDeclaresPartants` | Influence la tactique et la difficulté de la course. |
| `race_categorie` | `reunions.courses.categorieParticularite` | Type de course (Handicap, Nationale...). Très important. |
| `race_penetrometre` | `reunions.courses.penetrometre.intitule` | **Crucial** en Plat/Obstacle. État du terrain (bon, collant, lourd...). |

(~10 features ici)

---

### 3.2. Participants (Profil du Jour J)

C'est le profil du "candidat" pour la course du jour.

| Raw Feature Name | Source dans le JSON | Utilité |
| :--- | :--- | :--- |
| `horse_num_pmu` | `participants.numPmu` | Identifiant. |
| `horse_age` | `participants.age` | **Fondamental.** |
| `horse_sexe` | `participants.sexe` | **Fondamental.** |
| `horse_race` | `participants.race` | Trotteur Français vs. Etranger, Pur Sang, etc. |
| `horse_driver` | `participants.driver` | **Facteur humain clé.** |
| `horse_entraineur` | `participants.entraineur` | **Facteur humain clé.** |
| `horse_deferrage` | `participants.deferre` | **Crucial au trot.** |
| `horse_oeilleres` | `participants.oeilleres` | Indicateur d'équipement. |
| `horse_handicap_distance` | `participants.handicapDistance` | Distance réelle parcourue (avec recul éventuel). |
| `horse_cote` | `participants.dernierRapportDirect.rapport` | **La feature brute la plus prédictive.** |
| `horse_avis_entraineur` | `participants.avisEntraineur` | Avis d'expert direct. |
| `horse_gains_carriere` | `participants.gainsParticipant.gainsCarriere` | Indicateur de la "classe" du cheval. |
| `horse_gains_victoires` | `participants.gainsParticipant.gainsVictoires` | |
| `horse_gains_places` | `participants.gainsParticipant.gainsPlace` | |
| `horse_gains_annee_en_cours` | `participants.gainsParticipant.gainsAnneeEnCours`| Indicateur de forme récente. |
| `horse_gains_annee_precedente`| `participants.gainsParticipant.gainsAnneePrecedente`| |
| `horse_nom_pere` | `participants.nomPere` | Lignée / Génétique. |
| `horse_nom_mere` | `participants.nomMere` | Lignée / Génétique. |

*(~18 features ici)*

---

### 3.3. Performances Détaillées (Création de Features Historiques)

C'est là que l'on peut massivement augmenter le nombre de features. Au lieu de calculer des moyennes, on va "déplier" les N dernières courses dans des colonnes dédiées. C'est une technique très courante.

Pour la **dernière course (N-1)** :
*   `hist_1_place`
*   `hist_1_rk` (Réduction Kilométrique)
*   `hist_1_jours_depuis` (calcul simple : `date_course - date_historique`)
*   `hist_1_distance`
*   `hist_1_allocation` (pour comparer le niveau)
*   `hist_1_driver` (pour voir s'il y a un changement)
*   `hist_1_hippodrome`
*   `hist_1_incident` (Disqualifié, Non Placé...)

Pour l'**avant-dernière course (N-2)** :
*   `hist_2_place`
*   `hist_2_rk`
*   `hist_2_jours_depuis`
*   `hist_2_distance`
*   ... et ainsi de suite.

Pour l'**antépénultième course (N-3)** :
*   `hist_3_place`
*   `hist_3_rk`
*   ... et ainsi de suite.

En dépliant sur 3 à 5 courses, vous ajoutez `5 * 8 = 40` features ! Même en se limitant à 3 courses, cela fait déjà **24 nouvelles features**.

---

### 3.4. Rapports Définitifs (Définition des Cibles)

Ce JSON n'est pas utilisé pour les features d'entrée, mais pour **créer les colonnes cibles (Y)** que le modèle devra prédire, et pour le **backtesting**.

| Cible à Créer | Chemin d'accès dans le JSON | Rôle |
| :--- | :--- | :--- |
| `target_a_gagne`| Vérifier si `ordreArrivee` du cheval = 1. | **Classification :** Prédire le gagnant (Oui/Non). |
| `target_est_place`| Vérifier si `ordreArrivee` du cheval <= 3. | **Classification :** Prédire si le cheval sera sur le podium. |
| `target_rapport_gagnant`| Extraire le `dividendePourUnEuro` du pari `SIMPLE_GAGNANT` pour le cheval gagnant. | **Régression / Backtesting :** Prédire la rentabilité d'un pari gagnant. |
| `target_rapport_place`| Extraire le `dividendePourUnEuro` du pari `SIMPLE_PLACE` pour les 3 premiers chevaux. | **Régression / Backtesting :** Prédire la rentabilité d'un pari placé. |

## 4. Pipeline de Développement

1.  **Collecte :** Écrire un script (ex: `fetch_race_data.py`) qui prend en entrée une date, une réunion et une course, télécharge les 4 JSONs, et les fusionne en un DataFrame unique.
2.  **Constitution de la Base de Données :** Exécuter ce script en boucle sur des milliers de courses passées pour créer un grand dataset d'entraînement.
3.  **Feature Engineering :** Nettoyer les données, gérer les valeurs manquantes, et créer toutes les features listées ci-dessus. Encoder les variables catégorielles (ex: nom du driver) en variables numériques.
4.  **Modélisation :**
    *   **Entraînement :** Utiliser un algorithme de type Gradient Boosting (XGBoost, LightGBM) pour entraîner un modèle de classification sur la cible `target_a_gagne`.
    *   **Validation :** Séparer les données par date (ex: entraîner sur 2023, valider sur 2024) pour éviter les fuites de données temporelles.
5.  **Backtesting :**
    *   Utiliser le modèle entraîné pour prédire les probabilités de victoire sur un jeu de données de test.
    *   Définir une stratégie de pari (ex: parier si `probabilité * cote > 1.2`).
    *   Utiliser les colonnes `target_rapport_gagnant` pour simuler les gains/pertes et calculer la rentabilité de la stratégie.