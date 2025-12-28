import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

class PmuFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Transformateur sklearn intelligent.
    Intègre la logique métier avancée :
    - Gestion des débutants
    - Ratios financiers relatifs
    - Classements intra-course (Ranks)
    - Imputation statistique apprise lors du fit().
    """

    def __init__(self):
        # Stats apprises durant le fit
        self.defaults_ = {} 
        self.cat_fill_value_ = 'MISSING'

    def fit(self, X: pd.DataFrame, y=None) -> 'PmuFeatureEngineer':
        """Apprend les statistiques globales pour l'imputation."""
        df = X.copy()
        
        # 1. Apprendre la température moyenne globale
        if 'weather_temperature' in df.columns:
            self.defaults_['weather_temperature'] = df['weather_temperature'].mean()
            
        # 2. Apprendre la cote de référence moyenne (pour les nulls)
        if 'reference_odds' in df.columns:
            self.defaults_['reference_odds'] = df['reference_odds'].mean()

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Applique les transformations sans fuite de données."""
        df = X.copy()
        
        # --- 1. Dates & Âges ---
        if 'program_date' in df.columns:
            df['program_date'] = pd.to_datetime(df['program_date'])
            df['race_month'] = df['program_date'].dt.month
            df['race_day_of_week'] = df['program_date'].dt.dayofweek
            
            # Calcul robuste de l'âge
            if 'birth_year' in df.columns:
                # Fallback sur 'age' si birth_year manquant, sinon calcul
                current_year = df['program_date'].dt.year
                calculated_age = current_year - df['birth_year']
                df['horse_age_at_race'] = calculated_age.fillna(df['age'])
            else:
                df['horse_age_at_race'] = df['age']

        # --- 2. Imputation Intelligente ---
        # Température (Par Racetrack si possible, sinon Global appris)
        if 'weather_temperature' in df.columns:
            # On remplit d'abord par la moyenne du track dans ce batch (si dispo)
            df['weather_temperature'] = df['weather_temperature'].fillna(
                df.groupby('racetrack_code')['weather_temperature'].transform('mean')
            )
            # Sinon valeur globale apprise
            df['weather_temperature'] = df['weather_temperature'].fillna(self.defaults_.get('weather_temperature', 15.0))

        # Categorial Filling
        cat_cols = ['racetrack_code', 'discipline', 'track_type', 'sex', 
                   'shoeing_status', 'jockey_name', 'trainer_name', 'terrain_label']
        for col in cat_cols:
            if col in df.columns:
                df[col] = df[col].fillna(self.cat_fill_value_).astype(str)

        # --- 3. Feature Engineering Métier (Le "Power" du script) ---
        
        # A. Cotes (Odds) Logic
        if 'reference_odds' in df.columns:
            df['is_odds_missing'] = df['reference_odds'].isnull().astype(int)
            # Impute avec moyenne de la COURSE courante d'abord
            if 'race_id' in df.columns:
                race_avg_odds = df.groupby('race_id')['reference_odds'].transform('mean')
                df['reference_odds'] = df['reference_odds'].fillna(race_avg_odds)
            
            # Fallback final
            df['reference_odds'] = df['reference_odds'].fillna(self.defaults_.get('reference_odds', 10.0))

            # Rang de la cote dans la course (puissant pour le modèle)
            if 'race_id' in df.columns:
                df['odds_rank_in_race'] = df.groupby('race_id')['reference_odds'].rank(ascending=True, method='min')

        # B. Finances & Performance
        if 'career_winnings' in df.columns:
            df['career_winnings'] = df['career_winnings'].fillna(0)
            df['career_races_count'] = df['career_races_count'].fillna(0)
            
            # Drapeau "Débutant"
            df['is_debutant'] = (df['career_races_count'] == 0).astype(int)
            
            # Gains par course
            df['winnings_per_race'] = df['career_winnings'] / (df['career_races_count'] + 1)
            
            if 'race_id' in df.columns:
                # Est-ce le cheval le plus riche de la course ?
                df['winnings_rank_in_race'] = df.groupby('race_id')['career_winnings'].rank(ascending=False, method='min')
                
                # Ratio vs Moyenne de la course (Contextuel)
                race_avg_earnings = df.groupby('race_id')['career_winnings'].transform('mean')
                df['relative_winnings'] = df['career_winnings'] / (race_avg_earnings + 1)

        return df