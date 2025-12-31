# Guide d’utilisation – Ingestion journalière

Ce document décrit le fonctionnement de l’ingestion journalière des données, exécutée via un workflow GitHub Actions.

---

## 1. Principe général

L’ingestion des données repose sur un workflow automatisé permettant :
- une exécution quotidienne planifiée,
- une exécution manuelle avec une date spécifique.

Le pipeline assure une ingestion robuste et reproductible des données nécessaires au système.

---

## 2. Modes de déclenchement

**Mode automatique (planifié) :** 

Le workflow s’exécute automatiquement tous les jours à 06:00 UTC. Il utilise une fenêtre glissante de trois jours :
- J-2
- J-1
- J (jour courant)

Ce mécanisme permet de gérer les retards de données et d’assurer la complétude des jeux de données.


**Mode manuel (à la demande) :** 

Le workflow peut être déclenché manuellement avec une date spécifique au format `DDMMYYYY`. Dans ce cas, seule la journée indiquée est traitée.

---

## 3. Calcul de la plage de dates

**Cas 1 — Date fournie manuellement**

Lorsque la date est fournie :
- le mode `single` est activé
- une seule journée est ingérée

Exemple :

    DATE = 01012025


**Cas 2 — Exécution automatique**

Lorsque aucune date n’est fournie :
- le mode `range` est activé
- la plage utilisée est :

    START = J - 2  
    END   = J  

Cela garantit une ingestion robuste même en cas de retard de données.

---

## 4. Exécution du script d’ingestion

Le script principal exécuté est :
    ```bash
    python backend/src/cli/etl.py
    ```
Selon le mode, les arguments utilisés sont :

**Mode simple :** `--type all --date <DATE>`
**Mode plage :** `--type all --range <START> <END>`

Le script se charge de :
- l’extraction des données,
- leur transformation,
- leur stockage dans la base cible.

---

## 5. Environnement d’exécution

L’exécution se fait dans un environnement contrôlé via GitHub Actions :

- Python 3.12
- Dépendances installées depuis `backend/requirements.txt`
- Variable d’environnement `DB_URL` injectée via les secrets GitHub
- `PYTHONPATH` configuré pour accéder aux modules du backend

---