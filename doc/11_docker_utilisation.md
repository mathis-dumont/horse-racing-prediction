```markdown
# 🐳 Guide d'Utilisation Docker - PMU Predictor

Ce document explique comment utiliser Docker pour gérer toutes les étapes du projet : de l'entraînement du modèle IA jusqu'au déploiement de l'interface utilisateur, en passant par les tests unitaires.

---

## 📋 Prérequis

1.  **Docker Desktop** doit être installé et lancé.
2.  Le fichier **`.env`** doit être présent à la racine du projet avec la configuration suivante (sans guillemets !) :
    ```ini
    # Exemple de contenu pour .env
    DATABASE_URL=postgresql://postgres:PASSWORD@host.docker.internal:5432/pmu_database
    ```

---

## 🚀 1. Entraînement du Modèle (Machine Learning)

Avant de lancer l'API, il est impératif d'entraîner le modèle pour générer le fichier `model_calibrated.pkl`. Nous utilisons un conteneur éphémère pour cela.

**Commande :**
```bash
docker-compose run --rm backend python src/ml/trainer.py

```

**Ce que cela fait :**

* Lance un conteneur basé sur l'image `backend`.
* Monte le volume `./backend/data` pour que le fichier `.pkl` généré soit sauvegardé sur votre machine hôte.
* Connecte le conteneur à votre base de données locale via `host.docker.internal`.
* Supprime le conteneur automatiquement (`--rm`) une fois le script terminé.

---

## 🧪 2. Exécution des Tests (Quality Assurance)

## 🖥️ 2.a. Tests Backend

Pour valider que le code fonctionne correctement **dans l'environnement de production** (Python 3.12, Pandas 2.2.3, etc.), lancez les tests via Docker.

**Commande :**

```bash
docker-compose run --rm backend pytest tests/test_api.py -v

```

**Résultat attendu :**
Vous devriez voir `5 passed` (ou plus selon vos ajouts).

* Si vous voyez des warnings `InconsistentVersionWarning`, c'est que vous n'avez pas ré-entraîné le modèle (voir Étape 1).

---
---

## 🖥️ 2.b. Tests Frontend (Interface Streamlit)

Une fois le backend validé, vous pouvez vérifier le bon fonctionnement de l'interface utilisateur sans même ouvrir un navigateur. Ces tests simulent le lancement de l'application et vérifient que les éléments s'affichent correctement.

**Commande :**
```bash
docker-compose run --rm frontend pytest tests/test_main.py -v

## 🌐 3. Lancement de l'Application (Backend + Frontend)

Une fois le modèle entraîné et les tests validés, lancez l'ensemble de la stack.

**Commande :**

```bash
docker-compose up --build

```

*(L'option `--build` force la reconstruction des images si vous avez modifié le code ou les requirements).*

**Accès aux services :**

* **Backend (Swagger UI) :** [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)
* *Utilisez l'endpoint `/bets/sniper/{date}` pour tester les prédictions.*


* **Frontend (Streamlit) :** [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)

Pour arrêter les services : `CTRL + C`.

---

## 🛠️ Commandes Utiles & Dépannage

### Nettoyer l'environnement

Si vous voulez tout arrêter et supprimer les conteneurs créés par Compose :

```bash
docker-compose down

```

### Accéder au shell du conteneur

Si vous avez besoin de déboguer à l'intérieur du conteneur backend :

```bash
docker-compose run --rm backend /bin/bash

```

### Problèmes courants

**Erreur : `FATAL: password authentication failed**`

* Vérifiez votre fichier `.env`.
* Assurez-vous qu'il n'y a **pas de guillemets** autour de l'URL (`""`).
* Vérifiez que votre base PostgreSQL locale accepte les connexions.

**Erreur : `Model file not found**`

* Le script `trainer.py` n'a pas été lancé (Étape 1).
* Ou le volume Docker n'est pas correctement monté (vérifiez le `docker-compose.yml` section `volumes`).

**Erreur : `Connection refused` (Database)**

* Assurez-vous d'utiliser `host.docker.internal` dans votre `.env` et non `localhost` ou `127.0.0.1`.

```

```