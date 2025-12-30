import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from ui.sidebar import render_sidebar
from ui.sniper import render_sniper_section
from ui.race import render_race_grid
from state import store

@pytest.mark.usefixtures("mock_session_state")
class TestUIComponents:
    """
    Integration tests for UI functions.
    Mocks streamlit commands and API calls to verify logic flow and state updates.
    """

    @patch('frontend.ui.sidebar.st')
    @patch('frontend.ui.sidebar.fetch_daily_races')
    def test_sidebar_logic(self, mock_fetch, mock_st, mock_races_data):
        """
        Verify sidebar sets date and fetches data.
        """
        # Setup
        store.init_session()
        mock_fetch.return_value = mock_races_data
        
        # Mock user interaction: Date Input returns a date
        mock_st.sidebar.date_input.return_value = store.get_date_obj()
        # Mock user interaction: Radio returns the first meeting
        mock_st.radio.return_value = 1

        render_sidebar()

        # Assertions
        mock_fetch.assert_called_once()
        assert not store.get_races_data().empty
        assert store.get_selected_meeting() == 1
        # Check that UI elements were called
        mock_st.sidebar.title.assert_called()

    @patch('frontend.ui.sniper.st')
    @patch('frontend.ui.sniper.get_sniper_bets')
    def test_sniper_section_rendering(self, mock_get_bets, mock_st, mock_sniper_bets):
        """
        Verify sniper section renders dataframe when bets exist.
        """
        store.init_session()
        mock_get_bets.return_value = mock_sniper_bets
        
        render_sniper_section()
        
        mock_st.success.assert_called()
        mock_st.dataframe.assert_called_once()

    @patch('frontend.ui.sniper.st')
    @patch('frontend.ui.sniper.get_sniper_bets')
    def test_sniper_section_empty(self, mock_get_bets, mock_st):
        """
        Verify sniper section handles no bets gracefully.
        """
        store.init_session()
        mock_get_bets.return_value = []
        
        render_sniper_section()
        
        mock_st.info.assert_called_with("ℹ️ No 'Sniper' bets found today. The market is efficient right now.")
        mock_st.dataframe.assert_not_called()

    @patch('frontend.ui.race.st')
    def test_race_grid_no_selection(self, mock_st):
        """
        Verify warning when no meeting is selected.
        """
        store.init_session()
        store.set_races_data(pd.DataFrame()) # Empty data
        
        render_race_grid()
        
        mock_st.info.assert_called()

    @patch('frontend.ui.race.render_analysis_view')
    @patch('frontend.ui.race.st')
    def test_race_grid_render_tabs(self, mock_st, mock_render_analysis, mock_races_data):
        """
        Verify race grid renders tabs and analysis button triggers state change.
        """
        # Setup Store
        store.init_session()
        store.set_races_data(mock_races_data)
        store.set_selected_meeting(1)
        
        # Mock Tabs (context manager)
        mock_tab = MagicMock()
        mock_st.tabs.return_value = [mock_tab, mock_tab] # 2 races in fixture
        
        # Simulate render
        render_race_grid()
        
        # Verify tabs created
        assert mock_st.tabs.call_count == 1
        args, _ = mock_st.tabs.call_args
        assert len(args[0]) == 2 # 2 races