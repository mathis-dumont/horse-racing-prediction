# 🏇 Guide d'Utilisation : Docker & Automation avec Makefile

Afin de rendre l'application portable, la conteneurisation est utilisée dans ce projet. Elle permet d'exécuter le code dans un environnement identique, du système d'exploitation (OS) aux bibliothèques Python, quelle que soit la machine hôte.

L'utilisation du **Makefile** est fortement recommandée car elle encapsule les commandes Docker complexes et gère les problématiques de caches et de permissions.

---

## 🛠️ Prérequis

1. **Docker Desktop** doit être installé et lancé.
2. L'utilitaire **`make`** doit être installé sur votre machine.
3. Le fichier **`.env`** doit être présent à la racine avec vos identifiants Supabase :
```ini
DB_URL=postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres

```



---

## 🏗️ 1. Initialisation et Build

Avant de commencer, il est conseillé de nettoyer l'environnement pour éviter les conflits de cache.

**Commande :** `make clean`

> **Équivalent Docker :** `docker-compose down -v --remove-orphans` + `sudo rm -rf` (sur les dossiers de cache).

* *Action :* Arrête les conteneurs, supprime les volumes (Base de données) et nettoie les fichiers de cache Python créés par Docker sur l'hôte.

**Commande :** `make build-nc`

> **Équivalent Docker :** `docker-compose build --no-cache`

* *Action :* Force la reconstruction complète des images sans utiliser le cache, garantissant que les dernières versions des dépendances sont installées.

---

## 🧠 2. Entraînement du Modèle ML

Le backend a besoin d'un modèle entraîné (`.pkl`) pour fonctionner. Puisque la base contient déjà l'historique, nous pouvons générer le modèle immédiatement.

**Commande :** `make train`

> **Équivalent Docker :** `docker-compose run --rm backend python -m src.ml.trainer`

* *Action :* Crée un conteneur éphémère qui se connecte à Supabase, traite les données, génère `model_calibrated.pkl` et le sauvegarde sur votre disque local via un volume partagé.

---

## 🧪 3. Exécution des Tests

L'architecture de test est isolée. Cela permet de valider le code sans dépendre de l'état réel du serveur.

**Commande :** `make test-all`

> **Équivalents Docker :**
> * Backend : `docker-compose run --rm backend pytest tests/ -v`
> * Frontend : `docker-compose run --rm -e PYTHONPATH=/app frontend pytest tests/ -v`
> 
> 

* *Action :* Lance les tests unitaires et d'intégration. Notez l'injection de `PYTHONPATH` pour le frontend afin de garantir la découverte des modules internes dans le conteneur.

---

## 💾 4. Ingestion de nouvelles données

Si vous souhaitez mettre à jour la base de données avec les courses du jour :

**Commande :** `make ingest DATE=31122025`

> **Équivalent Docker :** `docker-compose run --rm backend python -m src.cli.etl --date 31122025 --type all`

* *Action :* Lancez le script ETL pour récupérer les données PMU à une date précise et les injecter dans la base de données.

---

## 🚀 5. Lancement de l'Application

Une fois le modèle entraîné, lancez l'interface utilisateur et l'API.

**Commande :** `make up`

> **Équivalent Docker :** `docker-compose up -d`

* *Action :* Démarre les services en arrière-plan.

**Accès aux services :**

* **Interface UI (Streamlit) :** [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)
* **Documentation API (Swagger) :** [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)
* **Suivi des logs :** `make logs` (équivalent : `docker-compose logs -f`)

---

## 🔍 Dépannage

| Problème | Cause probable | Solution |
| --- | --- | --- |
| **`ml_engine: failed`** | Fichier `.pkl` absent | `make train` puis `docker-compose restart backend` |
| **Permissions caches** | Fichiers créés par `root` | `make clean` pour forcer la suppression via `sudo` |
| **Erreur de connexion DB** | Mauvais `.env` | Vérifier que le mot de passe est celui de la DB Supabase |

---