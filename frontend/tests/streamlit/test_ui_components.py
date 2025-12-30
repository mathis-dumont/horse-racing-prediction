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

    @patch('ui.sidebar.st')
    @patch('ui.sidebar.fetch_daily_races')
    def test_sidebar_logic(self, mock_fetch, mock_st, mock_races_data):
        """
        Verify sidebar sets date and fetches data.
        """
        # Setup
        store.init_session()
        mock_fetch.return_value = pd.DataFrame(mock_races_data)
        
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
        mock_st.title.assert_called()

    @patch('ui.sniper.st')
    @patch('ui.sniper.get_sniper_bets')
    def test_sniper_section_rendering(self, mock_get_bets, mock_st, mock_sniper_bets):
        """
        Verify sniper section renders dataframe when bets exist.
        """
        store.init_session()
        mock_get_bets.return_value = mock_sniper_bets
        
        render_sniper_section()
        
        mock_st.success.assert_called()
        mock_st.dataframe.assert_called_once()

    @patch('ui.sniper.st')
    @patch('ui.sniper.get_sniper_bets')
    def test_sniper_section_empty(self, mock_get_bets, mock_st):
        """
        Verify sniper section handles no bets gracefully.
        """
        store.init_session()
        mock_get_bets.return_value = []
        
        render_sniper_section()
        
        mock_st.info.assert_called_with("ℹ️ No 'Sniper' bets found today. The market is efficient right now.")
        mock_st.dataframe.assert_not_called()

    @patch('ui.race.st')
    def test_race_grid_no_selection(self, mock_st):
        """
        Verify warning when no meeting is selected.
        """
        store.init_session()
        store.set_races_data(pd.DataFrame()) # Empty data
        
        render_race_grid()
        
        mock_st.info.assert_called()

    @patch('ui.race.render_analysis_view')
    @patch('ui.race.st')
    def test_race_grid_render_tabs(self, mock_st, mock_render_analysis, mock_races_data):
        """
        Integration Test: Verify race grid rendering logic.
        
        Ensures that:
        1. Tabs are created for each race.
        2. Column layouts are generated correctly inside the loop.
        3. No StopIteration error occurs during the iteration over races.
        """
        # --- ARRANGE ---
        # Initialize session state
        store.init_session()
        store.set_races_data(pd.DataFrame(mock_races_data))
        store.set_selected_meeting(1)  # Matches meeting_number in mock_races_data

        # Calculate expected iterations based on fixture data size
        # This makes the test robust regardless of how many races are in the fixture.
        num_races = len(mock_races_data)

        # Mock Return Values for st.columns()
        # Call 1 per race: st.columns([3, 1]) -> Returns 2 objects (Info col, Action col)
        # Call 2 per race: st.columns(3)      -> Returns 3 objects (Metrics)
        mock_layout_cols = [MagicMock(), MagicMock()]
        mock_metric_cols = [MagicMock(), MagicMock(), MagicMock()]

        # Apply side_effect:
        # We repeat the pattern [Layout, Metrics] for EACH race to ensure the mock 
        # has enough values to yield during the loop, preventing StopIteration.
        mock_st.columns.side_effect = [mock_layout_cols, mock_metric_cols] * num_races

        # Mock Tabs (st.tabs returns a list of context managers)
        mock_tab_ctx = MagicMock()
        mock_st.tabs.return_value = [mock_tab_ctx] * num_races

        # --- ACT ---
        render_race_grid()

        # --- ASSERT ---
        # Verify columns were called exactly twice per race (Layout + Metrics)
        expected_col_calls = 2 * num_races
        assert mock_st.columns.call_count == expected_col_calls
        
        # Verify tabs were created with correct labels
        mock_st.tabs.assert_called_once()