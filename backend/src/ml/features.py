import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

class PmuFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Intelligent Scikit-learn Transformer.
    Integrates advanced business logic:
    - Debutant handling
    - Relative financial ratios
    - Intra-race rankings
    - Statistical imputation learned during fit().
    """

    def __init__(self):
        # Stats learned during fit
        self.learned_stats_ = {} 
        self.cat_fill_value_ = 'MISSING'

    def fit(self, X: pd.DataFrame, y=None) -> 'PmuFeatureEngineer':
        """Learns global statistics for imputation."""
        df = X.copy()
        
        # 1. Learn global average temperature
        if 'weather_temperature' in df.columns:
            self.learned_stats_['weather_temperature'] = df['weather_temperature'].mean()
            
        # 2. Learn average reference odds (for nulls)
        if 'reference_odds' in df.columns:
            self.learned_stats_['reference_odds'] = df['reference_odds'].mean()

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Applies transformations without data leakage."""
        df = X.copy()
        
        # --- 1. Dates & Ages ---
        if 'program_date' in df.columns:
            df['program_date'] = pd.to_datetime(df['program_date'])
            df['race_month'] = df['program_date'].dt.month
            df['race_day_of_week'] = df['program_date'].dt.dayofweek
            
            # Robust age calculation
            if 'birth_year' in df.columns:
                # Fallback to 'age' column if birth_year is missing, otherwise calculate
                current_year = df['program_date'].dt.year
                calculated_age = current_year - df['birth_year']
                df['horse_age_at_race'] = calculated_age.fillna(df['age'])
            else:
                df['horse_age_at_race'] = df['age']

        # --- 2. Intelligent Imputation ---
        # Temperature (By Racetrack if possible, otherwise Global learned)
        if 'weather_temperature' in df.columns:
            # First fill by track mean within this batch (if available)
            df['weather_temperature'] = df['weather_temperature'].fillna(
                df.groupby('racetrack_code')['weather_temperature'].transform('mean')
            )
            # Fallback to learned global value
            df['weather_temperature'] = df['weather_temperature'].fillna(
                self.learned_stats_.get('weather_temperature', 15.0)
            )

        # Categorical Filling
        cat_cols = ['racetrack_code', 'discipline', 'track_type', 'sex', 
                   'shoeing_status', 'jockey_name', 'trainer_name', 'terrain_label']
        for col in cat_cols:
            if col in df.columns:
                df[col] = df[col].fillna(self.cat_fill_value_).astype(str)

        # --- 3. Business Feature Engineering ---
        
        # A. Odds Logic
        if 'reference_odds' in df.columns:
            df['is_odds_missing'] = df['reference_odds'].isnull().astype(int)
            # Impute with average of the current RACE first
            if 'race_id' in df.columns:
                race_avg_odds = df.groupby('race_id')['reference_odds'].transform('mean')
                df['reference_odds'] = df['reference_odds'].fillna(race_avg_odds)
            
            # Final Fallback
            df['reference_odds'] = df['reference_odds'].fillna(
                self.learned_stats_.get('reference_odds', 10.0)
            )

            # Odds rank within the race (Powerful predictor)
            if 'race_id' in df.columns:
                df['odds_rank_in_race'] = df.groupby('race_id')['reference_odds'].rank(ascending=True, method='min')

        # B. Finances & Performance
        if 'career_winnings' in df.columns:
            df['career_winnings'] = df['career_winnings'].fillna(0)
            df['career_races_count'] = df['career_races_count'].fillna(0)
            
            # "Debutant" Flag
            df['is_debutant'] = (df['career_races_count'] == 0).astype(int)
            
            # Winnings per race
            df['winnings_per_race'] = df['career_winnings'] / (df['career_races_count'] + 1)
            
            if 'race_id' in df.columns:
                # Is this the richest horse in the race?
                df['winnings_rank_in_race'] = df.groupby('race_id')['career_winnings'].rank(ascending=False, method='min')
                
                # Ratio vs Race Average (Contextual)
                race_avg_earnings = df.groupby('race_id')['career_winnings'].transform('mean')
                df['relative_winnings'] = df['career_winnings'] / (race_avg_earnings + 1)

        return df