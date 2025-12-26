import xgboost as xgb
import pandas as pd
import numpy as np
import os
import sys

def load_and_split_data(file_path, test_days=60):
    """
    Loads the dataset, sorts chronologically, and splits into train/test 
    based on the cutoff date.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)

    print(f"Loading data from {file_path}...")
    # Fix: read_csv does not accept index=False
    df = pd.read_csv(file_path)
    
    # Ensure chronological order
    if 'program_date' in df.columns:
        df['program_date'] = pd.to_datetime(df['program_date'])
        df = df.sort_values('program_date')
    else:
        print("Error: 'program_date' column missing. Cannot perform time-series split.")
        sys.exit(1)

    # Define cutoff date
    cutoff_date = df['program_date'].max() - pd.Timedelta(days=test_days)
    
    # Create sets
    train_df = df[df['program_date'] <= cutoff_date].copy()
    test_df = df[df['program_date'] > cutoff_date].copy()

    print(f"Training Range: {train_df['program_date'].min().date()} to {train_df['program_date'].max().date()}")
    print(f"Testing Range:  {test_df['program_date'].min().date()} to {test_df['program_date'].max().date()}")
    
    return train_df, test_df

def select_features(df):
    """
    Defensively selects features based on available columns in the dataframe.
    """
    # Defensive Column Mapping
    # Maps the 'Idea' of a feature to potential column names
    feature_map = {
        'age': ['horse_age_at_race', 'horse_age'],
        'dist': ['distance_m'],
        'runners': ['declared_runners_count'],
        'winnings': ['career_winnings', 'relative_winnings', 'winnings_per_race'],
        'ranks': ['winnings_rank_in_race', 'earnings_rank', 'odds_rank_in_race', 'odds_rank'],
        'market': ['reference_odds'], # Uncommented based on usage logic
        'is_debut': ['is_debutant'],
        'time': ['race_month', 'race_day_of_week'],
        # Dynamically grab all encoded categorical columns
        'cat_encoded': [col for col in df.columns if '_encoded' in col or col.endswith('_n')]
    }

    final_features = []
    
    # Flatten the map and verify existence
    for category, options in feature_map.items():
        if isinstance(options, list):
            # Check which options actually exist in the df
            existing = [opt for opt in options if opt in df.columns]
            final_features.extend(existing)
        else:
            if options in df.columns:
                final_features.append(options)

    # Remove duplicates while preserving order
    final_features = list(dict.fromkeys(final_features))
    
    print(f"\nSelected {len(final_features)} features for training:")
    print(final_features)
    
    return final_features

def train_model(X_train, y_train):
    """
    Configures and trains the XGBoost Classifier.
    """
    print("\nTraining XGBoost model...")
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=10,  # Crucial for imbalanced racing data
        tree_method='hist',   # Faster training
        random_state=42,
        enable_categorical=True # Helpful if native categories are passed, harmless otherwise
    )
    
    model.fit(X_train, y_train)
    print("Training complete.")
    return model

def evaluate_model(model, test_df, features):
    """
    Predicts on test set and calculates Top-3 Hit Rate.
    """
    print("\nEvaluating model...")
    X_test = test_df[features]
    
    # Predict probabilities (index 1 is the positive class 'Winner')
    # We copy test_df to avoid SettingWithCopy warnings
    eval_df = test_df.copy()
    eval_df['proba'] = model.predict_proba(X_test)[:, 1]

    # Rank horses by probability within each race
    # method='min' means if there's a tie, they get the same rank (e.g. 1, 2, 2, 4)
    eval_df['model_rank'] = eval_df.groupby('race_id')['proba'].rank(ascending=False, method='min')

    # Calculate Hit Rate
    winners = eval_df[eval_df['is_winner'] == 1]
    top3_hits = (winners['model_rank'] <= 3).sum()
    total_races = winners['race_id'].nunique()
    
    if total_races == 0:
        print("Warning: No races found in test set (or no winners flagged).")
        return

    hit_rate = top3_hits / total_races

    print(f"-" * 30)
    print(f"EVALUATION RESULTS")
    print(f"-" * 30)
    print(f"Total Races in Test Set: {total_races}")
    print(f"Top 3 Hit Rate:          {hit_rate:.2%}")
    print(f"-" * 30)

def main():
    # Configuration
    DATA_PATH = './data/final_ml_dataset.csv'
    
    # 1. Load Data
    train_df, test_df = load_and_split_data(DATA_PATH)
    
    # 2. Select Features
    # We select features based on the training set to ensure consistency
    features = select_features(train_df)
    
    if not features:
        print("Error: No valid features found based on the feature map.")
        sys.exit(1)

    # 3. Prepare Matrices
    X_train = train_df[features]
    y_train = train_df['is_winner']
    
    # 4. Train
    model = train_model(X_train, y_train)
    
    # 5. Evaluate
    evaluate_model(model, test_df, features)

if __name__ == "__main__":
    main()