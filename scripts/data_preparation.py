import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

# 1. LOAD THE DATA
print(" Loading CSV files...")
df_main = pd.read_csv("./data/data_training_participants.csv")
df_hist = pd.read_csv("./data/data_training_history.csv")

# Convert dates to datetime objects (Crucial for sorting)
df_main['program_date'] = pd.to_datetime(df_main['program_date'])
df_hist['race_date'] = pd.to_datetime(df_hist['race_date'])

# 2. FEATURE ENGINEERING
# We need to calculate stats from history for every horse.

print(" Engineering features from history (this might take a moment)...")

# For this example, we calculate global career stats for simplicity.

horse_stats = df_hist.groupby('horse_id').agg({
    'finish_place': ['count', 'mean'],      # Total races, Avg Rank
    'reduction_km': ['mean', 'min'],        # Avg speed, Best speed (lower is better)
    'prize_money': 'sum'                    # Total earnings
}).reset_index()

# Flatten the column names (pandas makes them hierarchical by default)
horse_stats.columns = ['horse_id', 'career_races', 'avg_rank', 'avg_speed', 'best_speed', 'hist_earnings']

# Handle missing speeds (e.g. fill with a default value or average)
horse_stats['avg_speed'] = horse_stats['avg_speed'].fillna(1.20) # Default slow speed if unknown

print(" Merging datasets...")

# Join the calculated stats onto the main list of participants
df_final = pd.merge(df_main, horse_stats, on='horse_id', how='left')

# Fill horses with no history with zeros
df_final['career_races'] = df_final['career_races'].fillna(0)
df_final['hist_earnings'] = df_final['hist_earnings'].fillna(0)

# 4. ENCODING (Text -> Numbers)

print(" Encoding categorical text...")

# List of columns that are text
cat_cols = ['racetrack_code', 'discipline', 'track_type', 'terrain_label', 'sex', 'shoeing_status']

# We use LabelEncoder (A -> 1, B -> 2...)
# For better results later, we might consider "Target Encoding" or "One-Hot Encoding"
le = LabelEncoder()

for col in cat_cols:
    # Convert column to string type just in case of mixed types
    df_final[col] = df_final[col].astype(str)
    # Create a new column with suffix _encoded
    df_final[f"{col}_encoded"] = le.fit_transform(df_final[col])

# 5. FINAL CLEANUP & EXPORT

# Select only numeric columns for the final training file
# We keep 'program_date' to split Train/Test data later
features = [
    'program_date', 'race_id', 'horse_id', 'finish_rank', 'is_winner', # Metadata & Targets
    'distance_m', 'declared_runners_count', 'age', 'career_winnings',  # Raw features
    'career_races', 'avg_rank', 'avg_speed', 'hist_earnings',          # Engineered features
    'racetrack_code_encoded', 'discipline_encoded', 'shoeing_status_encoded' # Encoded features
]

df_ready = df_final[features].copy()

# Drop rows where target (finish_rank) might be missing or broken
df_ready = df_ready.dropna(subset=['finish_rank'])

output_file = "dataset_ready_for_ml.csv"
df_ready.to_csv(output_file, index=False)

print(f" Success! Generated '{output_file}' with {len(df_ready)} rows.")
