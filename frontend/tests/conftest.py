import pytest
import pandas as pd
from datetime import datetime
import streamlit as st

@pytest.fixture
def mock_races_data():
    """Returns a sample DataFrame mimicking /races/{date} response."""
    return pd.DataFrame([
        {
            "meeting_number": 1,
            "racetrack_code": "VINCENNES",
            "race_number": 1,
            "race_id": 101,
            "discipline": "TROTTING",
            "distance_m": 2700,
            "declared_runners_count": 14
        },
        {
            "meeting_number": 1,
            "racetrack_code": "VINCENNES",
            "race_number": 2,
            "race_id": 102,
            "discipline": "TROTTING",
            "distance_m": 2100,
            "declared_runners_count": 12
        }
    ])

@pytest.fixture
def mock_prediction_data():
    """Returns a sample DataFrame mimicking /predict response."""
    return pd.DataFrame([
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
    ])

@pytest.fixture
def mock_participants_data():
    """Returns a sample DataFrame mimicking /participants response."""
    return pd.DataFrame([
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
    ])

@pytest.fixture
def mock_sniper_bets():
    """Returns a sample list of dicts for sniper bets."""
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

@pytest.fixture(autouse=True)
def mock_session_state():
    """
    Automatically mocks st.session_state for every test to prevent 
    KeyErrors or context errors when logic accesses it.
    """
    # Create a dictionary to act as session state
    session_state = {}
    
    # Patch the actual st.session_state object
    import streamlit as st
    with pytest.helpers.mock.patch.object(st, 'session_state', session_state):
        yield session_state

# Helper to register the patch helper if using pytest-mock, 
# otherwise we use standard unittest.mock in the tests.
pytest_plugins = ["pytest_mock"]