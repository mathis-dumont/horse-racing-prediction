import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pandas as pd
import datetime as dt

# Import the FastAPI app
from src.api.main import app
from src.core.database import DatabaseManager

@pytest.fixture(scope="session")
def mock_db_manager():
    """
    Global mock for the DatabaseManager to prevent actual DB connection attempts.
    Returns a mock that simulates connection and cursor context managers.
    """
    with patch("src.core.database.DatabaseManager") as MockManager:
        instance = MockManager.return_value
        
        # Setup Connection Mock
        mock_conn = MagicMock()
        instance.get_connection.return_value = mock_conn
        
        # Setup Cursor Mock
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        yield instance

@pytest.fixture
def mock_cursor(mock_db_manager):
    """Returns the mocked cursor for assertion verification."""
    return mock_db_manager.get_connection.return_value.cursor.return_value.__enter__.return_value

@pytest.fixture
def client():
    """FastAPI Test Client."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_ml_pipeline():
    """Mocks the loaded ML pipeline to avoid needing physical .pkl files."""
    with patch("src.api.main.ml_models") as mock_models:
        mock_predictor = MagicMock()
        # Default behavior: predict 50% probability
        mock_predictor.predict_race.return_value = [0.5, 0.5]
        mock_models.get.return_value = mock_predictor
        yield mock_predictor