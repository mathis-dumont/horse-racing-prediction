import streamlit as st
import pandas as pd
from api.api_client import fetch_predictions, fetch_participants

def render_analysis_view(race_id: int):
    """
    Renders the detailed prediction tables and cards for a specific race.
    """
    with st.spinner("Calculating probabilities..."):
        prediction_data = fetch_predictions(race_id)
        participant_data = fetch_participants(race_id)
    
    if prediction_data.empty:
        st.error("Prediction failed or data unavailable.")
        return

    # Merge Logic
    if not participant_data.empty:
        cols_to_use = ['program_number', 'driver_name', 'odds']
        actual_cols = [c for c in cols_to_use if c in participant_data.columns]
        
        full_race_data = pd.merge(
            prediction_data, 
            participant_data[actual_cols], 
            on='program_number', 
            how='left'
        )
    else:
        full_race_data = prediction_data
        full_race_data['driver_name'] = "N/A"
        full_race_data['odds'] = None

    # Sort by probability
    if 'win_probability' in full_race_data.columns:
        full_race_data = full_race_data.sort_values(by='win_probability', ascending=False)

    # 1. Top 3 Cards
    st.subheader("🏆 AI Forecast")
    
    col1, col2, col3 = st.columns(3)
    top_3 = full_race_data.head(3)
    colors = ["#FFD700", "#C0C0C0", "#CD7F32"] 
    
    for i, (idx_r, row) in enumerate(top_3.iterrows()):
        if i < 3:
            with [col1, col2, col3][i]:
                st.markdown(
                    f"""<div style="background:white; border-top:5px solid {colors[i]}; padding:15px; border-radius:8px; text-align:center; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                        <h2 style="margin:0; color:#333;">#{row.get('program_number', '-')}</h2>
                        <div style="font-weight:bold; color:#555;">{row.get('horse_name', 'Unknown')}</div>
                        <div style="font-size:0.9em; color:#888;">{row.get('driver_name', '')}</div>
                        <div style="color:{colors[i]}; font-size:1.4em; font-weight:bold; margin-top:5px;">{row.get('win_probability', 0)*100:.1f}%</div>
                    </div>""", unsafe_allow_html=True
                )

    # 2. Detailed Table
    st.markdown("### 📊 Detailed Analysis")
    
    display_cols = ['predicted_rank', 'program_number', 'horse_name', 'driver_name', 'odds', 'win_probability']
    display_cols = [c for c in display_cols if c in full_race_data.columns]

    # CORRECTION: use_container_width=True -> width="stretch"
    st.dataframe(
        full_race_data[display_cols],
        width="stretch",
        hide_index=True,
        column_config={
            "predicted_rank": st.column_config.NumberColumn("Rank", format="%d 🏅"),
            "program_number": "No.",
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