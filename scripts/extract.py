import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# --- 1. CONNECTION CONFIGURATION ---
load_dotenv()

db_url = os.getenv("DB_URL")
if not db_url:
    raise ValueError("DB_URL is not set in the .env file or environment variables.")

engine = create_engine(db_url)

# --- 2. SQL QUERY TO BUILD DATASET ---
# Here we use %% to escape the % character in SQLAlchemy text queries

sql_query = """
SELECT
    -- --- IDENTIFIERS & TARGET ---
    r.race_id,
    r.race_number,
    prog.program_date as race_date,
    rp.horse_id,
    rp.finish_rank as target_rank,
    
    -- --- CONTEXTUAL FEATURES (RACE) ---
    rm.racetrack_code as racetrack,
    r.distance_m as distance,
    rm.weather_temperature,
    
    -- --- HORSE & HUMAN FEATURES ---
    -- rp.horse_name,  <-- REMOVED: Name not needed for ML, ID is sufficient
    rp.age,
    rp.sex,
    rp.shoeing_status,
    rp.driver_jockey_name as driver,
    rp.trainer_name as trainer,
    rp.career_winnings as career_earnings,
    rp.reference_odds as morning_odds,
    
    -- --- CALCULATED HISTORY ---
    hist.avg_red_km_last_5,
    hist.nb_races_last_5,
    hist.nb_dai_last_5,      -- Disqualification rate
    hist.avg_place_last_5,
    hist.days_since_last_race
    
FROM race_participant rp
JOIN race r ON rp.race_id = r.race_id
JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
JOIN daily_program prog ON rm.program_id = prog.program_id

-- LATERAL JOIN FOR HISTORY
-- Allows calculating stats for each horse dynamically based on the specific race date
LEFT JOIN LATERAL (
    SELECT 
        AVG(sub.reduction_km) FILTER (WHERE sub.reduction_km > 0) as avg_red_km_last_5,
        COUNT(*) as nb_races_last_5,
        -- Count disqualifications (DAI/DIS)
        COUNT(*) FILTER (WHERE sub.finish_status LIKE '%%DAI%%' OR sub.finish_status LIKE '%%DIS%%') as nb_dai_last_5,
        AVG(sub.finish_place) FILTER (WHERE sub.finish_place > 0) as avg_place_last_5,
        MIN(prog.program_date - sub.race_date) as days_since_last_race
    FROM (
        -- SUBQUERY: Retrieve raw data for the last 5 races strictly before today
        SELECT 
            h.reduction_km, 
            h.finish_status, 
            h.finish_place, 
            h.race_date
        FROM horse_race_history h
        WHERE h.horse_id = rp.horse_id
          AND h.race_date < prog.program_date -- Prevent Data Leakage
          AND h.discipline = 'ATTELE'         -- Filter for relevant discipline
        ORDER BY h.race_date DESC
        LIMIT 5
    ) sub 
) hist ON TRUE

WHERE 
    r.discipline = 'ATTELE'               -- Global Filter: Harness Trot only
    AND prog.program_date >= '2023-01-01' -- Training period
    AND rp.finish_rank IS NOT NULL        -- Keep only finished races (or handle NULLs later)
"""

# --- 3. EXECUTION & CLEANING ---
print("Executing SQL query (this may take some time)...")

try:
    # Open explicit connection for SQLAlchemy 2.0 compatibility
    with engine.connect() as connection:
        # Wrap query with text() for safety
        df = pd.read_sql(text(sql_query), connection)
    
    print(f"Data loaded successfully: {len(df)} rows.")
    

    # --- 4. ADVANCED PRE-PROCESSING ---

    # A. Timedelta Correction
    # If database returns a date object, pandas creates Timedeltas. We need Integers (days).
    if pd.api.types.is_timedelta64_dtype(df['days_since_last_race']):
        df['days_since_last_race'] = df['days_since_last_race'].dt.days

    # B. NULL Handling (Imputation)
    
    # Freshness: If NULL, it implies a debut or a very long break.
    # Set to 365 days (arbitrary high value).
    df['days_since_last_race'] = df['days_since_last_race'].fillna(365)

    # Kilometer Reduction (Speed):
    # Instead of mean (which benefits unknown horses), we use a "slow" value or a flag.
    df['is_debutant'] = df['nb_races_last_5'].fillna(0) == 0
    
    # Impute missing speed with the slowest time in the dataset (worst case scenario)
    worst_red_km = df['avg_red_km_last_5'].max() 
    df['avg_red_km_last_5'] = df['avg_red_km_last_5'].fillna(worst_red_km)
    
    # C. Target Engineering
    # If the SQL filter 'IS NOT NULL' was removed, handle missing ranks (DAI) here.
    # 99 represents a non-placed/disqualified horse.
    df['target_rank'] = df['target_rank'].fillna(99).astype(int)

    # D. Odds Encoding
    # Fill missing odds with 50/1 (considered a long shot/outsider).
    df['morning_odds'] = df['morning_odds'].fillna(50.0)

    # E. Type Optimization (Memory Usage)
    categorical_cols = ['racetrack', 'shoeing_status', 'driver', 'trainer', 'sex']

    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype('category')

    
    # --- 5. SAVE ---
    output_file = "dataset_trot_attele.csv"
    df.to_csv(output_file, index=False)
    print(f"File saved: {output_file}")
    
    print("\nPreview of the first 5 rows:")
    print(df.head())

except Exception as e:
    print(f"Error during extraction: {e}")