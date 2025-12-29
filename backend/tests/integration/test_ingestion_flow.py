# tests/integration/test_ingestion_flow.py
import pytest
from unittest.mock import MagicMock, patch
from src.ingestion.program import ProgramIngestor
from src.ingestion.base import IngestStatus

@pytest.fixture
def mock_response():
    """Mocks a requests.Response object."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}
    return resp

def test_program_ingest_flow(mock_db_manager, mock_response):
    """
    Integration test for ProgramIngestor.
    Mocks network and DB to verify the flow of data.
    """
    # 1. Setup Data
    mock_response.json.return_value = {
        "programme": {
            "date": 1704067200000, # Timestamp
            "reunions": [
                {
                    "numOfficiel": 1,
                    "nature": "TROT",
                    "hippodrome": {"code": "VINC"},
                    "courses": [
                        {
                            "numOrdre": 1,
                            "discipline": "ATTELE",
                            "distance": 2700
                        }
                    ]
                }
            ]
        }
    }
    
    # 2. Setup mocks
    with patch("src.ingestion.base.requests.Session.get", return_value=mock_response):
        ingestor = ProgramIngestor("01012025")
        
        # Configure DB mock to return IDs
        mock_cursor = mock_db_manager.get_connection.return_value.cursor.return_value.__enter__.return_value
        mock_cursor.fetchone.side_effect = [(1,), (10,), (100,)] # Program ID, Meeting ID, Race ID (unused)
        
        # 3. Execute
        ingestor.ingest()
        
        # 4. Assertions
        # Check that we inserted the Program
        assert "INSERT INTO daily_program" in mock_cursor.execute.call_args_list[0][0][0]
        
        # Check that we inserted the Meeting
        assert "INSERT INTO race_meeting" in mock_cursor.execute.call_args_list[1][0][0]
        
        # Check that we inserted the Race
        # The 3rd execute call (index 2) should be the race
        call_args = mock_cursor.execute.call_args_list[2]
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert "INSERT INTO race" in query
        assert params[1] == 1 # race_number
        assert params[2] == "ATTELE" # discipline

def test_ingestor_api_failure(mock_db_manager):
    """Test behavior when External API fails."""
    mock_fail_resp = MagicMock()
    mock_fail_resp.status_code = 500
    mock_fail_resp.raise_for_status.side_effect = Exception("API Error")
    
    with patch("src.ingestion.base.requests.Session.get", return_value=mock_fail_resp):
        ingestor = ProgramIngestor("01012025")
        
        # Should catch exception and log error, not crash
        ingestor.ingest()
        
        # Verify no DB writes happened
        mock_cursor = mock_db_manager.get_connection.return_value.cursor.return_value.__enter__.return_value
        mock_cursor.execute.assert_not_called()