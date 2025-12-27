# Documentation des Tests & Qualité Logicielle

Ce document détaille la stratégie de tests mise en place pour le projet de prédiction de courses hippiques. Le projet suit une architecture de test rigoureuse garantissant que chaque micro-service (Backend et Frontend) fonctionne de manière isolée et robuste.

## Philosophie : Isolation et Mocking

Pour garantir la fiabilité des tests (et éviter qu'ils n'échouent si la connexion internet est coupée ou si la base de données est vide), nous appliquons le principe d'**Isolation**.

* **Backend :** Les tests ne se connectent **pas** à la vraie base de données (Supabase). Les appels sont interceptés (Mockés) pour renvoyer des données contrôlées.
* **Frontend :** Les tests ne font **pas** de requêtes HTTP vers l'API. Les fonctions du client API sont simulées pour valider l'interface graphique indépendamment du serveur.

---

## Guide d'Exécution Rapide

### Prérequis

L'application doit être lancée via Docker.

```bash
docker compose up -d --build

```

### 1. Exécuter les tests Backend (API & ML)

Ces tests valident la logique métier, les routes API et l'intégration du modèle de Machine Learning.

```bash
docker compose exec backend pytest -v

```

**Couverture des tests :**

* **Health Check :** Vérification de la disponibilité du service.
* **Logique ML :** Simulation des prédictions (XGBoost) pour garantir des sorties déterministes.
* **Repository Pattern :** Mock de la couche d'accès aux données (PostgreSQL/Supabase).
* **Stratégie "Sniper" :** Validation de l'algorithme de détection de "Value Bet" (calcul de l'Edge).

### 2. Exécuter les tests Frontend (Interface UI)

Ces tests utilisent le framework natif `AppTest` de Streamlit pour simuler une navigation utilisateur sans navigateur ("headless").

```bash
docker compose exec frontend pytest -v

```

**Couverture des tests :**

* **Smoke Test :** L'application démarre sans erreur.
* **Scénario "Sans Données" :** Vérification de l'affichage (Message d'avertissement) quand l'API est vide.
* **Scénario "Nominal" :** Vérification que les widgets (Sélecteur de réunion, Tableaux) apparaissent quand l'API renvoie des courses.
* **Injection de dépendances :** Patch du module `api_client` pour simuler les réponses JSON.

---

##  Détails Techniques

Voici comment l'isolation est implémentée techniquement dans le code.

### A. Mocking de la Base de Données (Backend)

Nous utilisons `unittest.mock.patch` pour remplacer la méthode du Repository.

```python
# Extrait de backend/tests/test_api.py
@patch("src.api.repositories.RaceRepository.get_races_by_date")
def test_get_races_success(mock_get_races):
    # 1. ARRANGE : On définit la réponse fictive de la BDD
    mock_get_races.return_value = [
        {"race_id": 1, "race_name": "Prix d'Amérique", "date": "27122025"}
    ]

    # 2. ACT : Appel API réel
    response = client.get("/races/27122025")

    # 3. ASSERT : Le code a bien traité la fausse donnée
    assert response.status_code == 200
    assert response.json()[0]["race_name"] == "Prix d'Amérique"

```

### B. Mocking de l'API (Frontend)

Nous injectons le chemin du dossier parent dans le `sys.path` pour permettre l'importation des modules, puis nous patchons le client API.

```python
# Extrait de frontend/tests/test_app.py
@patch("api_client.fetch_daily_races")
def test_races_loaded_ui(mock_fetch_races):
    # Simulation d'une réponse API contenant des courses
    mock_fetch_races.return_value = pd.DataFrame({...})
    
    # Lancement de l'application en mode test
    at = AppTest.from_file("../main.py")
    at.run()
    
    # Vérification que l'UI a réagi (ex: affichage du sélecteur)
    assert len(at.sidebar.radio) > 0

```

---

## Résultats Attendus

Si l'environnement est correctement configuré, l'exécution des commandes ci-dessus doit produire un résultat "Vert" (PASSED).

**Exemple de sortie Backend :**

```text
tests/test_api.py::test_health_check PASSED                            [ 20%]
tests/test_api.py::test_get_races_success PASSED                       [ 40%]
tests/test_api.py::test_predict_race_success PASSED                    [ 60%]
tests/test_api.py::test_predict_race_not_found PASSED                  [ 80%]
tests/test_api.py::test_sniper_bets_strategy PASSED                    [100%]

============================== 5 passed in 0.45s ==============================

```

**Exemple de sortie Frontend :**

```text
tests/test_app.py::test_app_initial_load PASSED                        [ 50%]
tests/test_app.py::test_races_loaded_ui PASSED                         [100%]

============================== 2 passed in 1.12s ==============================

```