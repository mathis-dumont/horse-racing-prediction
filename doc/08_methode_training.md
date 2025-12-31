# Documentation Technique : Explications de la méthode d'entraînement et justifications

Voici ce que ce notre trainer.py fait précisemment :

### 1. Gestion du "Temporal Split" (Rigueur Académique)

Notre code n'utilise pas un simple `train_test_split` aléatoire. Il utilise une **séparation temporelle** :

* **Train :** Le passé lointain.
* **Validation (30 jours) :** Utilisé pour l'arrêt précoce (*early stopping*) et surtout pour **calculer la calibration**.
* **Test (60 derniers jours) :** La "boîte noire" qui simule les performances réelles du futur.

> **Pourquoi c'est bien :** Cela évite le "Data Leakage" (fuite de données) où le modèle connaîtrait le futur pour prédire le passé.

### 2. Le Pipeline de Preprocessing

Il utilise `ColumnTransformer` pour traiter différemment les données :

* **OrdinalEncoding** pour les catégories (Jockeys, Hippodromes, etc.).
* **Passthrough** pour les numériques (Cotes, Gains).
Il encapsule tout cela dans un objet `Pipeline` de Scikit-Learn. Cela signifie qu'en production, nous injectons du texte brut et le pipeline s'occupe de tout traduire.

### 3. Entraînement avec Early Stopping

Le modèle s'arrête de lui-même (`early_stopping_rounds=50`) s'il ne progresse plus sur le jeu de validation. Cela garantit que le modèle ne fait pas de sur-apprentissage sur le bruit des données de courses.

### 4. Calibration Isotonique (Le point fort)

C'est ici que nous justifions la "fiabilité" :

```python
calibrated_model = CalibratedClassifierCV(..., method='isotonic', cv='prefit')

```

Au lieu d'utiliser les scores bruts de XGBoost (souvent trop extrêmes), la **régression isotonique** réajuste les probabilités pour qu'elles correspondent à la fréquence réelle des victoires.

### 5. Exportation "All-in-One"

Le `joblib.dump` ne sauvegarde pas juste notre modèle, il sauvegarde **l'intelligence complète** :

1. Le `PmuFeatureEngineer` (Calcul des features).
2. Le `preprocessor` (Encodage).
3. Le `model` (XGBoost calibré).

---

### Statistique de validation :

Avec un **AUC > 0.75**, le modèle est considéré comme "performant" dans le domaine hippique (très bruité). Un **LogLoss < 0.25** est également un excellent indicateur de calibration.