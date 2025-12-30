### Planning et état d'avancement du projet

#### Objectif du projet

Le projet vise à construire un système de prédiction des résultats de courses hippiques. Le processus inclut la collecte automatisée des données depuis une interface de programmation, leur stockage dans une base de données normalisée, l'entraînement de modèles d'apprentissage automatique et la restitution des résultats via un site web dédié.

---

#### Phase 1 : architecture et configuration
*   **État** : terminé.
*   **Tâches réalisées** :
    *   Définition de l'architecture globale (ingestion, base de données, apprentissage automatique, interface de programmation, interface utilisateur).
    *   Mise en place de la structure du projet.
    *   Implémentation du schéma SQL complet.
    *   Configuration de l'environnement de développement.

---

#### Phase 2 : création du schéma de la base de données
*   **État** : terminé.
*   **Tâches réalisées** :
    *   Implémentation de l'ensemble des tables SQL.
    *   Vérification de l'intégrité du schéma.

---

#### Phase 3 : analyse des données sources (json)
*   **État** : terminé.
*   **Tâches réalisées** :
    *   Création de scripts d'analyse pour les différentes sources de données.
    *   Vérification de la correspondance entre les champs attendus et les champs fournis par l'interface de programmation pour évaluer la fiabilité des caractéristiques.

---

#### Phase 4 : ingestion des données du programme (json 1)
*   **État** : terminé.
*   **Tâches réalisées** :
    *   Développement du script `ingest_programme_day.py`.
    *   Le script peuple les tables `daily_program`, `race_meeting` et `race`.
    *   La logique de traitement gère les conversions de données et les opérations de mise à jour pour éviter les doublons.

---

#### Phase 5 : ingestion des données détaillées de course (participants, performances et rapports)
*   **État** : terminé.
*   **Description** : cette phase a pour objectif de finaliser l'ensemble des scripts nécessaires pour collecter toutes les informations relatives à une course : participants (JSON 2), historique de performances (JSON 3) et rapports de paris (JSON 4).
*   **Tâches à réaliser** :
    *   Développer un script pour l'ingestion des participants et chevaux (JSON 2), afin de peupler les tables horse et race_participant.
    *   Développer un script pour l'ingestion des performances historiques (JSON 3), afin d'alimenter la table horse_race_history.
    *   Développer un script pour l'ingestion des rapports de paris (JSON 4), afin d'alimenter les tables race_bet et bet_report.

---

#### Phase 6 : rétro-ingestion des données historiques
*   **État** : terminé.
*   **Description** : constitution d'un historique de données sur une période significative (objectif d'au moins cinq ans) pour permettre l'entraînement du modèle.
*   **Tâches à réaliser** :
    *   Créer un script principal capable d'orchestrer les scripts d'ingestion développés dans les phases 4, 5 et 6.
    *   Exécuter ce script de manière itérative sur une plage de dates passées pour peupler la base de données.

---

#### Phase 7 : préparation des données et ingénierie des caractéristiques
*   **État** : terminé.
*   **Description** : transformation des données brutes stockées en un jeu de données structuré et exploitable pour l'apprentissage automatique.
*   **Tâches à réaliser** :
    *   Construire le jeu de données final en joignant les différentes tables de la base.
    *   Séparer le jeu de données en ensembles d'entraînement, de validation et de test, en utilisant une approche temporelle pour éviter les fuites de données.
    *   Créer de nouvelles caractéristiques (ingénierie des caractéristiques) à partir des données brutes, telles que des indicateurs de vitesse, des mesures de la forme récente d'un cheval ou des statistiques sur les entraîneurs.

---

#### Phase 8 : entraînement et évaluation des modèles
*   **État** : terminé.
*   **Description** : développement et sélection du modèle prédictif le plus performant.
*   **Tâches à réaliser** :
    *   Établir une performance de référence avec un modèle simple (par exemple, régression logistique).
    *   Tester plusieurs algorithmes plus complexes (par exemple, XGBoost, LightGBM).
    *   Entraîner les modèles sur l'ensemble d'entraînement.
    *   Évaluer rigoureusement les performances sur l'ensemble de validation.
    *   Sélectionner et sauvegarder la version du meilleur modèle.

---

#### Phase 9 : développement de l'interface de programmation (api) de prédiction
*   **État** : terminé.
*   **Description** : création d'une interface de programmation pour exposer les prédictions du modèle.
*   **Tâches à réaliser** :
    *   Développer une application avec FastAPI.
    *   Définir les points d'accès (`endpoints`) pour obtenir les prédictions, par exemple pour une course spécifique ou pour toutes les courses du jour.
    *   Intégrer le chargement du modèle versionné pour générer et retourner les prédictions.

---

#### Phase 10 : automatisation et planification
*   **État** : terminé.
*   **Description** : mise en place de l'exécution récurrente et autonome du pipeline de données et de prédiction.
*   **Tâches à réaliser** :
    *   Configurer une tâche planifiée (cron) ou une action GitHub pour l'ingestion quotidienne des nouvelles données.
    *   Automatiser l'exécution du script de prédiction après chaque ingestion.
    *   Configurer un système de suivi des erreurs.

---

#### Phase 11 : développement de l'interface utilisateur web
*   **État** : terminé.
*   **Description** : conception et réalisation d'un site web pour présenter le projet, visualiser les prédictions et afficher les performances du modèle. Cette étape est une composante clé de l'évaluation du projet.
*   **Tâches à réaliser** :
    *   Définir la structure et le contenu du site.
    *   Développer l'interface à l'aide d'un framework approprié (par exemple, Streamlit, React).
    *   Connecter l'interface à l'API de prédiction pour afficher les données en temps réel.
    *   Présenter les résultats passés et les indicateurs de performance du modèle.