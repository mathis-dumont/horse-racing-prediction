import logging
import requests
import pandas as pd
import streamlit as st
from typing import Optional

# Set up a logger for this module
logger = logging.getLogger(__name__)

BASE_API_URL = "http://127.0.0.1:8000"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_daily_races(date_code: str) -> pd.DataFrame:
    """
    Fetches the list of races for a specific date from the API.

    Args:
        date_code (str): The date formatted as a string (e.g., "DDMMYYYY").

    Returns:
        pd.DataFrame: A DataFrame containing race information, or an empty DataFrame on failure.
    """
    logger.info(f"Fetching races for date code: {date_code}")
    try:
        response = requests.get(f"{BASE_API_URL}/races/{date_code}")
        response.raise_for_status()
        data = response.json()
        
        if not data:
            logger.warning("No race data returned from API.")
            return pd.DataFrame()
            
        return pd.DataFrame(data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error in fetch_daily_races: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)  # Predictions don't change often once calculated
def fetch_predictions(race_id: int) -> pd.DataFrame:
    """
    Fetches prediction data for a specific race.

    Args:
        race_id (int): The unique identifier of the race.

    Returns:
        pd.DataFrame: A DataFrame containing prediction data, or an empty DataFrame on failure.
    """
    logger.info(f"Fetching predictions for race ID: {race_id}")
    try:
        response = requests.get(f"{BASE_API_URL}/races/{race_id}/predict")
        response.raise_for_status()
        data = response.json()
        
        if not data:
            logger.warning(f"No prediction data found for race {race_id}.")
            return pd.DataFrame()
            
        return pd.DataFrame(data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error in fetch_predictions: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_participants(race_id: int) -> pd.DataFrame:
    """
    Fetches raw participant details (supplementary info like drivers, odds) for a race.

    Args:
        race_id (int): The unique identifier of the race.

    Returns:
        pd.DataFrame: A DataFrame containing participant details.
    """
    logger.debug(f"Fetching participants for race ID: {race_id}")
    try:
        response = requests.get(f"{BASE_API_URL}/races/{race_id}/participants")
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error in fetch_participants: {e}")
        return pd.DataFrame()