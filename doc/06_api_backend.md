# Documentation Technique : API REST & Inférence

## 1. Vue d'ensemble

L'API (`src/api`) est le cœur applicatif du projet. Elle expose les données hippiques et fournit désormais des services de **prédiction en temps réel** grâce à l'intégration du modèle de Machine Learning.

Elle est construite avec **FastAPI** pour la performance et **Pydantic** pour la validation stricte des données.

## 2. Architecture Logicielle

L'API respecte une architecture en couches (Clean Architecture) :

1.  **Entrypoint (`main.py`)** : Gestion du cycle de vie (`Lifespan`), Injection de dépendances et définition des Routes.
2.  **Schemas (`schemas.py`)** : Contrats d'interface (DTOs) pour les entrées/sorties.
3.  **Repositories (`repositories.py`)** : Couche d'accès aux données (SQL pur).
4.  **Inference Engine (`src/ml/predictor.py`)** : Couche d'intelligence artificielle.

## 3. Intégration du Machine Learning

### 3.1. Gestion du cycle de vie (Lifespan)
Le chargement d'un modèle de Machine Learning est coûteux en ressources. Pour éviter de le charger à chaque requête :
*   Le modèle est chargé **une seule fois** au démarrage de l'API (événement `startup`).
*   Il est stocké dans une variable globale `ml_models` en mémoire RAM.
*   Si le fichier `.pkl` est absent, l'API démarre en mode "dégradé" (les routes de prédiction renvoient une erreur 503, mais les données restent accessibles).

### 3.2. Le Predictor
La classe `RacePredictor` fait le pont entre l'API et le pipeline ML.
*   Elle reçoit une liste de participants bruts (dictionnaires).
*   Elle les convertit en DataFrame Pandas.
*   Elle interroge le pipeline (`model.predict_proba`).
*   Elle gère les erreurs silencieusement (logging) pour ne pas crasher le serveur.

## 4. Points d'accès (Endpoints)

### A. Consultation des Données (Lecture)

*   **`GET /races/{date_code}`** : Récupère le programme d'une journée.
*   **`GET /races/{race_id}/participants`** : Récupère les partants, drivers et cotes simples.

### B. Prédictions (Intelligence Artificielle)

*   **URL** : `/races/{race_id}/predict`
*   **Méthode** : `GET`
*   **Description** : Analyse une course et prédit le classement probable.

**Flux de traitement de la requête :**
1.  **Repository** : La méthode `get_race_data_for_ml(race_id)` extrait un dataset enrichi (contexte météo, historique complet des chevaux, musique...).
2.  **Predictor** : Le modèle calcule la probabilité de victoire (score entre 0 et 1).
3.  **Post-Processing** :
    *   L'API trie les chevaux par probabilité décroissante.
    *   Un rang prédit (`predicted_rank`) est attribué (1er, 2ème, etc.).
4.  **Réponse JSON** :
    ```json
    [
      {
        "pmu_number": 12,
        "horse_name": "IDAO DE TILLARD",
        "win_probability": 0.45,
        "predicted_rank": 1
      },
      ...
    ]
    ```

## 5. Démarrage

**Commande de lancement :**
```bash
uvicorn src.api.main:app --reload
```

**Documentation Swagger UI :**
Disponible à l'adresse `http://127.0.0.1:8000/docs`.