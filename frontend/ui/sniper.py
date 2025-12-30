import streamlit as st
import pandas as pd
from api.api_client import get_sniper_bets
import state.store as store

def render_sniper_section():
    date_code = store.get_date_code()
    
    st.markdown("## 🎯 AI Sniper Recommendations")
    
    with st.spinner(f"Scanning market for {date_code}..."):
        sniper_bets = get_sniper_bets(date_code)
    
    if sniper_bets:
        st.success(f"✅ The model identified **{len(sniper_bets)} high-value opportunities** today.")
        
        bet_rows = []
        for bet in sniper_bets:
            bet_rows.append({
                "Race": f"C{bet.get('race_num', '?')}", 
                "Horse": f"#{bet.get('program_number', '?')} {bet.get('horse_name', 'Unknown')}",
                "Odds": f"{bet.get('odds', 0):.1f}",
                "AI Prob": f"{bet.get('win_probability', 0)*100:.1f}%",
                "Edge": f"+{bet.get('edge', 0)*100:.1f}%",
                "Strategy": "Mid-Range Value"
            })
        
        # CORRECTION: use_container_width=True -> width="stretch"
        st.dataframe(
            pd.DataFrame(bet_rows),
            width="stretch",
            hide_index=True,
            column_config={
                "Edge": st.column_config.TextColumn("Edge", help="Diff AI vs Market"),
                "AI Prob": st.column_config.ProgressColumn("Win Probability", min_value=0, max_value=100, format="%s")
            }
        )
    else:
        st.info("ℹ️ No 'Sniper' bets found today. The market is efficient right now.")