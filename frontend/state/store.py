import streamlit as st
from datetime import datetime

# State Keys
KEY_DATE = "date_code"
KEY_MEETING_ID = "selected_meeting_id"
KEY_RACE_ID = "selected_race_id"
KEY_RACES_DATA = "daily_races_df"

def init_session():
    """Initialize session state variables if they don't exist."""
    if KEY_DATE not in st.session_state:
        st.session_state[KEY_DATE] = datetime.today()
    
    if KEY_MEETING_ID not in st.session_state:
        st.session_state[KEY_MEETING_ID] = None
        
    if KEY_RACE_ID not in st.session_state:
        st.session_state[KEY_RACE_ID] = None

    if KEY_RACES_DATA not in st.session_state:
        st.session_state[KEY_RACES_DATA] = None

def get_date_code() -> str:
    """Returns date formatted as DDMMYYYY."""
    date_obj = st.session_state[KEY_DATE]
    return date_obj.strftime("%d%m%Y")

def get_date_obj():
    return st.session_state[KEY_DATE]

def set_date(new_date):
    """Updates date and resets downstream selections."""
    if st.session_state[KEY_DATE] != new_date:
        st.session_state[KEY_DATE] = new_date
        st.session_state[KEY_MEETING_ID] = None
        st.session_state[KEY_RACE_ID] = None

def get_selected_meeting():
    return st.session_state[KEY_MEETING_ID]

def set_selected_meeting(meeting_id):
    """Updates meeting and resets selected race."""
    if st.session_state[KEY_MEETING_ID] != meeting_id:
        st.session_state[KEY_MEETING_ID] = meeting_id
        st.session_state[KEY_RACE_ID] = None

def get_selected_race():
    return st.session_state[KEY_RACE_ID]

def set_selected_race(race_id):
    st.session_state[KEY_RACE_ID] = race_id

def set_races_data(df):
    st.session_state[KEY_RACES_DATA] = df

def get_races_data():
    return st.session_state[KEY_RACES_DATA]