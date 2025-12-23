import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

file_path = "../scripts/data/data_training_participants.csv"

def prepare_pmu_dataset(file_path):
    '''Prepare a dataset with all features extracted from data_training_participants'''
    df = pd.read_csv(file_path)
    
    # --- 1. DATETIME & TEMPORAL FEATURES ---
    df['program_date'] = pd.to_datetime(df['program_date'])
    df['race_month'] = df['program_date'].dt.month
    df['race_day_of_week'] = df['program_date'].dt.dayofweek
    df['horse_age_at_race'] = df['program_date'].dt.year - df['birth_year']
    
    # --- 2. ADVANCED IMPUTATION ---
    
    # Categorical/String Imputation: Fill with 'UNKNOWN' or the most frequent value per track
    cat_cols = ['weather_wind', 'track_type', 'terrain_label', 'shoeing_status', 'trainer_advice']
    for col in cat_cols:
        df[col] = df[col].fillna('MISSING')
        
    # Numerical Imputation: Temperature (Fill by Track/Date average, then global average)
    df['weather_temperature'] = df.groupby('racetrack_code')['weather_temperature'].transform(
        lambda x: x.fillna(x.mean())
    )
    df['weather_temperature'] = df['weather_temperature'].fillna(df['weather_temperature'].mean())
    
    # 1. Create a flag so the model knows the data was missing
    df['is_odds_missing'] = df['reference_odds'].isnull().astype(int)

    # 2. Impute with a neutral value (like the Race Average) 
    # This prevents the "99.0" outlier effect
    df['reference_odds'] = df['reference_odds'].fillna(
        df.groupby('race_id')['reference_odds'].transform('mean')
    )

    # 3. Fallback for races where EVERY horse has missing odds (rare)
    df['reference_odds'] = df['reference_odds'].fillna(10.0) # A neutral middle-ground

    # --- 3. FEATURE ENGINEERING (RELATIVE STRENGTH) ---
    
    # Career Efficiency
    df['winnings_per_race'] = df['career_winnings'] / (df['career_races_count'] + 1)
    
    # Grouped Features: Rank the horse within its specific race
    # (Higher earnings vs others usually indicates a higher class of horse)
    df['winnings_rank_in_race'] = df.groupby('race_id')['career_winnings'].rank(ascending=False)
    df['odds_rank_in_race'] = df.groupby('race_id')['reference_odds'].rank(ascending=True)
    
    # Relative Winnings: How many times richer is this horse than the race average?
    race_avg_winnings = df.groupby('race_id')['career_winnings'].transform('mean')
    df['relative_winnings'] = df['career_winnings'] / (race_avg_winnings + 1)

    # --- 4. CATEGORICAL ENCODING ---
    # We use Label Encoding here for a flat dataset. 
    # For Trainers/Jockeys, we handle them as strings but clean them first.
    le = LabelEncoder()
    encode_me = ['racetrack_code', 'discipline', 'track_type', 'sex', 
                 'jockey_name', 'trainer_name', 'shoeing_status']
    
    for col in encode_me:
        df[f'{col}_encoded'] = le.fit_transform(df[col].astype(str))

    return df
# --- 5. CLEANUP ---
    # Drop "Future" leakage and raw strings if we only want the numbers
    # But for a "full" dataset, we keep them for our own custom processing.
    
def finalize_ml_ready_dataset(df):
    '''Deal with missing values with smart imputations'''
    # 1. FIX IDENTITY GAPS
    # Backfill birth year using the 'age' column (which has 0 missing)
    df['birth_year'] = df['birth_year'].fillna(df['program_date'].dt.year - df['age'])
    # Fill sex with the most common value (mode)
    df['sex'] = df['sex'].fillna(df['sex'].mode()[0])
    
    # 2. CREATE THE "DEBUTANT" FEATURE
    # This captures the 282k missing values as a specific binary signal
    df['is_debutant'] = df['career_winnings'].isnull().astype(int)
    
    # 3. FILL FINANCIAL GAPS (The 282,329 rows)
    df['career_winnings'] = df['career_winnings'].fillna(0)
    df['career_races_count'] = df['career_races_count'].fillna(0)
    
    # 4. RE-CALCULATE DERIVED FEATURES
    # Now that we have 0s instead of NaNs, these formulas will work perfectly
    df['winnings_per_race'] = df['career_winnings'] / (df['career_races_count'] + 1)
    
    # Contextual relative winnings (how rich vs the field)
    race_avg = df.groupby('race_id')['career_winnings'].transform('mean')
    df['relative_winnings'] = df['career_winnings'] / (race_avg + 1)
    
    # Rank of the horse in this specific race by wealth
    df['winnings_rank_in_race'] = df.groupby('race_id')['career_winnings'].rank(ascending=False, method='min')

    # 5. FINAL IMPUTATION
    df['trainer_name'] = df['trainer_name'].fillna('UNKNOWN_TRAINER')
    # If live_odds are missing (20k rows), use reference_odds as a proxy
    df['live_odds'] = df['live_odds'].fillna(df['reference_odds'])
    
    # 6. CALCULATE HORSE AGE AT RACE (Fixing the 9k missing)
    df['horse_age_at_race'] = df['program_date'].dt.year - df['birth_year']

    return df

df_prepared = prepare_pmu_dataset(file_path)
# Apply the final cleaning
df_ml = finalize_ml_ready_dataset(df_prepared)

# Final check
# Save the final CSV
df_ml.to_csv('../scripts/data/final_ml_dataset.csv', index=False)

