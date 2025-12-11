# Documentation des Scripts d'Ingestion (ETL)

Ce document décrit le fonctionnement des scripts Python situés dans le dossier `scripts/`. Ces scripts constituent le pipeline ETL (Extract, Transform, Load) qui alimente la base de données PostgreSQL à partir de l'API du PMU.

## 1. Principes Généraux

*   **Idempotence** : Tous les scripts sont conçus pour être relancés plusieurs fois sans risque. Ils utilisent la clause SQL `ON CONFLICT DO NOTHING` pour éviter les doublons.
*   **Mode "Stealth" (Anti-Ban)** : Pour éviter le blocage par l'API (Erreurs 403), tous les scripts simulent un navigateur réel en injectant des en-têtes HTTP spécifiques (`User-Agent`, `Referer`).
*   **Parallélisme Contrôlé** : Les scripts lourds (Participants, Performances, Rapports) utilisent le **Multithreading** (`ThreadPoolExecutor`) pour traiter plusieurs courses simultanément, tout en respectant une limite de workers et un délai (throttling) pour ne pas surcharger le serveur distant.
*   **Logique "Database-First"** : À l'exception du premier script (Programme), tous les autres interrogent d'abord la base de données pour connaître les courses à traiter.
*   **Gestion des Courses Étrangères** : Le pipeline gère nativement les réponses HTTP 204 (No Content), fréquentes pour les courses internationales sans historique détaillé.

---

## 2. Détail des Scripts

L'ordre d'exécution est strict car les tables sont liées par des clés étrangères.

### Étape 1 : `ingest_programme_day.py` (Architecture)
Ce script est la fondation. Il doit impérativement être exécuté en premier.

*   **Source** : API PMU (JSON 1 - Programme).
*   **Mode** : Séquentiel (une seule requête par jour).
*   **Rôle** : Crée l'arborescence de la journée.
*   **Tables impactées** : `daily_program`, `race_meeting`, `race`.
*   **Commande** :
    ```bash
    python scripts/ingest_programme_day.py --date 05112025
    ```

### Étape 2 : `ingest_participants_day.py` (Acteurs)
*   **Source** : API PMU (JSON 2 - Participants).
*   **Mode** : Parallèle (Multithreadé).
*   **Rôle** : Récupère la liste des partants pour chaque course existante en base.
*   **Tables impactées** : `horse`, `race_participant`.
*   **Commande** :
    ```bash
    python scripts/ingest_participants_day.py --date 05112025
    ```

### Étape 3 : `ingest_performances_day.py` (Historique - Big Data)
C'est le script le plus complexe et le plus optimisé. Il récupère l'historique de carrière (musique) de chaque cheval.

*   **Source** : API PMU (JSON 3 - Performances Détaillées).
*   **Mode** : Hybride (Parallèle + Batch Insert).
*   **Optimisations Techniques** :
    1.  **ThreadPoolExecutor** : Traite ~10 à 12 courses en parallèle.
    2.  **Thread-Safe Caching** : Utilise un `threading.Lock` pour gérer un cache local des IDs de chevaux (`HORSE_CACHE`) partagé entre les threads, réduisant drastiquement les lectures en base.
    3.  **Batch par Course** : Les performances de tous les chevaux d'une même course sont insérées en une seule transaction SQL (`execute_values`).
    4.  **Gestion HTTP 204** : Ignore silencieusement (avec log INFO) les courses sans historique (fréquent sur les réunions R7, R8...).
*   **Tables impactées** : `horse`, `horse_race_history`.
*   **Commande** :
    ```bash
    python scripts/ingest_performances_day.py --date 05112025
    ```

### Étape 4 : `ingest_rapports_day.py` (Résultats)
*   **Source** : API PMU (JSON 4 - Rapports Définitifs).
*   **Mode** : Parallèle (Multithreadé).
*   **Rôle** : Récupère les résultats des paris pour calculer la cible (Target).
*   **Tables impactées** : `race_bet`, `bet_report`.
*   **Commande** :
    ```bash
    python scripts/ingest_rapports_day.py --date 05112025
    ```

---

## 3. Orchestration

Pour simplifier l'utilisation quotidienne, deux scripts "pilotes" sont disponibles.

### A. Ingestion d'une journée complète : `ingest_full_day.py`
Orchestre l'exécution séquentielle des 4 scripts. Gère les dépendances et arrête le processus en cas d'erreur critique sur le programme.

**Usage recommandé au quotidien :**
```bash
python scripts/ingest_full_day.py --date 05112025
```

### B. Ingestion d'une période (Backfill) : `ingest_range.py`
Permet de rattraper l'historique sur une plage de dates.

**Usage pour l'historique :**
```bash
python scripts/ingest_range.py --start 01112025 --end 30112025
```

---

## 4. Dépannage Rapide

| Symptôme | Cause Probable | Solution |
| :--- | :--- | :--- |
| **Erreur 403 (Forbidden)** | Détection de Bot | Les headers `User-Agent` ne sont pas à jour ou le script tourne trop vite. Réduire `MAX_WORKERS` ou augmenter `REQUEST_DELAY`. |
| **"Found 0 races"** | Programme manquant | Vérifier que `ingest_programme_day.py` a bien tourné pour cette date. |
| **Logs "HTTP 204"** | Course étrangère/vide | **Comportement normal**. Le script ignore les courses sans données JSON (souvent R8, R9, etc.). |
| **Erreur SSL/Connection** | Instabilité réseau | Le script gère les retries basiques, mais une coupure internet stoppera le thread. Relancer le script (il est idempotent). |

---

## 5. Configuration Recommandée (Performance vs Sécurité)

Pour modifier la vitesse d'ingestion, ajustez les constantes en haut des scripts Python :

*   **Standard (Sûr)** : `MAX_WORKERS = 5`, `REQUEST_DELAY = 0.1`
*   **Rapide (Optimisé)** : `MAX_WORKERS = 12`, `REQUEST_DELAY = 0.05` (Configuration actuelle recommandée).
*   **Risqué** : `MAX_WORKERS > 20` (Risque élevé de ban IP temporaire).