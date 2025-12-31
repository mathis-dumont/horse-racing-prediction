# Documentation Technique : Pipeline Machine Learning

Ce document décrit l'architecture du module d'apprentissage automatique (`backend/src/ml`). Contrairement aux scripts séquentiels classiques, ce projet utilise une approche **Pipeline** intégrée, garantissant que les transformations appliquées lors de l'entraînement sont rigoureusement identiques à celles utilisées lors de la prédiction (inférence).

## 1. Vue d'ensemble du flux

Le processus ML est encapsulé dans le package `src.ml` et suit ces étapes :

1.  **Loader** (`loader.py`) : Extraction complexe SQL et fusion des données historiques.
2.  **Feature Engineering** (`features.py`) : Transformateur scikit-learn personnalisé pour créer les variables mathématiques.
3.  **Training** (`trainer.py`) : Entraînement du modèle XGBoost et sérialisation.
4.  **Inference** (`predictor.py`) : Chargement du modèle et prédiction en temps réel.

---

## 2. Extraction des Données (`loader.py`)

La classe `DataLoader` gère la récupération des données depuis PostgreSQL. Elle évite la création de CSV intermédiaires en chargeant les données directement en DataFrames pandas.

### Stratégie de Fusion
Le loader exécute deux requêtes majeures :
1.  **Main Dataset** : Récupère les participations (Course + Cheval + Contexte).
2.  **History Dataset** : Récupère l'historique complet des courses passées.

Il effectue ensuite une agrégation (Group By) sur l'historique pour calculer des statistiques "à vie" (gains totaux, record de vitesse, taux de réussite) et fusionne ces stats avec le dataset principal.

---

## 3. Ingénierie des Caractéristiques (`features.py`)

La transformation des données est gérée par la classe `PmuFeatureEngineer`, qui hérite de `TransformerMixin` de Scikit-Learn. Cela permet d'intégrer le nettoyage directement dans le modèle final.

### Transformations Appliquées

1.  **Gestion Temporelle & Âge** :
    *   Calcul de l'âge exact du cheval au moment de la course (`program_date` - `birth_year`).
    *   Extraction du mois et du jour de la semaine (saisonnalité).

2.  **Imputation (Valeurs Manquantes)** :
    *   Variables numériques (Gains, Courses) : Remplacées par `0`.
    *   Variables catégorielles (Jockey, Ferrure) : Remplacées par `"UNKNOWN"`.

3.  **Métriques Relatives (Contextuelles)** :
    *   *Ces calculs sont cruciaux car ils comparent un cheval à ses concurrents du jour.*
    *   `winnings_rank_in_race` : Rang du cheval dans la course en termes de gains carrière.
    *   `relative_winnings` : Ratio (Gains du cheval / Moyenne des gains de la course).
    *   `odds_rank_in_race` : Classement du cheval selon la cote de référence (PMU).

---

## 4. Entraînement (`trainer.py`)

La classe `XGBoostTrainer` orchestre l'apprentissage.

### Le "Super Pipeline"
Le modèle sauvegardé n'est pas juste l'algorithme XGBoost. C'est un pipeline composite :

```python
Pipeline([
    ('engineer', PmuFeatureEngineer()),  # 1. Création des features (Ratios, Rangs...)
    ('training_pipeline', Pipeline([     # 2. Pipeline technique
        ('preprocessor', ColumnTransformer(...)), # Encodage (OrdinalEncoder)
        ('model', XGBClassifier(...))             # Algorithme Gradient Boosting
    ]))
])
```

**Avantage :** Lors de l'utilisation dans l'API, nous envoyons des données brutes au modèle. Le pipeline s'occupe de recréer les features, encoder les catégories et prédire. Aucune logique n'est dupliquée.

### Sortie
Le script génère un fichier binaire sérialisé : `data/model_xgboost.pkl`.

---

## 5. Exécution

Pour lancer un ré-entraînement complet du modèle :

```bash
# Depuis le dossier 'backend/' :
python -m src.ml.trainer
```