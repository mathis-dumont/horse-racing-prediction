import pytest
from unittest.mock import MagicMock, patch, ANY
from src.ingestion.program import ProgramIngestor

# --- FIXTURES ---

@pytest.fixture
def mock_db_manager():
    """
    Patches the DatabaseManager so the Ingestor doesn't connect to the real DB.
    """
    
    with patch("src.ingestion.base.DatabaseManager") as MockDB:
        mock_instance = MockDB.return_value
        # Setup the connection context manager
        mock_conn = mock_instance.get_connection.return_value
        mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
        
        yield mock_instance

@pytest.fixture
def mock_response():
    """Mocks a requests.Response object."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}
    return resp

# --- TESTS ---

def test_program_ingest_flow(mock_db_manager, mock_response):
    """
    Integration test for ProgramIngestor.
    Mocks network and DB to verify the flow of data.
    """
    # 1. Setup Mock API Data
    mock_response.json.return_value = {
        "programme": {
            "date": 1704067200000, 
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
    
    # 2. Patch Requests (Network Layer)
    # We patch Session.get specifically because that's likely what BaseIngestor uses
    with patch("requests.Session.get", return_value=mock_response):
        ingestor = ProgramIngestor("01012025")
        
        # 3. Configure DB Mock Returns
        # We expect 3 fetches (Program ID, Meeting ID, Race ID)
        mock_cursor = mock_db_manager.get_connection.return_value.cursor.return_value.__enter__.return_value
        mock_cursor.fetchone.side_effect = [(1,), (10,), (100,)] 
        
        # 4. Execute
        ingestor.ingest()
        
        # 5. Robust Assertions (Order Independent)
        # We loop through all execute calls to check if our queries are in there somewhere
        all_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
        
        # Check Program Insert
        assert any("INSERT INTO daily_program" in q for q in all_queries), "Daily Program INSERT missing"
        
        # Check Meeting Insert
        assert any("INSERT INTO race_meeting" in q for q in all_queries), "Meeting INSERT missing"
        
        # Check Race Insert & Params
        race_insert_calls = [call for call in mock_cursor.execute.call_args_list 
            if "INSERT INTO race (" in call[0][0]]
        assert len(race_insert_calls) == 1
        
        # Check params of the race insert
        race_params = race_insert_calls[0][0][1] # query is index 0, params is index 1
        assert race_params[1] == 1        # race_number
        assert race_params[2] == "ATTELE" # discipline

def test_ingestor_api_failure(mock_db_manager):
    """Test behavior when External API fails."""
    mock_fail_resp = MagicMock()
    mock_fail_resp.status_code = 500
    mock_fail_resp.raise_for_status.side_effect = Exception("API Error")
    
    # Patch where 'requests' is used in our code
    with patch("requests.Session.get", return_value=mock_fail_resp):
        ingestor = ProgramIngestor("01012025")
        
        # Should catch exception and log error, not crash
        ingestor.ingest()
        
        # Verify no DB writes happened
        mock_cursor = mock_db_manager.get_connection.return_value.cursor.return_value.__enter__.return_value
        mock_cursor.execute.assert_not_called()