import logging
import streamlit as st
from ui.sidebar import render_sidebar
from ui.sniper import render_sniper_section
from ui.race import render_race_grid
from state.store import init_session

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
st.set_page_config(
    page_title="Turf Analytics Pro",
    layout="wide",
    page_icon="🏇",
    initial_sidebar_state="expanded"
)

# --- CSS INJECTION ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa !important; color: #1e293b !important; }
    h1, h2, h3, h4, h5, h6, p, span, div { color: #1e293b; }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

def main():
    # 1. Initialize State
    init_session()
    
    # 2. Render Sidebar (Handling Inputs)
    render_sidebar()
    
    # 3. Render Main Content (Reading State)
    render_sniper_section()
    render_race_grid()

if __name__ == "__main__":
    main()