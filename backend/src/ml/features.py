"""
Feature engineering logic for transforming raw database data into 
model-ready numerical vectors.
"""
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

class PmuFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Custom Scikit-Learn transformer to handle feature engineering.
    Calculates ratios, relative ranks, and imputes missing values.
    """

    def fit(self, X: pd.DataFrame, y=None) -> 'PmuFeatureEngineer':
        """Fit method (stateless)."""
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Applies feature transformations to the input DataFrame.

        Args:
            X (pd.DataFrame): Raw input data.

        Returns:
            pd.DataFrame: Transformed DataFrame with engineered features.
        """
        df = X.copy()
        
        # 1. Dates & Ages Calculation
        if 'program_date' in df.columns:
            df['program_date'] = pd.to_datetime(df['program_date'])
            df['race_month'] = df['program_date'].dt.month
            df['race_day_of_week'] = df['program_date'].dt.dayofweek
            
            if 'birth_year' in df.columns:
                df['horse_age_at_race'] = df['program_date'].dt.year - df['birth_year']
                # Fallback to static age if calculation fails
                df['horse_age_at_race'] = df['horse_age_at_race'].fillna(df['age'])
            else:
                df['horse_age_at_race'] = df['age']

        # 2. Missing Value Imputation
        numerical_fill_values = {'career_winnings': 0, 'career_races_count': 0}
        for col, val in numerical_fill_values.items():
            if col in df.columns:
                df[col] = df[col].fillna(val)

        categorical_fill_columns = [
            'racetrack_code', 'discipline', 'track_type', 'sex', 
            'shoeing_status', 'jockey_name', 'trainer_name'
        ]
        for col in categorical_fill_columns:
            if col in df.columns:
                df[col] = df[col].fillna('UNKNOWN').astype(str)

        # 3. Feature Engineering (Business Logic)
        if 'career_winnings' in df.columns:
            # Indicator for horses with zero previous races
            df['is_debutant'] = (df['career_races_count'] == 0).astype(int)
            
            # Winnings per race ratio
            df['winnings_per_race'] = df['career_winnings'] / (df['career_races_count'] + 1)
            
            # --- RELATIVE FEATURES (Requires race context) ---
            # Grouping by race_id allows comparing horses within the same event.
            if 'race_id' in df.columns:
                # Rank Earnings: How this horse compares financially to rivals
                df['winnings_rank_in_race'] = df.groupby('race_id')['career_winnings'].rank(ascending=False, method='min')
                
                # Relative Winnings: Ratio against the average of the race
                race_averages = df.groupby('race_id')['career_winnings'].transform('mean')
                df['relative_winnings'] = df['career_winnings'] / (race_averages + 1)

        # 4. Odds Engineering
        if 'reference_odds' in df.columns:
            df['is_odds_missing'] = df['reference_odds'].isnull().astype(int)
            df['reference_odds'] = df['reference_odds'].fillna(10.0) # Neutral default value
            
            if 'race_id' in df.columns:
                df['odds_rank_in_race'] = df.groupby('race_id')['reference_odds'].rank(ascending=True, method='min')

        return df