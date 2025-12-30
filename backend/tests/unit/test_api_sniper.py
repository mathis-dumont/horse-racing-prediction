import pytest
from unittest.mock import MagicMock
from src.api.main import get_sniper_bets, ml_models  # Import the global dict

# --- FIXTURE SETUP ---
@pytest.fixture
def mock_predictor():
    """
    Creates a mock predictor and INJECTS it into the global ml_models dict.
    This ensures get_sniper_bets finds it.
    """
    mock = MagicMock()
    # 1. Inject the mock into the global state
    ml_models["predictor"] = mock
    
    yield mock
    
    # 2. Clean up after test
    ml_models.clear()

# --- TESTS ---

def test_sniper_strategy_logic(mock_predictor):
    """
    Test the betting strategy math:
    Edge = Prob - (1 / Odds)
    Should filter based on Edge > 0.05 and Odds between 5 and 20.
    """
    # 1. Setup Mock Repository
    mock_repo = MagicMock()
    
    # Setup mock data: 3 horses
    mock_repo.get_daily_data_for_ml.return_value = [
        # Horse A: Odds 1.1 (Too Low)
        {"race_id": 1, "race_number": 1, "program_number": 1, "horse_name": "Fav", "reference_odds": 1.1},
        
        # Horse B: Odds 10.0, Prob 0.2 -> Implied 0.1 -> Edge +0.1 (GOOD TARGET)
        {"race_id": 1, "race_number": 1, "program_number": 2, "horse_name": "SniperTarget", "reference_odds": 10.0},
        
        # Horse C: Odds 8.0, Prob 0.05 -> Implied 0.125 -> Edge -0.075 (Negative Edge)
        {"race_id": 1, "race_number": 1, "program_number": 3, "horse_name": "Loser", "reference_odds": 8.0},
    ]

    # 2. Setup Mock Model Predictions
    # Must match the order of the list above: [Fav, SniperTarget, Loser]
    mock_predictor.predict_race.return_value = [0.8, 0.2, 0.05]
    
    # 3. Execute
    # We pass the repo directly. The function finds 'mock_predictor' inside 'ml_models' automatically.
    recommendations = get_sniper_bets(date_code="01012025", repository=mock_repo)
    
    # 4. Assertions
    assert len(recommendations) == 1
    rec = recommendations[0]
    
    assert rec['horse_name'] == "SniperTarget"
    assert rec['odds'] == 10.0
    assert rec['win_probability'] == 0.2
    
    # Verify Math: Edge = 0.2 - (1/10.0) = 0.1
    assert rec['edge'] == pytest.approx(0.1, abs=0.0001)

def test_sniper_no_data(mock_predictor):
    """Handle empty data gracefully."""
    mock_repo = MagicMock()
    mock_repo.get_daily_data_for_ml.return_value = []
    
    res = get_sniper_bets("01012025", repository=mock_repo)
    assert res == []