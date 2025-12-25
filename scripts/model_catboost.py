import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
import matplotlib.pyplot as plt
import os
import sys

def load_and_split_data(file_path, test_days=60):
    """
    Loads the dataset, handles basic type conversions, sorts chronologically, 
    and splits into train/test based on the cutoff date.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)

    print(f"Loading data from {file_path}...")
    df = pd.read_csv(file_path)
    
    # ensure datetime
    if 'program_date' in df.columns:
        df['program_date'] = pd.to_datetime(df['program_date'])
        df = df.sort_values('program_date')
    else:
        print("Error: 'program_date' column missing. Cannot perform time-series split.")
        sys.exit(1)

    # --- FINAL PRE-PROCESSING FOR CATBOOST ---
    # CatBoost requires strings for categorical features, not NaNs.
    # We apply this transformation before splitting to ensure consistency.
    
    # 1. Fill Categorical NaNs
    cat_cols_to_fix = ['racetrack_code', 'discipline', 'track_type', 'sex', 
                       'jockey_name', 'trainer_name', 'shoeing_status']
    
    for col in cat_cols_to_fix:
        if col in df.columns:
            df[col] = df[col].fillna("UNKNOWN").astype(str)
            
    # 2. Fill Numerical NaNs (Safety net, though your previous script likely handled this)
    if 'is_debutant' not in df.columns and 'career_winnings' in df.columns:
         df['is_debutant'] = df['career_winnings'].isnull().astype(int)
         
    df['career_winnings'] = df['career_winnings'].fillna(0)
    df['career_races_count'] = df['career_races_count'].fillna(0)
    
    # 3. Recalculate Logic (just in case)
    if 'winnings_per_race' not in df.columns:
        df['winnings_per_race'] = df['career_winnings'] / (df['career_races_count'] + 1)
        
    # 4. Market Data Cleanup
    if 'reference_odds' in df.columns:
        df['is_odds_missing'] = df['reference_odds'].isnull().astype(int)
        df['reference_odds'] = df['reference_odds'].fillna(10.0) # Neutral fallback

    # --- SPLIT ---
    cutoff_date = df['program_date'].max() - pd.Timedelta(days=test_days)
    
    train_df = df[df['program_date'] <= cutoff_date].copy()
    test_df = df[df['program_date'] > cutoff_date].copy()

    print(f"Training Range: {train_df['program_date'].min().date()} to {train_df['program_date'].max().date()}")
    print(f"Testing Range:  {test_df['program_date'].min().date()} to {test_df['program_date'].max().date()}")
    
    return train_df, test_df

def define_features(df):
    """
    Selects numerical and categorical features.
    """
    # 1. Numerical Features
    num_candidates = [
        'horse_age_at_race', 'distance_m', 'declared_runners_count', 
        'career_winnings', 'career_races_count', 'winnings_per_race',
        'relative_winnings', 'winnings_rank_in_race', 
        'reference_odds', 'odds_rank_in_race', 'is_debutant', 
        'race_month', 'race_day_of_week', 'is_odds_missing'
    ]
    
    # 2. Categorical Features (Raw Strings)
    cat_candidates = [
        'racetrack_code', 'discipline', 'track_type', 'sex', 
        'shoeing_status', 'jockey_name', 'trainer_name'
    ]
    
    # Filter based on what actually exists in the dataframe
    num_features = [f for f in num_candidates if f in df.columns]
    cat_features = [f for f in cat_candidates if f in df.columns]
    
    final_features = num_features + cat_features
    
    print(f"\nSelected {len(final_features)} features.")
    print(f"Numerical: {len(num_features)} | Categorical: {len(cat_features)}")
    
    return final_features, cat_features

def train_catboost(X_train, y_train, X_test, y_test, cat_features):
    """
    Trains the CatBoost Classifier.
    """
    # Get indices of categorical columns for CatBoost
    cat_features_indices = [X_train.columns.get_loc(c) for c in cat_features]
    
    print(f"\nCategorical Indices: {cat_features_indices}")
    print("Initializing CatBoost Training...")

    # Initialize Pool
    train_pool = Pool(X_train, y_train, cat_features=cat_features_indices)
    test_pool = Pool(X_test, y_test, cat_features=cat_features_indices)

    # Initialize Model
    model = CatBoostClassifier(
        iterations=1500,             # High iteration count with early stopping
        learning_rate=0.03,          # Slow & steady
        depth=6,                     # Standard depth
        loss_function='Logloss',
        eval_metric='AUC',           # Good for ranking
        scale_pos_weight=8,          # Handle class imbalance (winners are rare)
        random_seed=42,
        use_best_model=True,
        verbose=100,                  # Log every 100 trees
        allow_writing_files=False  # This prevents folder creation
        # task_type="GPU"            # UNCOMMENT if you have a GPU
    )

    # Fit
    model.fit(train_pool, eval_set=test_pool, early_stopping_rounds=50)
    print("Training complete.")
    
    return model

def evaluate_performance(model, test_df, features):
    """
    Calculates Hit Rate, ROI, and plots Feature Importance.
    """
    print("\nEvaluating Model Performance...")
    
    X_test = test_df[features]
    
    # 1. Predictions
    # Copy to avoid SettingWithCopy warning
    eval_df = test_df.copy()
    eval_df['proba'] = model.predict_proba(X_test)[:, 1]
    
    # Rank within race
    eval_df['model_rank'] = eval_df.groupby('race_id')['proba'].rank(ascending=False, method='min')
    
    # 2. Top 3 Hit Rate
    winners = eval_df[eval_df['is_winner'] == 1]
    top3_hits = (winners['model_rank'] <= 3).sum()
    total_races = winners['race_id'].nunique()
    
    if total_races > 0:
        print(f"-" * 30)
        print(f"Top 3 Hit Rate: {top3_hits / total_races:.2%}")
    else:
        print("Warning: No races found for evaluation.")

    # 3. ROI Simulation (Rank #1 Strategy)
    bets = eval_df[eval_df['model_rank'] == 1].copy()
    if not bets.empty:
        bets['payout'] = np.where(bets['is_winner'] == 1, bets['reference_odds'], 0)
        net_profit = bets['payout'].sum() - len(bets)
        roi = (net_profit / len(bets)) * 100
        
        print(f"Rank #1 ROI:    {roi:.2f}%")
        print(f"Total Bets:     {len(bets)}")
        print(f"-" * 30)
    
    # 4. Feature Importance Plot
    feature_importance = model.get_feature_importance()
    sorted_idx = np.argsort(feature_importance)
    
    plt.figure(figsize=(10, 8))
    plt.barh(range(len(sorted_idx)), feature_importance[sorted_idx], align='center', color='steelblue')
    plt.yticks(range(len(sorted_idx)), np.array(features)[sorted_idx])
    plt.title('CatBoost Feature Importance')
    plt.xlabel('Importance Score')
    plt.grid(True, axis='x', alpha=0.3)
    plt.tight_layout()
    plt.show()

def main():
    # Configuration
    DATA_PATH = './data/data_training_participants.csv'
    
    # 1. Load & Split
    train_df, test_df = load_and_split_data(DATA_PATH)
    
    # 2. Define Features
    features, cat_features = define_features(train_df)
    
    if not features:
        print("Error: No features selected.")
        sys.exit(1)

    # 3. Prepare Data
    X_train = train_df[features]
    y_train = train_df['is_winner']
    
    X_test = test_df[features]
    y_test = test_df['is_winner']
    
    # 4. Train
    model = train_catboost(X_train, y_train, X_test, y_test, cat_features)
    
    # 5. Evaluate
    evaluate_performance(model, test_df, features)

if __name__ == "__main__":
    main()