import logging
import requests
import pandas as pd
import streamlit as st
import os
from typing import List, Dict, Any

# Set up a logger
logger = logging.getLogger(__name__)

# CONFIGURATION
# Try to get the URL from the system (good for Docker/Cloud), fallback to localhost
BASE_API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_daily_races(date_code: str) -> pd.DataFrame:
    """
    Fetches the list of races for a specific date.
    """
    logger.info(f"Fetching races for date code: {date_code}")
    try:
        response = requests.get(f"{BASE_API_URL}/races/{date_code}", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            logger.warning("No race data returned from API.")
            return pd.DataFrame()
            
        return pd.DataFrame(data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error in fetch_daily_races: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)  # Predictions are static once generated
def fetch_predictions(race_id: int) -> pd.DataFrame:
    """
    Fetches prediction data for a specific race.
    """
    logger.info(f"Fetching predictions for race ID: {race_id}")
    try:
        response = requests.get(f"{BASE_API_URL}/races/{race_id}/predict", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            logger.warning(f"No prediction data found for race {race_id}.")
            return pd.DataFrame()
            
        return pd.DataFrame(data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error in fetch_predictions: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)  # Cache sniper bets (odds change, so keep TTL reasonable)
def get_sniper_bets(date_str: str) -> List[Dict[str, Any]]:
    """
    Fetches AI Sniper recommendations for the day.
    """
    logger.info(f"Fetching Sniper bets for: {date_str}")
    try:
        # FIX: Removed 'self', using global BASE_API_URL
        response = requests.get(f"{BASE_API_URL}/bets/sniper/{date_str}", timeout=10)
        
        if response.status_code == 200:
            return response.json() # Returns a list of dicts
        
        logger.warning(f"Sniper API returned status: {response.status_code}")
        return []
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error in get_sniper_bets: {e}")
        return []

@st.cache_data(ttl=300)
def fetch_participants(race_id: int) -> pd.DataFrame:
    """
    Fetches raw participant details (drivers, odds, etc.).
    """
    logger.debug(f"Fetching participants for race ID: {race_id}")
    try:
        response = requests.get(f"{BASE_API_URL}/races/{race_id}/participants", timeout=5)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error in fetch_participants: {e}")
        return pd.DataFrame()