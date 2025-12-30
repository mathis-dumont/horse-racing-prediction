import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch  # <--- Import patch
from src.api.main import app, get_repository, ml_models

# --- MOCKS ---

class MockRaceRepository:
    def get_races_by_date(self, date_code: str):
        return [
            {
                "race_id": 100,
                "meeting_number": 1,
                "race_number": 1,
                "discipline": "ATTELE",
                "distance_m": 2700,
                "racetrack_code": "VINC",
                "name": "Prix d'Integration",
                "declared_runners_count": 12
            }
        ]

    def get_race_data_for_ml(self, race_id: int):
        if race_id == 999:
            return []
        return [
            {"program_number": 1, "horse_name": "A", "reference_odds": 2.0},
            {"program_number": 2, "horse_name": "B", "reference_odds": 5.0}
        ]

class MockPredictor:
    # Accept *args so it can catch the arguments meant for the real class
    def __init__(self, *args, **kwargs): 
        self.pipeline = True 

    def predict_race(self, participants):
        return [0.6, 0.4][:len(participants)]

# --- FIXTURE (The Fix) ---

@pytest.fixture
def client():
    # 1. Override Database
    app.dependency_overrides[get_repository] = MockRaceRepository
    
    # 2. PATCH the Predictor Class
    # This ensures that when main.py calls RacePredictor(), it gets our Mock instead.
    with patch("src.api.main.RacePredictor", side_effect=MockPredictor):
        with TestClient(app) as c:
            yield c
    
    # Cleanup
    app.dependency_overrides.clear()
    ml_models.clear()

# --- TESTS ---

def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["ml_engine"] == "loaded"

def test_get_races_success(client):
    response = client.get("/races/01012025")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["race_id"] == 100

def test_predict_race_endpoint(client):
    response = client.get("/races/100/predict")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Verify Mock Data: [0.6, 0.4]
    first = data[0]
    assert first["horse_name"] == "A"
    assert first["predicted_rank"] == 1
    assert first["win_probability"] == 0.6

def test_predict_race_not_found(client):
    response = client.get("/races/999/predict")
    assert response.status_code == 404