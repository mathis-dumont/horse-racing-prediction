import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from frontend.api.api_client import APIClient, fetch_daily_races, fetch_predictions

class TestAPIClient:
    """
    Tests the API client wrapper and data fetching functions.
    Mocks the network layer (requests).
    """

    @pytest.fixture
    def mock_requests_get(self):
        with patch('requests.Session.get') as mock_get:
            yield mock_get

    def test_client_initialization(self):
        with patch.dict('os.environ', {'API_URL': 'http://test-api'}):
            client = APIClient()
            assert client.base_url == 'http://test-api'

    def test_get_request_success(self, mock_requests_get):
        """Test successful JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_requests_get.return_value = mock_response

        client = APIClient()
        result = client._get("/test")
        
        assert result == {"key": "value"}

    def test_get_request_failure(self, mock_requests_get):
        """Test API failure (404/500) returns None."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_requests_get.return_value = mock_response

        client = APIClient()
        result = client._get("/test")
        
        assert result is None

    @patch('frontend.api.api_client.client._get')
    def test_fetch_daily_races_returns_dataframe(self, mock_get):
        """Test that list of dicts converts to DataFrame."""
        mock_get.return_value = [{"race_id": 1}, {"race_id": 2}]
        
        # Note: We are testing the function, ignoring the st.cache_data decorator 
        # (usually bypassed in unit tests or handled by framework)
        df = fetch_daily_races("01012023")
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "race_id" in df.columns

    @patch('frontend.api.api_client.client._get')
    def test_fetch_predictions_empty_on_failure(self, mock_get):
        """Test that API returning None results in empty DataFrame."""
        mock_get.return_value = None
        
        df = fetch_predictions(123)
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty