import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.api.main import app, get_repository, ml_models

# --- 1. MOCK CLASSES ---

class MockRaceRepository:
    """Simulates the database interactions with strict adherence to schema.py."""
    
    def get_races_by_date(self, date_code: str):
        return [
            {
                "race_id": 1, 
                "race_number": 1, 
                "meeting_number": 1,
                "name": "Prix de Test",
                "discipline": "HARNESS",
                "distance_m": 2700,
                "racetrack_code": "VINCENNES",
                "declared_runners_count": 14
            }
        ]

    def get_participants_by_race(self, race_id: int):
        return [
            {
                "program_number": 1, 
                "horse_name": "Fast Horse", 
                "driver_name": "J. Doe",
                "trainer_name": "T. Smith",
                "odds": 5.4
            }
        ]

    def get_daily_data_for_ml(self, date_code: str):
        return [
            # Case 1: Winner (Good Odds, High Edge)
            {
                "race_id": 1, "race_number": 1, "program_number": 1, 
                "horse_name": "Sniper Choice", "reference_odds": 10.0
            },
            # Case 2: Favorite (Odds too low)
            {
                "race_id": 1, "race_number": 1, "program_number": 2, 
                "horse_name": "Low Odds Fav", "reference_odds": 2.0
            },
            # Case 3: Longshot (Odds too high)
            {
                "race_id": 1, "race_number": 1, "program_number": 3, 
                "horse_name": "Longshot", "reference_odds": 50.0
            },
        ]

    def get_race_data_for_ml(self, race_id: int):
        return [
            {"program_number": 1, "horse_name": "Horse A", "reference_odds": 5.0},
            {"program_number": 2, "horse_name": "Horse B", "reference_odds": 10.0}
        ]

class MockPredictor:
    """Simulates the ML Model."""
    
    # Accept any arguments so it can replace the real RacePredictor(path)
    def __init__(self, *args, **kwargs):
        self.pipeline = True 

    def predict_race(self, participants):
        count = len(participants)
        if count == 0: return []
        
        # 3 participants = Sniper Test
        if count == 3:
            # 1. Sniper Choice: Prob 0.20 -> Edge = 0.20 - (1/10) = 0.10 (KEEP)
            return [0.20, 0.60, 0.05]
            
        # 2 participants = Single Race Prediction
        if count == 2:
            return [0.8, 0.2]
            
        return [0.0] * count

# --- 2. FIXTURES ---

@pytest.fixture
def client():
    # 1. Override the DB Repository
    app.dependency_overrides[get_repository] = MockRaceRepository
    
    # 2. PATCH the RacePredictor class in main.py
    # When main.py calls RacePredictor(...), it will get our MockPredictor(...) instead.
    # This prevents the real model (and its heavy pickle file) from ever loading.
    with patch("src.api.main.RacePredictor", side_effect=MockPredictor):
        with TestClient(app) as c:
            yield c
            
    # Cleanup
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
    data = response.json()
    assert data[0]["name"] == "Prix de Test"

def test_get_participants(client):
    response = client.get("/races/1/participants")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["driver_name"] == "J. Doe"

def test_sniper_bets_logic(client):
    response = client.get("/bets/sniper/28122025")
    assert response.status_code == 200
    bets = response.json()
    
    assert len(bets) == 1
    bet = bets[0]
    
    assert bet["horse_name"] == "Sniper Choice"
    assert bet["strategy"] == "Sniper"
    assert bet["edge"] == pytest.approx(0.10, abs=0.01)

def test_predict_race(client):
    response = client.get("/races/1/predict")
    assert response.status_code == 200
    results = response.json()
    
    assert results[0]["predicted_rank"] == 1
    assert results[0]["win_probability"] == 0.8