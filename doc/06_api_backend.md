# Architecture de l'API REST (FastAPI)

## 1. Vue d'ensemble

L'interface de programmation (API) permet d'exposer les données consolidées dans la base PostgreSQL aux applications clientes (frontend, scripts d'analyse). Elle est développée avec le framework **FastAPI**.

Le code source de l'API se situe dans le répertoire `src/api/`.

## 2. Choix d'architecture

L'API suit une architecture en couches stricte pour séparer les responsabilités :

1.  **Couche Routeur (`main.py`)** : gère les points d'entrée HTTP et la validation des paramètres.
2.  **Couche Contrôleur/Service** : (intégrée ici via l'injection de dépendance) fait le lien entre la requête et les données.
3.  **Couche Répository (`repositories.py`)** : contient exclusivement la logique d'accès aux données (SQL). Aucune requête SQL ne doit apparaître dans le routeur.
4.  **Couche Schéma (`schemas.py`)** : définit le format des données échangées (DTO - Data Transfer Objects) via **Pydantic**.

## 3. Composants détaillés

### 3.1. Routeur (`main.py`)
Le fichier `main.py` initialise l'application `app = FastAPI()`. Il définit les routes (endpoints) disponibles.
*   Il utilise l'injection de dépendances (`Depends`) pour instancier le `RaceRepository`. Cela facilite les tests et la gestion du cycle de vie des connexions.
*   Il délègue la logique métier au repository et retourne des objets validés par les schémas Pydantic.

### 3.2. Pattern Repository (`repositories.py`)
La classe `RaceRepository` encapsule toutes les interactions avec la base de données.
*   Elle utilise le singleton `DatabaseManager` (défini dans `src/core/database.py`) pour obtenir une connexion du pool.
*   Elle exécute les requêtes SQL brutes.
*   Elle utilise `psycopg2.extras.RealDictCursor` pour retourner les résultats sous forme de dictionnaires, directement mappables vers les modèles Pydantic.
*   Elle gère la fermeture propre des connexions dans un bloc `finally`.

### 3.3. Schémas de données (`schemas.py`)
Les classes héritant de `BaseModel` définissent la structure des réponses JSON.
*   **`RaceSummary`** : expose les informations essentielles d'une course (id, numéro, discipline, distance).
*   **`ParticipantSummary`** : expose les détails d'un partant (nom du cheval, driver, entraîneur, cote).
*   L'utilisation de `Optional` et le typage strict garantissent que l'API documente clairement les champs pouvant être nuls.

## 4. Points d'accès (Endpoints)

L'API expose actuellement les ressources suivantes en lecture seule (GET) :

### Liste des courses d'une journée
*   **URL** : `/races/{date_code}`
*   **Méthode** : `GET`
*   **Paramètre** : `date_code` (format JJMMAAAA).
*   **Réponse** : liste d'objets `RaceSummary`.
*   **Usage** : permet d'afficher le calendrier des réunions et courses pour une date donnée.

### Détail des participants d'une course
*   **URL** : `/races/{race_id}/participants`
*   **Méthode** : `GET`
*   **Paramètre** : `race_id` (identifiant unique interne de la base de données).
*   **Réponse** : liste d'objets `ParticipantSummary`.
*   **Usage** : permet d'afficher la liste des partants, les couples cheval/driver et les cotes en direct.

## 5. Démarrage et Documentation

L'API est servie par **Uvicorn**, un serveur ASGI performant.

**Commande de lancement (mode développement) :**
```bash
uvicorn src.api.main:app --reload
```

**Documentation interactive :**
FastAPI génère automatiquement une documentation conforme au standard OpenAPI (Swagger). Une fois le serveur lancé, elle est accessible à l'adresse :
`http://127.0.0.1:8000/docs`

Cette interface permet de tester les endpoints directement depuis le navigateur sans écrire de code client.

## 6. Évolutions futures (Intégration ML)

L'API actuelle constitue le socle technique pour l'exposition des données. Elle a vocation à évoluer pour intégrer la couche d'intelligence artificielle (Phase 8 et 9 du projet).

### 6.1. Stratégie d'inférence
Une fois les modèles entraînés, ils seront chargés en mémoire au démarrage de l'API ou à la demande.

### 6.2. Futurs Endpoints de Prédiction
L'architecture actuelle sera étendue pour inclure un service de prédiction. De nouvelles routes seront ajoutées :

*   **POST /predict/race/{race_id}** :
    *   Récupère les données brutes de la course via le `RaceRepository`.
    *   Transforme les données (Feature Engineering) via un pipeline interne identique à celui de l'entraînement.
    *   Interroge le modèle ML chargé.
    *   Retourne les probabilités de victoire pour chaque partant.

*   **GET /predictions/best-of-day** :
    *   Retourne les "meilleures chances" calculées pour l'ensemble des réunions de la journée.

Cette approche centralisée garantit que l'API reste le point d'entrée unique pour le frontend, simplifiant ainsi la maintenance et le déploiement.