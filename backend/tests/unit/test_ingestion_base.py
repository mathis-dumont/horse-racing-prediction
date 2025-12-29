# tests/unit/test_ingestion_base.py
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

def test_to_euros_conversion(ingestor):
    """Verify distinct cents to euros conversion scenarios."""
    assert ingestor._to_euros(1250) == 12.5
    assert ingestor._to_euros(0) == 0.0
    assert ingestor._to_euros("500") == 5.0
    assert ingestor._to_euros(None) is None
    assert ingestor._to_euros("invalid") is None

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
    adapter = session.adapters["https://"]
    
    assert adapter.max_retries.total == 3
    assert 429 in adapter.max_retries.status_forcelist
    assert 503 in adapter.max_retries.status_forcelist