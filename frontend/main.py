import logging
import streamlit as st
import pandas as pd
from datetime import datetime
from api_client import fetch_daily_races, fetch_predictions, fetch_participants, get_sniper_bets

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Turf Analytics Pro",
    layout="wide",
    page_icon="🏇",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa !important; color: #1e293b !important; }
    h1, h2, h3, h4, h5, h6, p, span, div { color: #1e293b; }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] p { color: #64748b !important; }
    div[data-testid="stMetricValue"] div { color: #1e293b !important; }
    </style>
""", unsafe_allow_html=True)

def main():
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🏇 Turf Analytics")
        st.markdown("---")
        
        st.subheader("📅 Schedule")
        selected_date = st.date_input("Select a date", datetime.today())
        formatted_date_code = selected_date.strftime("%d%m%Y")
        
        with st.spinner("Loading schedule..."):
            races_dataframe = fetch_daily_races(formatted_date_code)

        selected_meeting_number = None
        
        if not races_dataframe.empty:
            unique_meeting_numbers = sorted(races_dataframe['meeting_number'].unique())
            st.subheader("📍 Meeting")
            
            meeting_labels = {}
            for meeting_num in unique_meeting_numbers:
                meeting_races = races_dataframe[races_dataframe['meeting_number'] == meeting_num]
                racetrack_code = meeting_races.iloc[0]['racetrack_code']
                meeting_labels[meeting_num] = f"R{meeting_num} - {racetrack_code}"
                
            selected_meeting_number = st.radio(
                "Choose a meeting:",
                unique_meeting_numbers,
                format_func=lambda x: meeting_labels[x]
            )
            st.markdown("---")
            st.caption("v3.1.0 • Powered by Calibrated XGBoost")
        else:
            st.warning("No races available for this date.")

    # --- MAIN CONTENT ---
    if races_dataframe.empty:
        st.info("👈 Please select a date with scheduled races from the sidebar.")
        st.stop()

    # ----------------------------------------------------
    # SECTION 1: AI SNIPER RECOMMENDATIONS (Top of Dashboard)
    # ----------------------------------------------------
    st.markdown("## 🎯 AI Sniper Recommendations")
    
    with st.spinner(f"Scanning all races on {formatted_date_code} for value bets..."):
        sniper_bets = get_sniper_bets(formatted_date_code)
    
    if sniper_bets:
        st.success(f"✅ The model identified **{len(sniper_bets)} high-value opportunities** today.")
        
        bet_rows = []
        for bet in sniper_bets:
            # --- FIX STARTS HERE ---
            # Safely parse race_id to avoid IndexError if format differs
            race_id_str = str(bet['race_id'])
            if '_' in race_id_str:
                # Expected format "27122025_R1" -> Split gives ["27122025", "R1"]
                # We want the "1" from "R1"
                parts = race_id_str.split('_')
                if len(parts) > 1:
                    race_suffix = parts[1][1:] # Removes 'R'
                else:
                    race_suffix = race_id_str
            else:
                # Fallback if no underscore exists
                race_suffix = race_id_str
            # --- FIX ENDS HERE ---

            bet_rows.append({
                "Race": f"R{race_suffix} C{bet['race_num']}", 
                "Horse": f"#{bet['pmu_number']} {bet['horse_name']}",
                "Odds": f"{bet['odds']:.1f}",
                "AI Prob": f"{bet['win_probability']*100:.1f}%",
                "Edge": f"+{bet['edge']*100:.1f}%",
                "Strategy": "Mid-Range Value"
            })
        
        st.dataframe(
            pd.DataFrame(bet_rows),
            width="stretch",
            hide_index=True,
            column_config={
                "Edge": st.column_config.TextColumn("Edge", help="Difference between AI Prob and Market Implied Prob"),
                "AI Prob": st.column_config.ProgressColumn("Win Probability", min_value=0, max_value=100, format="%s")
            }
        )
    else:
        st.info("ℹ️ No 'Sniper' bets found today. The market is efficient right now.")

    # ----------------------------------------------------
    # SECTION 2: RACE ANALYSIS VIEW
    # ----------------------------------------------------
    selected_meeting_races = races_dataframe[
        races_dataframe['meeting_number'] == selected_meeting_number
    ].sort_values('race_number')

    current_racetrack_name = selected_meeting_races.iloc[0]['racetrack_code']
    st.markdown(f"## 🏟️ Meeting {selected_meeting_number} : {current_racetrack_name}")

    race_tab_labels = [
        f"C{row['race_number']} - {row['discipline']}" 
        for _, row in selected_meeting_races.iterrows()
    ]
    race_tabs = st.tabs(race_tab_labels)

    for (idx, race_row), tab in zip(selected_meeting_races.iterrows(), race_tabs):
        with tab:
            col_info, col_action = st.columns([3, 1])
            
            with col_info:
                st.markdown(f"### 🚩 C{race_row['race_number']} - {race_row['discipline']}")
                metric_1, metric_2, metric_3 = st.columns(3)
                metric_1.metric("Distance", f"{race_row['distance_m']} m")
                runner_count = race_row.get('declared_runners', "14") 
                metric_2.metric("Runners", runner_count)
                metric_3.metric("Racetrack", race_row['racetrack_code'])
                
            with col_action:
                analyze_button_clicked = st.button(
                    f"🧠 Analyze C{race_row['race_number']}", 
                    key=f"btn_{race_row['race_id']}", 
                    type="primary", 
                    width="stretch"
                )

            st.divider()

            if analyze_button_clicked:
                with st.spinner("Calculating probabilities..."):
                    prediction_data = fetch_predictions(race_row['race_id'])
                    participant_data = fetch_participants(race_row['race_id'])
                
                if not prediction_data.empty:
                    # Merge data to get Driver and Odds
                    if not participant_data.empty:
                        full_race_data = pd.merge(
                            prediction_data, 
                            participant_data[['pmu_number', 'driver_name', 'odds']], 
                            on='pmu_number', 
                            how='left'
                        )
                    else:
                        full_race_data = prediction_data
                        full_race_data['driver_name'] = "N/A"
                        full_race_data['odds'] = None

                    # --- CONFIDENCE SCORE ---
                    if len(full_race_data) >= 2:
                        top_1_prob = full_race_data.iloc[0]['win_probability']
                        top_2_prob = full_race_data.iloc[1]['win_probability']
                        prob_diff = top_1_prob - top_2_prob
                        
                        if prob_diff > 0.1:
                            confidence_stars = "⭐⭐⭐"
                        elif prob_diff > 0.05:
                            confidence_stars = "⭐⭐"
                        else:
                            confidence_stars = "⭐"
                    else:
                        confidence_stars = "⭐"

                    # Display Top 3 with Stars
                    st.subheader(f"🏆 AI Forecast {confidence_stars}")
                    
                    col1, col2, col3 = st.columns(3)
                    top_3 = full_race_data.head(3)
                    # Colors: Gold, Silver, Bronze
                    colors = ["#FFD700", "#C0C0C0", "#CD7F32"] 
                    
                    for i, (idx_r, row) in enumerate(top_3.iterrows()):
                        if i < 3:
                            with [col1, col2, col3][i]:
                                st.markdown(
                                    f"""<div style="background:white; border-top:5px solid {colors[i]}; padding:15px; border-radius:8px; text-align:center; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                                        <h2 style="margin:0; color:#333;">#{row['pmu_number']}</h2>
                                        <div style="font-weight:bold; color:#555;">{row['horse_name']}</div>
                                        <div style="font-size:0.9em; color:#888;">{row.get('driver_name', '')}</div>
                                        <div style="color:{colors[i]}; font-size:1.4em; font-weight:bold; margin-top:5px;">{row['win_probability']*100:.1f}%</div>
                                    </div>""", unsafe_allow_html=True
                                )

                    # Detailed Analysis Table
                    st.markdown("### 📊 Detailed Analysis")
                    st.dataframe(
                        full_race_data[['predicted_rank', 'pmu_number', 'horse_name', 'driver_name', 'odds', 'win_probability']],
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "predicted_rank": st.column_config.NumberColumn("Rank", format="%d 🏅"),
                            "pmu_number": "No.",
                            "horse_name": "Horse",
                            "driver_name": "Driver/Jockey",
                            "odds": st.column_config.NumberColumn("Odds", format="%.1f"),
                            "win_probability": st.column_config.ProgressColumn(
                                "Win Probability", 
                                format="%.1f%%", 
                                min_value=0, 
                                max_value=1
                            )
                        }
                    )
                else:
                    st.error("Prediction failed. The API might be unavailable.")
            else:
                st.info("Click 'Analyze' to view AI predictions.")

if __name__ == "__main__":
    main()