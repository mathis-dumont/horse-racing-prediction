import pytest
import logging
from src.ingestion.base import BaseIngestor

class ConcreteIngestor(BaseIngestor):
    """Minimal concrete implementation for testing abstract base class logic."""
    def ingest(self):
        pass

@pytest.fixture
def ingestor():
    return ConcreteIngestor(date_code="01012025")

# --- Parameterized Test ---
@pytest.mark.parametrize("input_val, expected", [
    (1250, 12.5),       # Standard integer
    (0, 0.0),           # Zero edge case
    ("500", 5.0),       # String number
    (None, None),       # None handling
    ("invalid", None),  # Garbage input handling
])
def test_to_euros_conversion(ingestor, input_val, expected):
    """Verify distinct cents to euros conversion scenarios."""
    assert ingestor._to_euros(input_val) == expected

def test_safe_truncate(ingestor, caplog):
    """Verify string truncation and logging of overflows."""
    with caplog.at_level(logging.WARNING):
        # Case 1: No truncation needed
        assert ingestor._safe_truncate("field", "short", 10) == "short"
        assert len(caplog.records) == 0

        # Case 2: Truncation occurs
        long_string = "this is a very long string"
        truncated = ingestor._safe_truncate("test_field", long_string, 5)
        
        assert truncated == "this "
        assert len(caplog.records) == 1
        assert "OVERFLOW [test_field]" in caplog.text

def test_http_session_configuration(ingestor):
    """Ensure the HTTP session is configured with retries."""
    session = ingestor._get_http_session()
    
    # Check HTTPS adapter specifically
    adapter = session.adapters["https://"]
    
    assert adapter.max_retries.total == 3
    # Check that we retry on specific 'Temp Fail' codes
    assert 429 in adapter.max_retries.status_forcelist  # Rate Limit
    assert 503 in adapter.max_retries.status_forcelist  # Service Unavailable