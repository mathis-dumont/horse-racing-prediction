import sys
import os
import pytest
import pandas as pd
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Path to the main.py (relative to the tests folder)
APP_PATH = "../main.py"

# --- MOCK DATA ---
mock_races_data = pd.DataFrame({
    'date': ['27122025'],
    'meeting_number': [1],
    'race_number': [1],
    'race_id': [12345],
    'racetrack_code': ['VINCENNES'],
    'discipline': ['Trot Attelé'],
    'distance_m': [2700],
    'declared_runners': [16]
})

# --- TESTS ---

@patch("api_client.fetch_daily_races")
@patch("api_client.get_sniper_bets")
def test_app_initial_load(mock_sniper, mock_fetch_races):
    """
    Scenario 1: API returns NO data.
    The app should load without crashing and show the title.
    """
    # 1. ARRANGE: Simulate empty API response
    mock_fetch_races.return_value = pd.DataFrame()
    mock_sniper.return_value = []

    # 2. ACT: Run the app
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 3. ASSERT
    assert not at.exception, "The app crashed on startup!"
    
    # Verify the sidebar title exists
    # Streamlit testing returns lists for elements; we check the first one
    assert len(at.sidebar.title) > 0
    assert "Turf Analytics" in at.sidebar.title[0].value


@patch("api_client.fetch_daily_races")
@patch("api_client.get_sniper_bets")
def test_races_loaded_ui(mock_sniper, mock_fetch_races):
    """
    Scenario 2: API returns valid race data.
    The app should display the 'Choose a meeting' selector.
    """
    # 1. ARRANGE: Simulate valid data
    mock_fetch_races.return_value = mock_races_data
    mock_sniper.return_value = []

    # 2. ACT
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 3. ASSERT
    assert not at.exception
    
    # Check if the Meeting Selector (Radio Button) appeared
    assert len(at.sidebar.radio) > 0
    assert "Choose a meeting" in at.sidebar.radio[0].label
    
    # Check if the Racetrack name appears in the main area
    found = False
    for md in at.markdown:
        if "VINCENNES" in md.value:
            found = True
            break
    assert found, "The racetrack name (VINCENNES) was not found in the UI."