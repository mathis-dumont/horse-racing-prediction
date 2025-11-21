# 🏇 Spécifications de l'application web de prédictions hippiques

Ce document décrit les fonctionnalités et éléments d'interface que
l'application web doit afficher.\
Il sert de référence pour le développement du frontend et du backend.

------------------------------------------------------------------------

## 🎨 1. Interface générale

L'interface doit être :

-   moderne et lisible\
-   responsive (mobile + desktop)\
-   organisée en sections claires\
-   esthétique proche PMU

------------------------------------------------------------------------

## 📅 2. Courses du jour

### Objectif

Afficher les courses du jour et permettre le lancement de prédictions.

### Fonctionnalités

#### Liste des courses

-   Chaque course est cliquable.
-   Exemple :
    -   R1C3 -- Prix d'Enghien -- 15:15
    -   R2C5 -- Grand Handicap -- 17:40

#### Types de paris (après clic sur une course)

-   Simple gagnant\
-   Simple placé\
-   Couplé\
-   Tiercé\
-   Quinté+

Chaque type comporte un bouton : **Lancer la prédiction**

#### Tableau de résultats

  Participant   Prob. Gagnant   Prob. Placé   Côte   Commentaire
  ------------- --------------- ------------- ------ --------------
  Cheval 5      0.32            0.55          7.5    Bon outsider
  ...           ...             ...           ...    ...

------------------------------------------------------------------------

## 📊 3. Résultats de la semaine

Tableau comparatif modèle vs réel :

  Course   Pari   Prédiction modèle   Résultat réel     Correct ?
  -------- ------ ------------------- ----------------- -----------
  R1C3     SG     Cheval 5 (25%)      Cheval 5 -- 1er   ✔
  R2C1     SP     Cheval 2 (45%)      Cheval 2 -- 4e    ✘

------------------------------------------------------------------------

## 📈 4. Statistiques globales

-   Taux global de réussite\
-   Performance Simple Gagnant\
-   Performance Simple Placé\
-   Date de début du calcul

Exemple d'affichage :

    Taux global : 62%
    SG : 29%
    SP : 54%
    Depuis : 01/02/2025

------------------------------------------------------------------------

## 🔌 5. API Backend (Flask)

-   `GET /api/courses/today`
-   `GET /api/courses/<course_id>/bets`
-   `POST /api/predict`
-   `GET /api/results/week`
-   `GET /api/stats/global`

------------------------------------------------------------------------

## ✔️ Conclusion

Ce document définit : - l'interface attendue\
- les sections\
- les données à afficher\
- les connexions backend

Il constitue la base du développement du frontend de l'application.
