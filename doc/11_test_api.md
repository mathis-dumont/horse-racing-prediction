# 🚀 Guide de Test de l'API (FastAPI)

Une fois le projet lancé avec `make up`, l'API est accessible à l'adresse suivante : **`http://localhost:8000`**.

### 🛠 Documentation Interactive (Swagger)

Le moyen le plus simple de tester l'API est d'utiliser l'interface Swagger intégrée :
👉 **URL :** `http://localhost:8000/docs`

---

### 📡 Endpoints Principaux

| Méthode | Endpoint | Description | Paramètre Exemple |
| --- | --- | --- | --- |
| **GET** | `/` | État du système (Santé de la BDD et du moteur ML). | - |
| **GET** | `/races/{date}` | Liste toutes les courses pour une date donnée. | `31122025` |
| **GET** | `/races/{id}/participants` | Liste les chevaux et leurs cotes pour une course. | `45833` |
| **GET** | `/races/{id}/predict` | **(Cœur du projet)** Retourne les probabilités de victoire. | `45833` |
| **GET** | `/bets/sniper/{date}` | Affiche les meilleures opportunités (Value Bets) du jour. | `31122025` |

---

### 🔍 Exemples de commandes de test (cURL)

Pour tester via un terminal, voici les commandes clés :

**1. Vérifier si le modèle XGBoost est bien chargé :**

```bash
curl -X GET "http://localhost:8000/"

```

*Réponse attendue : `{"status":"online","ml_engine":"ready"}*`

**2. Obtenir des prédictions pour une course spécifique :**

```bash
curl -X GET "http://localhost:8000/races/45833/predict"

```

---

### 💡 Notes pour l'évaluation

1. **Code de retour 503 :** Si l'endpoint `/predict` renvoie une erreur 503, cela signifie que le modèle `.pkl` n'a pas été généré. Il faut lancer `make train`.
2. **Code de retour 404 :** Si une course n'est pas trouvée, vérifiez que l'ingestion a bien été faite pour cette date avec `make ingest DATE=...`.
3. **Logique "Sniper" :** L'endpoint `/bets/sniper/` ne retourne des résultats que si la probabilité prédite par notre modèle est significativement supérieure à la probabilité implicite de la cote (Edge > 10%).