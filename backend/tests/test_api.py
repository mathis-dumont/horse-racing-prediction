import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Import the 'app' and the global 'ml_models' dictionary from our main file
from src.api.main import app, ml_models

# Initialize the TestClient
client = TestClient(app)

# --- FIXTURES (Setup code) ---

@pytest.fixture(autouse=True)
def mock_ml_model():
    """
    Automatically mocks the ML Model for every test.
    This prevents the tests from trying to load the real .pkl file
    and allows us to define fake predictions.
    """
    # Create a fake predictor object
    mock_predictor = MagicMock()
    
    # Inject it into the global dictionary used by main.py
    ml_models["predictor"] = mock_predictor
    
    yield mock_predictor
    
    # Cleanup after test
    ml_models.clear()

# --- TESTS ---

def test_health_check():
    """
    Basic sanity check to ensure the API is running.
    """
    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "online"


# We patch the class method in the Repository where it is defined
@patch("src.api.repositories.RaceRepository.get_races_by_date")
def test_get_races_success(mock_get_races):
    """
    Test retrieving races for a specific date.
    We mock the repository to return a static list of races.
    """
    # 1. ARRANGE (Setup data)
    # We must provide ALL fields required by the RaceSummary schema
    mock_races = [
        {
            "race_id": 1,           # Matches 'race_id' in schema
            "race_number": 1,       # Required
            "meeting_number": 1,    # Required
            "racetrack_code": "VINCENNES", # Likely required
            "date": "27122025",
            "name": "Prix d'Amérique",
            "discipline": "ATTELÉ",  # Likely required
            "distance_m": 2700,      # Likely required
            "declared_runners": 18
        },
        {
            "race_id": 2,
            "race_number": 2,
            "meeting_number": 1,
            "racetrack_code": "VINCENNES",
            "date": "27122025",
            "name": "Prix de France",
            "discipline": "ATTELÉ",
            "distance_m": 2100,
            "declared_runners": 16
        }
    ]
    mock_get_races.return_value = mock_races

    # 2. ACT (Call API)
    response = client.get("/races/27122025")

    # 3. ASSERT (Verify)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Prix d'Amérique"
    # Verify that the schema mapping worked (some schemas map 'id' to 'race_id')
    assert data[0]["race_id"] == 1


@patch("src.api.repositories.RaceRepository.get_race_data_for_ml")
def test_predict_race_success(mock_get_data, mock_ml_model):
    """
    Test the prediction endpoint (/predict).
    This requires mocking TWO things:
    1. The Database (Repository) -> to get horse data.
    2. The ML Model (Predictor) -> to get probabilities.
    """
    # 1. ARRANGE
    
    # A. Mock Database Response (Raw participants)
    mock_participants = [
        {"pmu_number": 1, "horse_name": "Fast Horse", "jockey": "J. Doe"},
        {"pmu_number": 2, "horse_name": "Slow Horse", "jockey": "A. Smith"}
    ]
    mock_get_data.return_value = mock_participants

    # B. Mock ML Model Response
    # We simulate that the model returns high prob for Horse 1, low for Horse 2
    # Note: 'mock_ml_model' comes from the pytest fixture defined above
    mock_ml_model.pipeline = True # Simulate that pipeline exists
    mock_ml_model.predict_race.return_value = [0.85, 0.15] 

    # 2. ACT
    response = client.get("/races/123/predict")

    # 3. ASSERT
    assert response.status_code == 200
    results = response.json()

    # Check sorting: The horse with 0.85 prob should be Rank 1
    assert len(results) == 2
    assert results[0]["horse_name"] == "Fast Horse"
    assert results[0]["predicted_rank"] == 1
    assert results[0]["win_probability"] == 0.85
    
    # Check that the ML model was actually called
    mock_ml_model.predict_race.assert_called_once()


@patch("src.api.repositories.RaceRepository.get_race_data_for_ml")
def test_predict_race_not_found(mock_get_data, mock_ml_model):
    """
    Edge Case: What happens if the race ID doesn't exist?
    """
    # 1. ARRANGE
    mock_ml_model.pipeline = True
    # The DB returns an empty list (no data found)
    mock_get_data.return_value = []

    # 2. ACT
    response = client.get("/races/99999/predict")

    # 3. ASSERT
    assert response.status_code == 404
    assert "Race not found" in response.json()["detail"]


@patch("src.api.repositories.RaceRepository.get_races_by_date")
@patch("src.api.repositories.RaceRepository.get_race_data_for_ml")
def test_sniper_bets_strategy(mock_get_data, mock_get_races, mock_ml_model):
    """
    Integration Test for 'Sniper' Strategy.
    This endpoint is complex: it fetches races -> fetches participants -> predicts -> filters.
    """
    # 1. ARRANGE
    
    # A. Mock the list of races
    mock_get_races.return_value = [{"race_id": 100, "race_number": 1}]

    # B. Mock participants with Odds (Crucial for Sniper strategy)
    # Horse 1: High Prob (0.8), High Odds (10.0) -> HUGE EDGE -> Should be picked
    # Horse 2: Low Prob (0.2), Low Odds (2.0) -> No edge -> Ignored
    mock_participants = [
        {"pmu_number": 1, "horse_name": "Sniper Pick", "reference_odds": 10.0},
        {"pmu_number": 2, "horse_name": "Loser", "reference_odds": 2.0}
    ]
    mock_get_data.return_value = mock_participants

    # C. Mock Predictions corresponding to participants
    mock_ml_model.predict_race.return_value = [0.8, 0.2]

    # 2. ACT
    response = client.get("/bets/sniper/27122025")

    # 3. ASSERT
    assert response.status_code == 200
    bets = response.json()

    # We expect exactly 1 bet (The Sniper Pick)
    assert len(bets) == 1
    assert bets[0]["horse_name"] == "Sniper Pick"
    assert bets[0]["strategy"] == "Sniper"
    
    # Verify the math (0.8 probability - 1/10 implied prob = 0.7 edge)
    assert bets[0]["edge"] > 0.5