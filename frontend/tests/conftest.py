import pytest
import pandas as pd
from unittest.mock import MagicMock

# --- DATA FIXTURES ---
# We return Lists of Dicts (JSON style) because that is what the API Client 
# usually returns. The Streamlit App typically converts this to a DataFrame.

@pytest.fixture
def mock_races_data():
    """Returns a sample List[Dict] mimicking /races/{date} API response."""
    return [
        {
            "meeting_number": 1,
            "racetrack_code": "VINCENNES",
            "race_number": 1,
            "race_id": 101,
            "discipline": "TROTTING",
            "distance_m": 2700,
            "declared_runners_count": 14,
            "name": "Prix d'Amerique"
        },
        {
            "meeting_number": 1,
            "racetrack_code": "VINCENNES",
            "race_number": 2,
            "race_id": 102,
            "discipline": "TROTTING",
            "distance_m": 2100,
            "declared_runners_count": 12,
            "name": "Prix de France"
        }
    ]

@pytest.fixture
def mock_prediction_data():
    """Returns a sample List[Dict] mimicking /predict API response."""
    return [
        {
            "program_number": 1,
            "horse_name": "Fast Horse",
            "predicted_rank": 1,
            "win_probability": 0.35
        },
        {
            "program_number": 2,
            "horse_name": "Slow Horse",
            "predicted_rank": 2,
            "win_probability": 0.15
        }
    ]

@pytest.fixture
def mock_participants_data():
    """Returns a sample List[Dict] mimicking /participants API response."""
    return [
        {
            "program_number": 1,
            "driver_name": "J. Doe",
            "odds": 3.5
        },
        {
            "program_number": 2,
            "driver_name": "A. Smith",
            "odds": 12.0
        }
    ]

@pytest.fixture
def mock_sniper_bets():
    """Returns a sample List[Dict] for sniper bets."""
    return [
        {
            "race_num": 1,
            "program_number": 5,
            "horse_name": "Sniper Pick",
            "odds": 8.5,
            "win_probability": 0.20,
            "edge": 0.15
        }
    ]

# --- SESSION STATE FIXTURE ---

@pytest.fixture
def mock_session_state():
    """
    Mocks st.session_state for UNIT tests only.
    """
    import streamlit as st
    from unittest.mock import patch
    
    # Create a real dict to act as state
    mock_state = {}
    
    # Patch the session_state object on the streamlit module
    with patch.object(st, 'session_state', mock_state):
        yield mock_state