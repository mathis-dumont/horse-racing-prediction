import streamlit as st
import state.store as store
from ui.analysis import render_analysis_view

def render_race_grid():
    races_df = store.get_races_data()
    selected_meeting = store.get_selected_meeting()

    if races_df is None or races_df.empty or selected_meeting is None:
        st.info("👈 Please select a date and meeting from the sidebar.")
        return

    # Filter races for current meeting
    meeting_races = races_df[
        races_df['meeting_number'] == selected_meeting
    ].sort_values('race_number')

    if meeting_races.empty:
        st.warning("No races found for this meeting.")
        return

    # Header
    racetrack_name = meeting_races.iloc[0]['racetrack_code']
    st.markdown(f"## 🏟️ Meeting {selected_meeting} : {racetrack_name}")

    # Create Tabs
    race_labels = [f"C{r['race_number']}" for _, r in meeting_races.iterrows()]
    tabs = st.tabs(race_labels)

    # Render Tabs
    for (idx, race_row), tab in zip(meeting_races.iterrows(), tabs):
        with tab:
            render_race_tab_content(race_row)

def render_race_tab_content(race_row):
    """Renders the content inside a single race tab."""
    col_info, col_action = st.columns([3, 1])
    
    with col_info:
        st.markdown(f"### 🚩 C{race_row['race_number']} - {race_row['discipline']}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Distance", f"{race_row['distance_m']} m")
        m2.metric("Runners", f"{race_row.get('declared_runners_count', '-')}")
        m3.metric("Racetrack", race_row['racetrack_code'])
        
    with col_action:
        # State Management
        is_analyzed = (store.get_selected_race() == race_row['race_id'])
        
        if is_analyzed:
             st.button("🔄 Refresh", key=f"btn_ref_{race_row['race_id']}")
        else:
            # CORRECTION: use_container_width=True -> width="stretch"
            if st.button(f"🧠 Analyze C{race_row['race_number']}", key=f"btn_ana_{race_row['race_id']}", type="primary", width="stretch"):
                store.set_selected_race(race_row['race_id'])
                st.rerun()

    st.divider()

    if store.get_selected_race() == race_row['race_id']:
        render_analysis_view(race_row['race_id'])