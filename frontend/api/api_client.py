import logging
import requests
import pandas as pd
import streamlit as st
import os
from typing import List, Dict, Any

# Logger Setup
logger = logging.getLogger(__name__)

class APIClient:
    """
    Singleton-style API client to handle all backend communication.
    Uses requests.Session for connection pooling.
    """
    def __init__(self):
        self.base_url = os.getenv("API_URL", "http://127.0.0.1:8000")
        self.session = requests.Session()
        self.timeout = 10

    def _get(self, endpoint: str) -> Any:
        """Internal helper for GET requests with error handling."""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"GET {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request Failed: {e}")
            return None

# Instantiate a global client (stateless regarding user data, stateful regarding TCP)
client = APIClient()

@st.cache_data(ttl=300)
def fetch_daily_races(date_code: str) -> pd.DataFrame:
    data = client._get(f"/races/{date_code}")
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

@st.cache_data(ttl=600)
def fetch_predictions(race_id: int) -> pd.DataFrame:
    data = client._get(f"/races/{race_id}/predict")
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_sniper_bets(date_str: str) -> List[Dict[str, Any]]:
    data = client._get(f"/bets/sniper/{date_str}")
    return data if data else []

@st.cache_data(ttl=300)
def fetch_participants(race_id: int) -> pd.DataFrame:
    data = client._get(f"/races/{race_id}/participants")
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)