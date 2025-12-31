# Documentation Technique : Interface Utilisateur (Frontend)

## 1. Vue d'ensemble

Le module frontend (`frontend/`) constitue la couche de présentation du projet. Il s'agit d'une application web interactive développée avec **Streamlit**, conçue pour consommer les données exposées par l'API Backend.

Son rôle est strictement limité à la visualisation : il ne communique jamais directement avec la base de données PostgreSQL ni avec le moteur de Machine Learning, respectant ainsi le principe de séparation des responsabilités.

## 2. Architecture logicielle

L'application suit une architecture client-serveur légère.

*   **Framework** : Streamlit (Python).
*   **Design Pattern** : l'application est divisée en deux fichiers principaux séparant la logique d'affichage de la logique de récupération des données.
*   **Communication** : requêtes HTTP synchrones vers l'API Backend (`http://127.0.0.1:8000`).

### Structure du code

*   **`frontend/main.py`** : point d'entrée de l'application. Il gère la mise en page, les composants graphiques (widgets), la navigation et l'injection de styles CSS.
*   **`frontend/api_client.py`** : couche de service encapsulant les appels `requests`. Ce module gère la gestion des erreurs réseau et le mécanisme de mise en cache.

## 3. Gestion des données et performance

Pour assurer la fluidité de l'interface et réduire la charge sur l'API, le frontend implémente des mécanismes d'optimisation spécifiques.

### 3.1. Client API (`api_client.py`)
Ce module expose trois fonctions principales mappées sur les endpoints de l'API Backend :
1.  `fetch_daily_races(date_code)` : récupération du programme.
2.  `fetch_participants(race_id)` : récupération des détails statiques (noms, drivers, cotes actuelles).
3.  `fetch_predictions(race_id)` : récupération des probabilités calculées par le modèle ML.

### 3.2. Mise en cache
L'application utilise le décorateur `@st.cache_data` de Streamlit pour stocker temporairement les réponses API en mémoire RAM :
*   **Programme du jour** : cache de 5 minutes (`ttl=300`), car le statut des courses évolue peu.
*   **Prédictions** : cache de 10 minutes (`ttl=600`), car une fois la prédiction générée pour les partants déclarés, elle reste stable.
*   **Participants** : cache de 5 minutes pour rafraîchir les cotes éventuelles.

## 4. Fonctionnalités de l'interface

Le script `main.py` orchestre l'expérience utilisateur à travers plusieurs étapes logiques.

### 4.1. Navigation et filtres
Une barre latérale (sidebar) permet de sélectionner :
1.  **La date** : par défaut à la date du jour.
2.  **La réunion** : filtrage dynamique des courses par hippodrome (ex: R1 - VINCENNES).

### 4.2. Visualisation des courses
Les courses sont présentées sous forme d'onglets (`st.tabs`). Pour chaque course, l'utilisateur visualise les métadonnées essentielles : distance, discipline, nombre de partants et hippodrome.

### 4.3. Déclenchement de l'analyse
L'inférence n'est pas automatique au chargement de la page pour économiser des ressources. Un bouton **"Analyze"** déclenche :
1.  L'appel à l'API de prédiction.
2.  L'appel à l'API des participants (pour récupérer les noms des drivers et entraîneurs).
3.  La fusion (merge) des deux jeux de données via la librairie `pandas`.

### 4.4. Restitution des résultats
Les résultats sont affichés sous deux formes :
*   **Podium prédictif** : les trois chevaux ayant la plus forte probabilité de victoire sont mis en avant avec un code couleur (Or, Argent, Bronze).
*   **Tableau détaillé** : liste complète des partants avec leurs probabilités affichées sous forme de barres de progression.

## 5. Design et ergonomie

Le fichier `main.py` intègre une feuille de style CSS injectée (`st.markdown`) pour surcharger les styles par défaut de Streamlit :
*   **Thème clair forcé** : surcharge des variables de couleur pour garantir la lisibilité sur fond blanc (`#f8f9fa`), indépendamment des préférences système de l'utilisateur.
*   **Composants métriques** : stylisation des cartes de données (bordures, ombres portées) pour un aspect "dashboard" professionnel.

## 6. Lancement

L'application nécessite que l'API Backend soit démarrée au préalable.

**Commande d'exécution :**
```bash
streamlit run frontend/main.py
```

L'application est accessible par défaut sur `http://localhost:8501`.