# tests/unit/test_api_sniper.py
import pytest
import pandas as pd
from unittest.mock import MagicMock
from src.api.main import get_sniper_bets

# Mock configuration constants from main
MIN_EDGE = 0.05
MIN_ODDS = 5.0
MAX_ODDS = 20.0

def test_sniper_strategy_logic(mock_ml_pipeline):
    """
    Test the betting strategy math:
    Edge = Prob - (1 / Odds)
    Should filter based on Edge > 0.05 and Odds between 5 and 20.
    """
    mock_repo = MagicMock()
    
    # Setup mock data: 3 horses
    # Horse A: Odds 1.1, Prob 0.8 -> Implied 0.9. Edge -0.1 (Bad Value)
    # Horse B: Odds 10.0, Prob 0.2 -> Implied 0.1. Edge 0.1 (Good Value, High Odds)
    # Horse C: Odds 8.0, Prob 0.05 -> Implied 0.125. Edge -0.075 (Bad Value)
    mock_repo.get_daily_data_for_ml.return_value = [
        {"race_id": 1, "race_number": 1, "program_number": 1, "horse_name": "Fav", "reference_odds": 1.1},
        {"race_id": 1, "race_number": 1, "program_number": 2, "horse_name": "SniperTarget", "reference_odds": 10.0},
        {"race_id": 1, "race_number": 1, "program_number": 3, "horse_name": "Loser", "reference_odds": 8.0},
    ]

    # Mock Model predictions corresponding to the list above
    mock_ml_pipeline.predict_race.return_value = [0.8, 0.2, 0.05]
    
    # Execute
    recommendations = get_sniper_bets(date_code="01012025", repository=mock_repo)
    
    # Assertions
    assert len(recommendations) == 1
    rec = recommendations[0]
    
    assert rec['horse_name'] == "SniperTarget"
    assert rec['odds'] == 10.0
    assert rec['win_probability'] == 0.2
    
    # Edge Calculation: 0.2 - (1/10.0) = 0.1
    assert rec['edge'] == 0.1

def test_sniper_no_data(mock_ml_pipeline):
    """Handle empty data gracefully."""
    mock_repo = MagicMock()
    mock_repo.get_daily_data_for_ml.return_value = []
    
    res = get_sniper_bets("01012025", repository=mock_repo)
    assert res == []