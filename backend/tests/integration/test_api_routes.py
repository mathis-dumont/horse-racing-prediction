# tests/integration/test_api_routes.py
import pytest
from unittest.mock import patch

def test_health_check(client, mock_ml_pipeline):
    """Test the system health endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "ml_engine": "loaded"}

def test_get_races_success(client, mock_db_manager):
    """Test fetching the race list."""
    # Mock Repository via Dependency Override or mocking DB call inside it
    # Since we mocked DB Manager globally, we can mock the fetchall return
    mock_cursor = mock_db_manager.get_connection.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [
        {
            "race_id": 100,
            "meeting_number": 1,
            "race_number": 1,
            "discipline": "ATTELE",
            "distance_m": 2700,
            "racetrack_code": "VINC"
        }
    ]

    response = client.get("/races/01012025")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["race_id"] == 100
    assert data[0]["discipline"] == "ATTELE"

def test_predict_race_endpoint(client, mock_ml_pipeline, mock_db_manager):
    """Test the single race prediction endpoint."""
    mock_cursor = mock_db_manager.get_connection.return_value.cursor.return_value.__enter__.return_value
    
    # Mock return for get_race_data_for_ml
    mock_cursor.fetchall.return_value = [
        {"program_number": 1, "horse_name": "A", "some_feature": 1},
        {"program_number": 2, "horse_name": "B", "some_feature": 2}
    ]
    
    # Mock ML output
    mock_ml_pipeline.predict_race.return_value = [0.6, 0.4]

    response = client.get("/races/100/predict")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Check ranking logic (Highest prob should be rank 1)
    first = data[0]
    assert first["horse_name"] == "A"
    assert first["predicted_rank"] == 1
    assert first["win_probability"] == 0.6

def test_predict_race_not_found(client, mock_db_manager):
    """Test 404 behavior when race has no data."""
    mock_cursor = mock_db_manager.get_connection.return_value.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [] # No participants
    
    response = client.get("/races/999/predict")
    assert response.status_code == 404