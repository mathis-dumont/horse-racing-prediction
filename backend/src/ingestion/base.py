import abc
import json
import logging
import os
import requests
from enum import Enum
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.core.database import DatabaseManager

class IngestStatus(Enum):
    """Enumeration for the result status of an ingestion task."""
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    SKIPPED_NO_CONTENT = "SKIPPED_NO_CONTENT"
    FAILED = "FAILED"

class BaseIngestor(abc.ABC):
    """
    Abstract base class for all ingestion services.
    Handles database connections, logging configuration, HTTP sessions with retries,
    and common utility methods.
    """

    def __init__(self, date_code: str):
        """
        Initialize the ingestor.

        Args:
            date_code (str): The date string (format specific to the provider, usually DDMMYYYY) to ingest.
        """
        self.date_code = date_code
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_logging()

    def _setup_logging(self):
        """Configures logging format and levels."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        # Suppress noisy logs from urllib3
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def _get_http_session(self) -> requests.Session:
        """
        Creates a requests Session with a built-in retry strategy.
        
        Returns:
            requests.Session: Configured session object.
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _save_failed_json(self, data, subdirectory: str, meeting_number: str, race_number: str):
        """
        Saves raw data to a JSON file when ingestion fails, allowing for manual inspection/retry.
        """
        try:
            dir_path = os.path.join("failures", subdirectory)
            os.makedirs(dir_path, exist_ok=True)
            filename = f"{dir_path}/{self.date_code}_R{meeting_number}_C{race_number}.json"
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.warning(f"Fallback: JSON saved to {filename}")
        except Exception as e:
            self.logger.error(f"Critical: Failed to save fallback JSON: {e}")

    def _safe_truncate(self, field_name: str, value: str, max_length: int):
        """
        Truncates a string value to the specified length to prevent DB overflow, logging a warning if it occurs.
        """
        if value and isinstance(value, str) and len(value) > max_length:
            truncated = value[:max_length]
            self.logger.warning(f"OVERFLOW [{field_name}]: {len(value)} chars -> Truncated")
            return truncated
        return value

    def _to_euros(self, cents):
        """
        Converts a value in cents to euros. Returns None if input is invalid.
        """
        if cents is None:
            return None
        try:
            return float(cents) / 100.0
        except (ValueError, TypeError):
            return None

    @abc.abstractmethod
    def ingest(self):
        """Abstract method to execute the ingestion process."""
        pass