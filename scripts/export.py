import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# 1. SETUP & CONNECTION

load_dotenv()

# Check if DB_URL exists in .env
if "DB_URL" not in os.environ:
    print(" Error: DB_URL not found in .env file.")
    print("   Make sure your .env file contains: DB_URL=postgresql://...")
    exit(1)

db_url = os.environ["DB_URL"]
engine = create_engine(db_url)
os.makedirs("data", exist_ok=True)

# 2. SQL QUERIES
# ------------------------------------------------------------------

# QUERY 1: Main Participants Data
# We use LEFT JOINs to fetch text labels (names, codes) from IDs
QUERY_MAIN = """
SELECT
    -- IDs (Useful for debugging/merging)
    rp.participant_id,
    rp.race_id,
    rp.horse_id,

    -- 1. Context (Date, Weather, Track)
    prog.program_date,
    rm.racetrack_code,
    rm.weather_temperature,
    rm.weather_wind,

    -- 2. Race Conditions
    r.race_number,
    r.discipline,
    r.distance_m,
    r.track_type,           -- e.g. G (Grass), P (Pouzzolane)
    r.terrain_label,        -- e.g. BON, SOUPLE
    r.declared_runners_count,
    
    -- 3. The Horse (Static)
    h.horse_name,
    h.sex,
    h.birth_year,

    -- 4. Dynamic Features (Day of Race)
    rp.pmu_number,          -- Cloth number
    rp.age,
    rp.career_winnings,
    rp.career_races_count,
    rp.trainer_advice,      -- Emojis or text confidence
    
    -- JOINED COLUMNS (Fixing the previous error)
    ls.code AS shoeing_status,      -- From lookup_shoeing
    j.actor_name AS jockey_name,    -- From racing_actor
    t.actor_name AS trainer_name,   -- From racing_actor

    -- 5. Odds & Targets
    rp.reference_odds,
    rp.live_odds,
    rp.finish_rank,
    
    -- Binary Target (Winner)
    CASE 
        WHEN rp.finish_rank = 1 THEN 1 
        ELSE 0 
    END AS is_winner

FROM race_participant rp
JOIN race r ON rp.race_id = r.race_id
JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
JOIN daily_program prog ON rm.program_id = prog.program_id
JOIN horse h ON rp.horse_id = h.horse_id

-- FIX: Join the Lookup tables to get text values
LEFT JOIN lookup_shoeing ls ON rp.shoeing_id = ls.shoeing_id
LEFT JOIN racing_actor j ON rp.driver_jockey_id = j.actor_id
LEFT JOIN racing_actor t ON rp.trainer_id = t.actor_id

WHERE rp.finish_rank IS NOT NULL 
"""

# QUERY 2: History Data
QUERY_HISTORY = """
SELECT 
    horse_id, 
    race_date, 
    discipline, 
    distance_m, 
    finish_place, 
    reduction_km, 
    prize_money,
    distance_traveled_m
FROM horse_race_history
"""

# 3. EXPORT FUNCTION

def export_data():
    print(" Connecting to Supabase...")
    try:
        connection = engine.connect()
        print(" Connection successful.")
    except Exception as e:
        print(f" Connection failed: {e}")
        return

    # --- Export Main Dataset ---
    print(" Downloading Main Dataset (Participants)...")
    try:
        df_main = pd.read_sql(QUERY_MAIN, connection)
        
        # Ensure dates are dates
        df_main['program_date'] = pd.to_datetime(df_main['program_date'])
        
        csv_main = "data/data_training_participants.csv"
        df_main.to_csv(csv_main, index=False)
        print(f" Success! {len(df_main)} rows exported to {csv_main}")
    except Exception as e:
        print(f" Error in Main Query: {e}")

    # --- Export History Dataset ---
    print(" Downloading History Dataset (Past Performances)...")
    try:
        df_hist = pd.read_sql(QUERY_HISTORY, connection)
        
        # Ensure dates are dates
        df_hist['race_date'] = pd.to_datetime(df_hist['race_date'])
        
        csv_hist = "data/data_training_history.csv"
        df_hist.to_csv(csv_hist, index=False)
        print(f" Success! {len(df_hist)} rows exported to {csv_hist}")
    except Exception as e:
        print(f" Error in History Query: {e}")
        # Common fix advice if this fails
        if "column" in str(e) and "does not exist" in str(e):
            print(" Hint: The DB schema might be older than the query. Update the table or remove the missing column.")

    connection.close()

if __name__ == "__main__":
    export_data()