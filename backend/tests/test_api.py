import pytest
from fastapi.testclient import TestClient
from src.api.main import app, get_repository, ml_models

# --- 1. MOCK CLASSES ---

class MockRaceRepository:
    """Simulates the database interactions."""
    
    def get_races_by_date(self, date_code: str):
        return [
            {
                "race_id": 1, 
                "race_number": 1, 
                "meeting_number": 1,
                "name": "Prix de Test", 
                "start_time": "2023-10-01T13:50:00"
            }
        ]

    def get_participants_by_race(self, race_id: int):
        return [
            {"pmu_number": 1, "horse_name": "Fast Horse", "jockey": "J. Doe", "trainer": "T. Smith"}
        ]

    def get_daily_data_for_ml(self, date_code: str):
        """Returns data specifically designed to test the Sniper logic."""
        return [
            # Case 1: A Winner (Good Odds, High Edge)
            {
                "race_id": 1, "race_number": 1, "horse_name": "Sniper Choice", 
                "pmu_number": 1, "reference_odds": 10.0
            },
            # Case 2: Odds too low (Favorite)
            {
                "race_id": 1, "race_number": 1, "horse_name": "Low Odds Fav", 
                "pmu_number": 2, "reference_odds": 2.0
            },
            # Case 3: Odds too high (Longshot)
            {
                "race_id": 1, "race_number": 1, "horse_name": "Longshot", 
                "pmu_number": 3, "reference_odds": 50.0
            },
        ]

    def get_race_data_for_ml(self, race_id: int):
        return [
            {"pmu_number": 1, "horse_name": "Horse A", "reference_odds": 5.0},
            {"pmu_number": 2, "horse_name": "Horse B", "reference_odds": 10.0}
        ]

class MockPredictor:
    """Simulates the ML Model."""
    
    def __init__(self):
        self.pipeline = True 

    def predict_race(self, participants):
        count = len(participants)
        if count == 0:
            return []
        # Return probability 0.20 for the first horse (Sniper Choice) to ensure Edge > 0.05
        # 0.20 - (1/10.0) = 0.10 Edge.
        return [0.20, 0.60, 0.05, 0.15][:count]


# --- 2. FIXTURES ---

@pytest.fixture
def client():
    """
    Setup the TestClient with dependency overrides.
    """
    app.dependency_overrides[get_repository] = MockRaceRepository
    
    with TestClient(app) as c:
        ml_models["predictor"] = MockPredictor()
        yield c
    
    app.dependency_overrides.clear()
    ml_models.clear()


# --- 3. TESTS ---

def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["ml_engine"] == "loaded"

def test_get_races(client):
    response = client.get("/races/28122025")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Prix de Test"

def test_sniper_bets_logic(client):
    response = client.get("/bets/sniper/28122025")
    assert response.status_code == 200
    
    bets = response.json()
    assert len(bets) > 0  
    
    first_bet = bets[0]
    assert first_bet["horse_name"] == "Sniper Choice"
    assert first_bet["strategy"] == "Sniper"
    assert first_bet["edge"] == pytest.approx(0.10, abs=0.01)

def test_predict_race(client):
    response = client.get("/races/1/predict")
    assert response.status_code == 200
    
    results = response.json()
    assert len(results) == 2
    assert results[0]["predicted_rank"] == 1

def test_sniper_no_model(client):
    """Test behavior when model fails to load."""
    ml_models.clear() # Simulate empty model dict
    
    response = client.get("/bets/sniper/28122025")
    assert response.status_code == 503
    assert response.json()["detail"] == "ML Model is strictly required for betting calculations."