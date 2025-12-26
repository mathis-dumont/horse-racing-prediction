import logging
import streamlit as st
import pandas as pd
from datetime import datetime
from api_client import fetch_daily_races, fetch_predictions, fetch_participants

# --- LOGGING CONFIGURATION ---
# Initialize logging for the main application
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

# --- CUSTOM CSS (DESIGN SYSTEM & DARK MODE REMOVAL) ---
st.markdown("""
    <style>
    /* Force Light Mode Backgrounds & Text */
    .stApp {
        background-color: #f8f9fa !important;
        color: #1e293b !important;
    }
    
    /* Ensure all headers are dark */
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #1e293b;
    }

    /* Card Style for Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    div[data-testid="stMetricLabel"] p {
         color: #64748b !important;
    }
    
    div[data-testid="stMetricValue"] div {
         color: #1e293b !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e0e0e0;
    }
    
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #1e293b !important;
    }

    /* Tab Styling */
    button[data-baseweb="tab"] {
        color: #64748b !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #1e293b !important;
        border-bottom-color: #1e293b !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: NAVIGATION & FILTERS ---
with st.sidebar:
    st.title("🏇 Turf Analytics")
    st.markdown("---")
    
    st.subheader("📅 Schedule")
    selected_date = st.date_input("Select a date", datetime.today())
    formatted_date_code = selected_date.strftime("%d%m%Y")
    
    # Load global data for the selected date
    with st.spinner("Loading schedule..."):
        races_dataframe = fetch_daily_races(formatted_date_code)

    selected_meeting_number = None
    
    if not races_dataframe.empty:
        # Hierarchical Organization: Meeting first, then Race
        unique_meeting_numbers = sorted(races_dataframe['meeting_number'].unique())
        
        st.subheader("📍 Meeting")
        
        # Create enriched labels for the selectbox (e.g., "R1 - VINCENNES")
        meeting_labels = {}
        for meeting_num in unique_meeting_numbers:
            # Find the racetrack name from the first race of this meeting
            meeting_races = races_dataframe[races_dataframe['meeting_number'] == meeting_num]
            racetrack_code = meeting_races.iloc[0]['racetrack_code']
            meeting_labels[meeting_num] = f"R{meeting_num} - {racetrack_code}"
            
        selected_meeting_number = st.radio(
            "Choose a meeting:",
            unique_meeting_numbers,
            format_func=lambda x: meeting_labels[x]
        )
        
        st.markdown("---")
        st.caption("v2.1.0 • Powered by XGBoost")
    else:
        st.warning("No races available for this date.")

# --- MAIN CONTENT ---

if races_dataframe.empty:
    st.info("👈 Please select a date with scheduled races from the sidebar.")
    st.stop()

# Filter races for the selected meeting
selected_meeting_races = races_dataframe[
    races_dataframe['meeting_number'] == selected_meeting_number
].sort_values('race_number')

# 1. MEETING HEADER
current_racetrack_name = selected_meeting_races.iloc[0]['racetrack_code']
st.markdown(f"## 🏟️ Meeting {selected_meeting_number} : {current_racetrack_name}")

# 2. RACE SELECTOR
# Use tabs for ergonomics
race_tab_labels = [
    f"C{row['race_number']} - {row['discipline']}" 
    for _, row in selected_meeting_races.iterrows()
]
race_tabs = st.tabs(race_tab_labels)

for (idx, race_row), tab in zip(selected_meeting_races.iterrows(), race_tabs):
    with tab:
        # --- RACE HEADER ---
        col_info, col_action = st.columns([3, 1])
        
        with col_info:
            st.markdown(f"### 🚩 C{race_row['race_number']} - {race_row['discipline']}")
            
            # Metric Badges
            metric_1, metric_2, metric_3 = st.columns(3)
            metric_1.metric("Distance", f"{race_row['distance_m']} m")
            
            # Handle potential missing column for runners
            runner_count = race_row.get('declared_runners', "14") 
            metric_2.metric("Runners", runner_count)
            
            metric_3.metric("Racetrack", race_row['racetrack_code'])
            
        with col_action:
            # Main Action Button
            analyze_button_clicked = st.button(
                f"🧠 Analyze C{race_row['race_number']}", 
                key=f"btn_{race_row['race_id']}", 
                type="primary", 
                use_container_width=True
            )

        st.divider()

        # --- PREDICTION LOGIC ---
        if analyze_button_clicked:
            logger.info(f"User initiated analysis for Race {race_row['race_id']}")
            
            with st.spinner("Analyzing performance and calculating probabilities..."):
                prediction_data = fetch_predictions(race_row['race_id'])
                participant_data = fetch_participants(race_row['race_id'])
            
            if not prediction_data.empty:
                # Merge to get complete info (Driver, Trainer, Odds) if available
                if not participant_data.empty:
                    full_race_data = pd.merge(
                        prediction_data, 
                        participant_data[['pmu_number', 'driver_name', 'trainer_name', 'odds']], 
                        on='pmu_number', 
                        how='left'
                    )
                else:
                    full_race_data = prediction_data
                    full_race_data['driver_name'] = "N/A"
                    full_race_data['odds'] = None

                # Calculate "Confidence Score" (Gap between 1st and 2nd probability)
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

                # Display Top 3 Cards
                st.subheader(f"🏆 AI Forecast {confidence_stars}")
                
                col1, col2, col3 = st.columns(3)
                top_3_runners = full_race_data.head(3)
                
                columns = [col1, col2, col3]
                # Gold, Silver, Bronze hex codes
                rank_colors = ["#FFD700", "#C0C0C0", "#CD7F32"] 
                
                for i, (index, runner_row) in enumerate(top_3_runners.iterrows()):
                    # Ensure we don't go out of bounds if fewer than 3 runners
                    if i < 3:
                        with columns[i]:
                            st.markdown(
                                f"""
                                <div style="background-color: white; border-top: 5px solid {rank_colors[i]}; 
                                            padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
                                            text-align: center; color: #1e293b;">
                                    <h1 style="margin:0; font-size: 2.5em; color: #1e293b;">{runner_row['pmu_number']}</h1>
                                    <h4 style="margin:5px 0; color: #1e293b;">{runner_row['horse_name']}</h4>
                                    <p style="color: #64748b; font-size: 0.9em;">{runner_row.get('driver_name', '')}</p>
                                    <h2 style="color: {rank_colors[i]};">{runner_row['win_probability']*100:.1f}%</h2>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )

                st.markdown("### 📊 Detailed Analysis")
                
                # Prepare DataFrame for visual display
                display_df = full_race_data[[
                    'predicted_rank', 'pmu_number', 'horse_name', 
                    'driver_name', 'odds', 'win_probability'
                ]].copy()
                
                # Configure columns for st.dataframe
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "predicted_rank": st.column_config.NumberColumn(
                            "Rank",
                            format="%d 🏅",
                        ),
                        "pmu_number": st.column_config.NumberColumn(
                            "No.",
                            format="%d"
                        ),
                        "horse_name": "Horse",
                        "driver_name": "Driver/Jockey",
                        "odds": st.column_config.NumberColumn(
                            "Current Odds",
                            format="%.1f"
                        ),
                        "win_probability": st.column_config.ProgressColumn(
                            "Win Probability",
                            format="%.1f%%",
                            min_value=0,
                            max_value=1,
                        ),
                    }
                )
            else:
                st.error("Unable to generate predictions. The model API might be unavailable.")
                logger.error(f"Prediction dataframe empty for Race {race_row['race_id']}")
        
        else:
            # Clean "Waiting" State
            st.info("Click 'Analyze' to run the Machine Learning model.")
            
            # Optional: Display raw participants list if waiting
            raw_participant_data = fetch_participants(race_row['race_id'])
            if not raw_participant_data.empty:
                st.markdown("#### Declared Runners")
                st.dataframe(
                    raw_participant_data[['pmu_number', 'horse_name', 'driver_name', 'trainer_name']], 
                    hide_index=True, 
                    use_container_width=True
                )