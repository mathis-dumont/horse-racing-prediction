import streamlit as st
from datetime import datetime
from api.api_client import fetch_daily_races
import state.store as store

def render_sidebar():
    with st.sidebar:
        st.title("🏇 Turf Analytics")
        st.markdown("---")
        
        st.subheader("📅 Schedule")
        
        # 1. Date Selection
        current_date = store.get_date_obj()
        new_date = st.date_input("Select a date", current_date)
        
        # Update state immediately if changed
        if new_date != current_date:
            store.set_date(new_date)
            st.rerun() # Force reload to fetch new data

        # 2. Fetch Data based on State
        date_code = store.get_date_code()
        
        with st.spinner("Loading schedule..."):
            races_df = fetch_daily_races(date_code)
            store.set_races_data(races_df)

        # 3. Meeting Selection
        if not races_df.empty:
            unique_meetings = sorted(races_df['meeting_number'].unique())
            
            # Helper to create label
            def format_meeting(m_num):
                m_races = races_df[races_df['meeting_number'] == m_num]
                track = m_races.iloc[0]['racetrack_code'] if not m_races.empty else "Unknown"
                return f"R{m_num} - {track}"

            st.subheader("📍 Meeting")
            
            current_meeting = store.get_selected_meeting()
            # Default to first meeting if none selected
            if current_meeting is None and len(unique_meetings) > 0:
                current_meeting = unique_meetings[0]
                store.set_selected_meeting(current_meeting)

            selected_meeting = st.radio(
                "Choose a meeting:",
                unique_meetings,
                format_func=format_meeting,
                index=unique_meetings.index(current_meeting) if current_meeting in unique_meetings else 0
            )
            
            # Write to state
            store.set_selected_meeting(selected_meeting)

            st.markdown("---")
            st.caption("v3.2.0 • Architecture Refactor")
        else:
            st.warning("No races available for this date.")