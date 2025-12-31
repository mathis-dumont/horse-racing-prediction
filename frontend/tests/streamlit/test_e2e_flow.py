import pytest
from streamlit.testing.v1 import AppTest
import pandas as pd
from unittest.mock import patch, MagicMock

class TestAppE2E:
    """
    Uses Streamlit's AppTest to simulate a full application run.
    Note: We patch the API client globally for the script execution to avoid real network calls.
    """

    def test_app_startup_smoke_test(self, mock_races_data):
        """
        Ensures the app loads without error and displays the title.
        """
        # Patching where the function is used
        with patch("ui.sidebar.fetch_daily_races") as mock_fetch:
            mock_fetch.return_value = pd.DataFrame(mock_races_data)
            
            # Load the app
            at = AppTest.from_file("app.py")
            at.run(timeout=20)
            
            # Check for no exceptions
            assert not at.exception
            
            # Check title (set via st.title in sidebar)
            assert "Turf Analytics" in at.sidebar.title[0].value

    def test_navigation_flow(self, mock_races_data):
        """
        Test selecting a meeting from the sidebar.
        """
        with patch("ui.sidebar.fetch_daily_races") as mock_fetch:
            mock_fetch.return_value = pd.DataFrame(mock_races_data)
            
            at = AppTest.from_file("app.py")
            at.run(timeout=20)
            
            # Simulate changing the meeting radio button.
            if len(at.sidebar.radio) > 0:
                at.sidebar.radio[0].set_value(1) 
                at.run()
                
                assert not at.exception
                
                main_markdown = [e.value for e in at.markdown]
                assert any("Meeting 1" in m for m in main_markdown)