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
        # FIX: Add 'age' column required by the feature engineer as fallback
        'age': [5, 6, 4], 
        'reference_odds': [2.5, 10.0, None],  # One missing odd
        'career_winnings': [5000, 10000, 0],
        'career_races_count': [5, 10, 0],     # One debutant
        'weather_temperature': [None, None, None], # Missing temp
        'racetrack_code': ['VINC', 'VINC', 'VINC']
    }
    df = pd.DataFrame(data)
    # SAFETY: Ensure dates are actual timestamps
    df['program_date'] = pd.to_datetime(df['program_date'])
    return df

def test_feature_engineering_dates_and_ages(feature_engineer, sample_data):
    """Test date parsing and age calculation."""
    df_transformed = feature_engineer.fit_transform(sample_data.copy())
    
    assert 'race_month' in df_transformed.columns
    assert df_transformed['race_month'].iloc[0] == 1
    
    # Age calculation: 2025 (program) - 2020 (birth) = 5
    assert df_transformed['horse_age_at_race'].iloc[0] == 5

def test_missing_values_imputation(feature_engineer, sample_data):
    """Test that nulls are handled via learned stats or grouping."""
    # Use copy to avoid modifying the fixture for other tests
    df_train = sample_data.copy()
    
    # Fit first to learn stats
    feature_engineer.fit(df_train)
    df_transformed = feature_engineer.transform(df_train)
    
    # Reference odds imputation
    assert not df_transformed['reference_odds'].isnull().any()
    
    # Logic: Race Avg (6.25) or Learned Global.
    # Since race_id is present, it uses race average of existing (2.5+10)/2 = 6.25
    # We use np.isclose for float comparisons to be safe
    assert np.isclose(df_transformed['reference_odds'].iloc[2], 6.25)

def test_financial_ratios_and_debutant(feature_engineer, sample_data):
    """Test specific business logic for money and experience."""
    df_transformed = feature_engineer.fit_transform(sample_data.copy())
    
    # Debutant check (0 career races)
    assert df_transformed['is_debutant'].iloc[2] == 1
    assert df_transformed['is_debutant'].iloc[0] == 0
    
    # Winnings per race smoothing check
    # Row 0: 5000 / (5 + 1) = 833.333...
    expected_wpr = 5000 / 6
    assert np.isclose(df_transformed['winnings_per_race'].iloc[0], expected_wpr)

def test_rank_features(feature_engineer, sample_data):
    """Test intra-race ranking logic."""
    df_transformed = feature_engineer.fit_transform(sample_data.copy())
    
    # Odds Rank logic:
    # 1. Impute: [2.5, 10.0, 6.25]
    # 2. Rank: 2.5 is lowest (Rank 1), 6.25 is middle (Rank 2), 10.0 is highest (Rank 3)
    
    assert 'odds_rank_in_race' in df_transformed.columns
    
    # Row 0 (2.5) should be rank 1
    assert df_transformed['odds_rank_in_race'].iloc[0] == 1.0
    
    # Row 2 (The computed 6.25) should be rank 2
    assert df_transformed['odds_rank_in_race'].iloc[2] == 2.0