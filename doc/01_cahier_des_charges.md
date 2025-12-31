# Cahier des Charges - Projet de Prédiction de Courses Hippiques

## 1. Introduction et Contexte

### 1.1. Objet du document
Ce document constitue le cahier des charges pour le projet de développement d'un système d'analyse et de prédiction des résultats de courses hippiques. Il a pour but de définir de manière formelle le périmètre, les objectifs, les spécifications fonctionnelles et non-fonctionnelles, ainsi que les contraintes techniques du projet.

### 1.2. Contexte du projet
Les courses hippiques représentent un domaine complexe où les résultats dépendent d'un grand nombre de variables (performance du cheval, conditions de course, compétence du jockey/driver, etc.). L'analyse manuelle de ces facteurs est fastidieuse et subjective. Ce projet vise à exploiter les techniques de collecte de données et d'apprentissage automatique (Machine Learning) pour modéliser ces interactions et proposer des prédictions objectives sur l'issue des courses.

La source de données principale sera l'interface de programmation (API) non officielle du PMU, qui fournit des informations détaillées sur les programmes, les participants et les résultats.

### 1.3. Objectifs principaux
Le projet poursuit quatre objectifs majeurs :
1.  **Automatiser la collecte** : Mettre en place un système robuste pour l'ingestion quotidienne et historique des données de courses hippiques.
2.  **Stocker et structurer** : Organiser les données collectées dans une base de données relationnelle, normalisée et performante.
3.  **Modéliser et prédire** : Développer un ou plusieurs modèles d'apprentissage automatique capables de prédire les performances des chevaux avec une précision mesurable.
4.  **Restituer et valoriser** : Présenter les prédictions et les analyses de performance du modèle via une interface web accessible et intuitive.

### 1.4. Périmètre du projet
#### Inclusions
*   **Source de données** : Utilisation exclusive de l'API `online.turfinfo.api.pmu.fr`.
*   **Discipline** : Le périmètre initial se concentre sur les courses de **Trot (attelé et monté)**, réputées plus structurées pour une première approche.
*   **Fonctionnalités** : Le système couvrira l'ensemble du pipeline, de l'ingestion des données au déploiement d'une interface web de consultation.
*   **Historique** : Constitution d'un jeu de données couvrant au minimum les cinq dernières années.

#### Exclusions (pour la version 1.0)
*   **Autres disciplines** : Les courses de Galop (plat, obstacles) ne sont pas incluses dans cette version.
*   **Autres sources de données** : L'intégration de données provenant d'autres opérateurs (ex: Zeturf, Geny) n'est pas prévue.
*   **Gestion d'utilisateurs** : Le site web ne comportera ni système d'authentification ni espace personnel.
*   **Prise de paris** : Le système est un outil d'aide à la décision et n'intègre aucune fonctionnalité de pari en ligne.

## 2. Spécifications Fonctionnelles (SF)

### 2.1. Module d'ingestion de données
*   **SF-ING-010** : Le système doit pouvoir collecter, pour une date donnée, l'intégralité des programmes, réunions et courses (source JSON 1).
*   **SF-ING-020** : Le système doit collecter les informations détaillées de chaque participant pour chaque course (source JSON 2).
*   **SF-ING-030** : Le système doit collecter l'historique de performance de chaque participant (source JSON 3).
*   **SF-ING-040** : Le système doit collecter les rapports de paris définitifs après la fin de chaque course (source JSON 4).
*   **SF-ING-050** : Le système doit être capable d'exécuter les ingestions de manière rétroactive sur une plage de dates spécifiée.

### 2.2. Module de stockage (Base de données)
*   **SF-STO-010** : Les données doivent être stockées dans une base de données PostgreSQL en respectant le schéma relationnel défini en annexe.
*   **SF-STO-020** : Les opérations d'ingestion doivent être idempotentes : une exécution répétée sur la même date ne doit pas créer de doublons mais mettre à jour les enregistrements existants.
*   **SF-STO-030** : Le système doit archiver les fichiers JSON bruts de chaque source pour garantir la traçabilité et permettre une ré-ingestion future.

### 2.3. Module d'apprentissage automatique (ML)
*   **SF-ML-010** : Le système doit permettre la construction d'un jeu de données consolidé en agrégeant les informations des différentes tables.
*   **SF-ML-020** : Le système doit appliquer des techniques d'ingénierie des caractéristiques pour transformer les données brutes en variables prédictives pertinentes.
*   **SF-ML-030** : Le système doit permettre l'entraînement et l'évaluation comparative de plusieurs modèles d'apprentissage automatique.
*   **SF-ML-040** : Chaque modèle entraîné doit être sauvegardé et versionné pour assurer la reproductibilité des prédictions.
*   **SF-ML-050** : Le modèle doit générer, pour chaque participant, a minima une probabilité de victoire et une probabilité de se classer dans les trois premiers.

### 2.4. Module d'exposition (API)
*   **SF-API-010** : Une API REST doit être développée pour exposer les prédictions.
*   **SF-API-020** : L'API doit proposer un point d'accès (endpoint) pour récupérer les prédictions de toutes les courses d'une journée.
*   **SF-API-030** : L'API doit proposer un point d'accès pour récupérer les prédictions d'une course spécifique.
*   **SF-API-040** : Les réponses de l'API doivent être au format JSON.

### 2.5. Interface utilisateur (Site Web)
*   **SF-WEB-010** : Un site web public doit être développé pour présenter le projet.
*   **SF-WEB-020** : Le site doit afficher la liste des courses du jour et les prédictions associées générées par le modèle.
*   **SF-WEB-030** : Le site doit permettre de consulter les résultats des courses passées et de comparer les prédictions du modèle avec les arrivées réelles.
*   **SF-WEB-040** : Le site doit inclure une section décrivant la méthodologie du projet et les indicateurs de performance du modèle.

## 3. Spécifications Non-Fonctionnelles (SNF)

### 3.1. Performance
*   **SNF-PERF-010** : Le temps d'ingestion des données pour une journée complète doit être inférieur à 15 minutes.
*   **SNF-PERF-020** : Le temps de réponse de l'API pour une requête de prédictions doit être inférieur à 2 secondes.
*   **SNF-PERF-030** : Le temps de chargement initial des pages principales du site web doit être inférieur à 3 secondes.

### 3.2. Fiabilité et disponibilité
*   **SNF-REL-010** : Le processus d'ingestion automatisé doit gérer les erreurs réseau et les indisponibilités temporaires de l'API source sans interrompre le service.
*   **SNF-REL-020** : Un système de journalisation (logging) centralisé doit être mis en place pour toutes les composantes du projet.
*   **SNF-REL-030** : L'API et le site web doivent viser une disponibilité de 99 %.

### 3.3. Maintenabilité et évolutivité
*   **SNF-MAINT-010** : Le code source doit être modulaire, commenté et suivre les standards de qualité du langage Python (PEP 8).
*   **SNF-MAINT-020** : L'architecture doit faciliter l'ajout de nouvelles caractéristiques au modèle sans nécessiter une refonte majeure.
*   **SNF-MAINT-030** : Le système doit être conçu pour permettre, à terme, l'intégration de nouvelles disciplines (Galop) ou de nouvelles sources de données.

### 3.4. Sécurité
*   **SNF-SEC-010** : Les informations sensibles (identifiants de base de données, clés d'API) doivent être gérées via des variables d'environnement et ne jamais être inscrites en dur dans le code source.

## 4. Contraintes techniques

*   **Langage de programmation** : Python (version 3.8 ou supérieure).
*   **Base de données** : PostgreSQL.
*   **Frameworks** :
    *   API : FastAPI.
    *   Interface Web : Streamlit, React, ou Vue.js.
*   **Hébergement** :
    *   Base de données : Supabase.
    *   Application (API et site web) : Render, Railway, ou un serveur privé virtuel (VPS).
*   **Gestion de version** : Git.

## 5. Livrables

1.  **Code source** : Dépôt Git complet contenant l'ensemble du code de l'application.
2.  **Scripts de base de données** : Script SQL pour l'initialisation du schéma.
3.  **Modèle d'apprentissage automatique** : Fichiers du modèle entraîné et versionné.
4.  **Documentation** :
    *   `README.md` pour l'installation et l'utilisation.
    *   `01_cahier_des_charges.md` (ce document).
    *   `02_architecture_bdd.md` décrivant le schéma de la base de données.
5.  **Application déployée** :
    *   URL de l'API fonctionnelle.
    *   URL du site web public et accessible.

## 6. Glossaire

*   **API (Application Programming Interface)** : Interface de programmation permettant à deux applications de communiquer entre elles.
*   **Ingestion** : Processus de collecte, transformation et chargement des données depuis une source externe vers la base de données.
*   **Idempotence** : Propriété d'une opération qui peut être appliquée plusieurs fois sans changer le résultat au-delà de l'application initiale.
*   **Ingénierie des caractéristiques (Feature Engineering)** : Processus de création de nouvelles variables prédictives à partir des données brutes existantes.
*   **Pipeline** : Chaîne de traitement des données, de la collecte à la prédiction.