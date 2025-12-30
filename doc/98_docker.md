# Introduction à la Conteneurisation avec Docker

Ce document sert de guide technique pour l'initialisation et l'utilisation de Docker dans un contexte de Data Science. Il vise à fournir une compréhension architecturale et pratique de la conteneurisation pour garantir la **reproductibilité** et la **portabilité** des environnements de développement et de déploiement.

---

## 📑 Table des Matières
1. [Pourquoi Docker en Data Science ?](#1-pourquoi-docker-en-data-science-)
2. [Architecture et Concepts Clés](#2-architecture-et-concepts-clés)
3. [Installation et Prérequis](#3-installation-et-prérequis)
4. [Workflow Standard : Build, Ship, Run](#4-workflow-standard--build-ship-run)
5. [Cas Pratique : Conteneurisation d'un Script Python](#5-cas-pratique--conteneurisation-dun-script-python)
6. [Gestion des Données (Volumes)](#6-gestion-des-données-volumes)

---

## 1. Pourquoi Docker en Data Science ?

La "Crise de la Reproductibilité" est un enjeu majeur. Un modèle entraîné sur une machine locale avec `scikit-learn 0.24` peut échouer en production si l'environnement cible utilise la version `1.0`.

Docker résout ce problème par l'**isolation** et l'**immutabilité** :
* **Reproductibilité Stricte :** Le code s'exécute dans un environnement identique, du système d'exploitation (OS) aux bibliothèques Python, quelle que soit la machine hôte.
* **Portabilité :** Une image Docker peut être déployée indifféremment sur un laptop, un serveur on-premise, ou dans le Cloud (AWS ECS, Google Kubernetes Engine).
* **Isolation des dépendances :** Permet de faire cohabiter plusieurs projets nécessitant des versions de Python ou de CUDA conflictuelles sur la même machine.

---

## 2. Architecture et Concepts Clés

Contrairement à une Machine Virtuelle (VM) qui virtualise le matériel (hardware) et embarque un OS complet (lourd), Docker utilise la **virtualisation au niveau de l'OS**. Les conteneurs partagent le noyau (kernel) de la machine hôte mais isolent les processus utilisateurs.

### Terminologie
* **Docker Daemon (`dockerd`) :** Processus en arrière-plan qui gère les objets Docker (images, conteneurs, réseaux).
* **Image :** Un artefact binaire **immuable** et en lecture seule. C'est le "template" contenant le code source, les bibliothèques, les dépendances et l'OS minimal (ex: Alpine, Debian Slim).
* **Conteneur (Container) :** Une instance d'exécution (runtime) d'une image. C'est un environnement éphémère et isolé.
* **Dockerfile :** Fichier de configuration déclaratif décrivant les instructions pour assembler une image.
* **Registry :** Dépôt centralisé (ex: Docker Hub, AWS ECR) pour stocker et versionner les images.

---

## 3. Installation et Prérequis

Assurez-vous que le **Docker Engine** est installé et actif sur votre poste.

* **Vérification de l'installation :**
    ```bash
    docker info
    # Doit retourner les détails du Client et du Server sans erreur
    ```

---

## 4. Workflow Standard : Build, Ship, Run

Le cycle de vie d'une application conteneurisée suit trois étapes :

1.  **Build :** Construction de l'image à partir du `Dockerfile`.
2.  **Ship (Push) :** Envoi de l'image vers un registre (optionnel pour le dev local).
3.  **Run :** Instanciation du conteneur.

---

## 5. Cas Pratique : Conteneurisation d'un Script Python

Imaginons une structure de projet Data Science standard :

```text
/mon-projet-ds
├── main.py            # Votre script d'entraînement ou d'inférence
├── requirements.txt   # Vos dépendances (pandas, numpy, etc.)
└── Dockerfile         # La recette de construction

```

### A. Définition du Dockerfile

Le `Dockerfile` utilise une syntaxe par couches (layers). Chaque instruction crée une nouvelle couche cachée.

```dockerfile
# 1. Base Image : On part d'un environnement Python officiel léger (Debian Slim)
FROM python:3.9-slim

# 2. Workdir : Définition du répertoire de travail dans le conteneur
WORKDIR /app

# 3. Dependencies : Copie des requirements et installation
# Cette étape est séparée pour optimiser le cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Source Code : Copie du reste du code source
COPY . .

# 5. Entrypoint : Commande exécutée au démarrage du conteneur
CMD ["python", "main.py"]

```

### B. Build (Construction de l'image)

Nous allons "tagger" (nommer) l'image `ds-project:v1`. Le `.` final indique le contexte de build (dossier courant).

```bash
docker build -t ds-project:v1 .

```

### C. Run (Exécution du conteneur)

```bash
docker run --rm --name mon-run-ds ds-project:v1

```

* `--rm` : Supprime automatiquement le conteneur une fois l'exécution terminée (bonne pratique pour les scripts "one-off").
* `--name` : Nomme le conteneur pour faciliter son identification.

---

## 6. Gestion des Données (Volumes)

Par défaut, les données créées dans un conteneur sont **éphémères**. Si le conteneur est supprimé, les données (ex: un modèle `.pkl` ou un `.csv` de sortie) sont perdues.

Pour la Data Science, nous utilisons le **Volume Binding** pour lier un dossier de la machine hôte à un dossier du conteneur.

### Syntaxe

`-v /chemin/hote:/chemin/conteneur`

### Exemple pratique

Supposons que votre script `main.py` lise des données dans `/app/data` et sauvegarde un modèle dans `/app/output`.

```bash
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  ds-project:v1

```

**Résultat :** Le script s'exécute dans le conteneur, mais les fichiers générés sont physiquement écrits sur votre disque dur local dans le dossier `./output`.

---

## Commandes Essentielles (Cheatsheet)

| Commande | Description Technique |
| --- | --- |
| `docker build -t <tag> .` | Compile le Dockerfile en une image binaire. |
| `docker run -d -p 80:80 <img >` | Lance un conteneur en mode détaché (background) avec *port mapping*. |
| `docker ps -a` | Liste tous les processus conteneurisés (actifs et terminés). |
| `docker exec -it <id> bash` | Ouvre un shell interactif *dans* un conteneur en cours d'exécution (utile pour le debug). |
| `docker system prune` | Nettoie les ressources inutilisées (images pendantes, conteneurs arrêtés) pour libérer de l'espace disque. |