# Projet Prédiction Courses Hippiques

## Description
Ce projet est une application complète (Fullstack) permettant de prédire l'arrivée des courses hippiques, ainsi que de suggérer des paris intéressant. Il utilise une architecture micro-services dockerisée.

##  Architecture Technique
* **Frontend :** [Streamlit] (Interface utilisateur)
* **Backend :** [FastAPI] (API de prédiction)
* **Base de données :** PostgreSQL (Hébergée sur Supabase)
* **Orchestration :** Docker Compose

## Guide de démarrage pour correction

**Prérequis :** Avoir Docker Desktop installé et lancé.

1. **Décompresser le projet** (ou cloner le dépôt).
2. **Vérification du fichier .env :**
   Assurez-vous que le fichier `.env` est bien présent à la racine du projet (contenant la clé `DB_URL`).
3. **Lancer l'application :**
   Ouvrez un terminal dans le dossier et exécutez :
   ```bash
   docker-compose up --build

4. **Lancer les tests depuis Docker:**
   ```bash
   docker compose exec backend pytest -v
   docker compose exec frontend pytest -v

L'architecture de test est conçue pour être isolée. Le Backend utilise unittest.mock pour simuler la base de données (Supabase), et le Frontend utilise Streamlit AppTest en simulant les réponses de l'API. Cela permet de valider le code sans dépendre de la connexion internet ou de l'état du serveur.