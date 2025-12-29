# tests/unit/test_ml_features.py
import pytest
import pandas as pd
import numpy as np
from src.ml.features import PmuFeatureEngineer

@pytest.fixture
def feature_engineer():
    return PmuFeatureEngineer()

@pytest.fixture
def sample_data():
    """Creates a small DataFrame mimicking raw database output."""
    data = {
        'program_date': ['2025-01-01', '2025-01-01', '2025-01-01'],
        'race_id': [1, 1, 1],
        'birth_year': [2020, 2019, 2021],
        'reference_odds': [2.5, 10.0, None],  # One missing odd
        'career_winnings': [5000, 10000, 0],
        'career_races_count': [5, 10, 0],     # One debutant
        'weather_temperature': [None, None, None], # Missing temp
        'racetrack_code': ['VINC', 'VINC', 'VINC']
    }
    return pd.DataFrame(data)

def test_feature_engineering_dates_and_ages(feature_engineer, sample_data):
    """Test date parsing and age calculation."""
    df_transformed = feature_engineer.fit_transform(sample_data)
    
    assert 'race_month' in df_transformed.columns
    assert df_transformed['race_month'].iloc[0] == 1
    
    # Age calculation: 2025 (program) - 2020 (birth) = 5
    assert df_transformed['horse_age_at_race'].iloc[0] == 5

def test_missing_values_imputation(feature_engineer, sample_data):
    """Test that nulls are handled via learned stats or grouping."""
    # Fit first to learn stats
    feature_engineer.fit(sample_data)
    df_transformed = feature_engineer.transform(sample_data)
    
    # Reference odds imputation
    assert not df_transformed['reference_odds'].isnull().any()
    # The missing odd should be filled. In logic: Race Avg (6.25) or Learned Global.
    # Since race_id is present, it uses race average of existing (2.5+10)/2 = 6.25
    assert df_transformed['reference_odds'].iloc[2] == 6.25

def test_financial_ratios_and_debutant(feature_engineer, sample_data):
    """Test specific business logic for money and experience."""
    df_transformed = feature_engineer.fit_transform(sample_data)
    
    # Debutant check (0 career races)
    assert df_transformed['is_debutant'].iloc[2] == 1
    assert df_transformed['is_debutant'].iloc[0] == 0
    
    # Winnings per race
    # Row 0: 5000 / (5 + 1) = 833.33
    expected_wpr = 5000 / 6
    assert np.isclose(df_transformed['winnings_per_race'].iloc[0], expected_wpr)

def test_rank_features(feature_engineer, sample_data):
    """Test intra-race ranking logic."""
    df_transformed = feature_engineer.fit_transform(sample_data)
    
    # Odds Rank: 2.5 is lowest (1), 6.25 is mid (2), 10 is high (3)
    # Note: Logic fills NA before ranking.
    assert 'odds_rank_in_race' in df_transformed.columns
    # Row 0 (2.5) should be rank 1
    assert df_transformed['odds_rank_in_race'].iloc[0] == 1.0