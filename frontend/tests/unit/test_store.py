import pytest
from datetime import datetime
from state import store

class TestStore:
    """
    Tests business logic related to session state management.
    Ensures state transitions (resetting downstream selections) work correctly.
    """

    def test_init_session(self):
        """Test that session state is initialized with default values."""
        store.init_session()
        
        assert isinstance(store.get_date_obj(), datetime)
        assert store.get_selected_meeting() is None
        assert store.get_selected_race() is None
        assert store.get_races_data() is None

    def test_get_date_code_format(self):
        """Test that date is returned in DDMMYYYY format."""
        test_date = datetime(2023, 10, 25)
        store.init_session()
        store.set_date(test_date)
        
        assert store.get_date_code() == "25102023"

    def test_set_date_resets_downstream_state(self):
        """Changing the date should reset selected meeting and race."""
        store.init_session()
        
        # Set initial state
        store.set_selected_meeting(1)
        store.set_selected_race(101)
        
        # Change date
        new_date = datetime(2023, 12, 1)
        store.set_date(new_date)
        
        assert store.get_date_obj() == new_date
        assert store.get_selected_meeting() is None
        assert store.get_selected_race() is None

    def test_set_meeting_resets_race(self):
        """Changing the meeting should reset the selected race."""
        store.init_session()
        store.set_selected_race(101)
        
        store.set_selected_meeting(2)
        
        assert store.get_selected_meeting() == 2
        assert store.get_selected_race() is None

    def test_set_meeting_idempotent(self):
        """Setting the same meeting should not wipe the race selection."""
        store.init_session()
        store.set_selected_meeting(1)
        store.set_selected_race(101)
        
        # Set same meeting
        store.set_selected_meeting(1)
        
        assert store.get_selected_race() == 101