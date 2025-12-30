import pytest
from streamlit.testing.v1 import AppTest
from unittest.mock import patch

class TestAppE2E:
    """
    Uses Streamlit's AppTest to simulate a full application run.
    Note: We patch the API client globally for the script execution to avoid real network calls.
    """

    def test_app_startup_smoke_test(self, mock_races_data):
        """
        Ensures the app loads without error and displays the title.
        """
        # We need to mock the API calls that happen in app.py -> sidebar -> api_client
        with patch("frontend.api.api_client.fetch_daily_races") as mock_fetch:
            mock_fetch.return_value = mock_races_data
            
            # Load the app
            at = AppTest.from_file("app.py")
            at.run()
            
            # Check for no exceptions
            assert not at.exception
            
            # Check title (set via st.title in sidebar)
            assert "Turf Analytics" in at.sidebar.title[0].value

    def test_navigation_flow(self, mock_races_data):
        """
        Test selecting a meeting from the sidebar.
        """
        with patch("frontend.api.api_client.fetch_daily_races") as mock_fetch:
            mock_fetch.return_value = mock_races_data
            
            at = AppTest.from_file("frontend/app.py")
            at.run()
            
            # Simulate changing the meeting radio button
            # Note: Radio buttons might take time to render or be indexed differently depending on layout
            # Here we assume the radio is present if data was fetched.
            
            if len(at.sidebar.radio) > 0:
                # Select the first option
                at.sidebar.radio[0].set_value(1) # Assuming value corresponds to meeting_number
                at.run()
                
                assert not at.exception
                # Check if session state was updated (indirectly via UI reaction)
                # In a real AppTest, we inspect visible elements:
                # Expecting "Meeting 1" header in main area
                main_markdown = [e.value for e in at.markdown]
                assert any("Meeting 1" in m for m in main_markdown)