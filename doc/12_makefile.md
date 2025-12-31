# Guide d'utilisation du Makefile

## Introduction

Le Makefile constitue l’interface principale entre le développeur et l’infrastructure du projet.
Il permet de standardiser les actions et d’éviter l’utilisation directe de commandes longues ou complexes.
Ce document répertorie les différentes commandes pouvant être exécutées.

---

## 1. Principe général


Toutes les commandes s’exécutent via :

    ```bash
    make <commande>
    ```

---

## 2. Commandes principales

- `make up` : démarrer les services Docker en arrière-plan
- `make down` : arrête tous les conteneurs en cours d'exécution
- `make build` : reconstruire les images Docker. A utiliser après une modification du Dockerfile ou des dépendances
- `make clean` : nettoie l'environnement. Supprime les conteneurs, les volumes, les services orphelins
- `make logs` : affiche les logs de tous les services en temps réel

---

## 3. Workflow Machine Learning

- `make train` : entraîne le modèle
- `make ingest`: lance l'ingestion pour les données du jour par défaut
- `make ingest DATE=01012025` : lance l'ingestion pour une date donnée

---

## 4. Tests et qualité du code

- `make test-backend` : tests backend
- `make test-frontend` : tests frontend
- `make test-all` : lance tous les tests
- `make type-check` : vérifications des types (mypy)

---


