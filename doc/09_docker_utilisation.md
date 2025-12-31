# Guide d'utilisation de Docker

Afin de rendre l'application portable, la conteneurisation est utilisée dans ce projet. Elle permet d'exécuter le code dans un environnement identique, du système d'exploitation (OS) aux bibliothèques Python, quelle que soit la machine hôte.

---

## Prérequis

1.  **Docker Desktop** doit être installé et lancé.
2.  Le fichier **`.env`** doit contenir les identifiants de la base de données Supabase :
    ```ini
    DB_URL=postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres
    ```

---

## 1. Entraînement du Modèle

Puisque la base contient déjà 5 ans d'historique, nous pouvons entraîner le modèle immédiatement.

**Commande :**
```bash
docker-compose run --rm backend python src/ml/trainer.py

```

**Ce que cela fait :**

* Le conteneur se connecte à Supabase.
* Il télécharge les données d'entraînement (attention : cela peut prendre quelques minutes selon votre connexion internet car le volume de données est important).
* Il génère le fichier `model_calibrated.pkl` et le sauvegarde sur votre disque local via le volume Docker.

> **Note :** Si le script crash par manque de mémoire (car 5 ans de données c'est lourd), nous devrons ajuster le `trainer.py` pour charger moins d'années.

---

## 2. Exécution des Tests

Une fois le modèle généré, le fonctionnement de l'application peut être validé via des tests.
L'architecture de test est conçue pour être isolée. Le Backend utilise unittest.mock pour simuler la base de données (Supabase), et le Frontend utilise Streamlit AppTest en simulant les réponses de l'API. Cela permet de valider le code sans dépendre de la connexion internet ou de l'état du serveur.

**Tests Backend :**

```bash
docker-compose run --rm backend pytest tests/test_api.py -v

```

**Tests Frontend :**

```bash
docker-compose run --rm frontend pytest tests/test_main.py -v

```

---


---

## 3. Lancement de l'Application

Lancez l'interface utilisateur et l'API.

**Commande :**

```bash
docker-compose up --build

```

**Accès :**

* **Frontend (Streamlit) :** [http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)
* **Backend (API) :** [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)

---

## Dépannage Supabase

**Erreur : `FATAL: password authentication failed**`
Vérifiez que vous utilisez bien le mot de passe de la base de données (Database Password) et non celui de votre compte Supabase.

**Erreur : `OperationalError: SSL connection has been closed unexpectedly**`
Supabase ferme parfois les connexions inactives. Relancez simplement la commande.

**Lenteur extrême lors de l'entraînement**
Si le téléchargement des données depuis Supabase est trop lent pour l'entraînement, il faudra envisager de faire un "Dump" de la base Supabase pour la restaurer en local, mais essayez d'abord en direct.