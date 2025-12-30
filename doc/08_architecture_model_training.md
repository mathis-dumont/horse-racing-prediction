---

# Architecture du Modèle et Documentation de l'Entraînement

### 1. Le Pipeline d'Entraînement (`model_production.py`)
Le processus d'entraînement est un pipeline en plusieurs étapes conçu pour convertir les données brutes de courses hippiques en probabilités précises et calibrées.

*   **Découpage Temporel (Time-Series Splitting) :**
    Les données sont divisées strictement par date (Entraînement $\rightarrow$ Validation $\rightarrow$ Test). Nous n'entraînons jamais le modèle sur des courses futures afin d'éviter la "fuite de données" (*data leakage*).
*   **Synchronisation des Fonctionnalités (Features) :**
    Le script scanne toutes les données catégorielles (ex : Jockeys, Entraîneurs, Ferrure) dans l'ensemble d'entraînement. Il crée une "Liste Maîtresse" des catégories connues. Toute valeur nouvelle ou inconnue apparaissant dans le futur est strictement traitée comme `NaN` pour éviter le plantage du modèle en production.
*   **Étape 1 : XGBoost avec Contraintes Logiques :**
    Nous entraînons un modèle de Gradient Boosting (`XGBClassifier`) avec des **Contraintes Monotones**.
    *   *Contrainte :* Nous forçons le modèle à respecter la logique mathématique selon laquelle un `odds_rank` plus bas (1er favori) doit impliquer une probabilité de victoire plus élevée qu'un rang inférieur. Cela empêche le modèle "d'halluciner" des motifs erronés dans le bruit des outsiders (*longshots*).
*   **Étape 2 : Calibrage des Probabilités (Régression Isotonique) :**
    XGBoost produit des "scores", et non des probabilités réelles. Nous entraînons donc un second méta-modèle (`CalibratedClassifierCV`) sur l'**Ensemble de Validation**.
    *   *Objectif :* Si le modèle prédit une confiance de 30 % pour 100 chevaux, exactement 30 d'entre eux doivent gagner.
    *   *Résultat :* Cela aligne la confiance du modèle avec la réalité, nous permettant de calculer un **Avantage (Edge)** mathématique précis contre le bookmaker.

---

### 2. Artefacts Générés
Le script d'entraînement produit trois fichiers critiques. Les trois sont requis pour exécuter le script de prédiction `predict_today_v2.py`.

#### 1. `trot_sniper_model.json` (Le Cerveau Brut)
*   **C'est quoi :** Le cœur du modèle d'arbre de décision XGBoost sauvegardé au format JSON optimisé.
*   **Fonction :** Il contient les milliers de règles "Si/Sinon" apprises de l'historique (ex : *"Si Cheval est D4 ET Driver est Bazire, ajouter +0.5 au score"*).
*   **Usage :** Il est encapsulé à l'intérieur du Calibrateur. Nous chargeons rarement ce fichier directement en production.

#### 2. `probability_calibrator.pkl` (Le Produit Fini)
*   **C'est quoi :** Un objet Python Pickle contenant le **Classifieur Calibré**.
*   **Fonction :** Cet objet contient **à la fois** le modèle XGBoost Brut (ci-dessus) **et** la couche de correction par Régression Isotonique.
*   **Usage :** **C'est le fichier principal utilisé pour la prédiction.**
    *   *Entrée :* Données du cheval.
    *   *Sortie :* Une probabilité précise (ex : `0.317`), corrigée de tout excès de confiance.

#### 3. `model_artifacts.pkl` (Le Dictionnaire)
*   **C'est quoi :** Un dictionnaire de métadonnées contenant :
    1.  **Liste des Features :** L'ordre exact des colonnes attendu par le modèle.
    2.  **Cartes des Catégories :** La liste stricte des Jockeys, Entraîneurs et configurations de Ferrure vus lors de l'entraînement.
*   **Fonction :** Il agit comme un "Traducteur". Il assure que les données scrappées aujourd'hui sont formatées **exactement** de la même manière que les données d'entraînement (ex : convertir "D4" en l'ID interne correct).
*   **Usage :** Utilisé pour pré-traiter les données en direct avant de les envoyer au Calibrateur.

---

### 3. Flux d'Inférence (Fonctionnement conjoint)

```mermaid
[Données Scrappées en Direct] 
       ⬇
[model_artifacts.pkl] --> (Formate les données & Aligne les catégories)
       ⬇
[probability_calibrator.pkl] --> (Contient XGBoost + Logique de Correction)
       ⬇
[Probabilité Finale] --> (ex : 31.7%)
```