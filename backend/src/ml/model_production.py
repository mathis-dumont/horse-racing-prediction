import xgboost as xgb
import pandas as pd
import numpy as np
import os
import sys
import pickle
from sklearn.calibration import CalibratedClassifierCV


current_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.abspath(os.path.join(current_dir, '../../..'))

data_path = os.path.join(project_root, 'dataset', 'final_pmu_ml_dataset_v1.csv')

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG = {
    'data_path': data_path,
    'test_days': 60,
    'val_days': 30,
    'target': 'is_winner',
    'id_col': 'race_id',
    'date_col': 'program_date',
    'model_params': {
        'n_estimators': 2500,       # Increased slightly
        'max_depth': 5,             # Reduced to 5 to prevent overfitting
        'learning_rate': 0.015,     # Slower learning = better probability estimation
        'subsample': 0.7,
        'colsample_bytree': 0.7,
        'tree_method': 'hist',
        'random_state': 42,
        'enable_categorical': True,
        'eval_metric': 'logloss',   # CHANGED: Better for Value Betting than AUC
        'early_stopping_rounds': 75
    },
    'min_edge': 0.05,
    'min_odds': 5.0,
    'max_odds': 20.0,
    'model_file': 'trot_sniper_model.json',
    'calibrator_file': 'probability_calibrator.pkl', # NEW: Saves the correction logic
    'artifacts_file': 'model_artifacts.pkl'
}

# ==========================================
# 1. DATA LOADING
# ==========================================
def load_and_split_data(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    df = pd.read_csv(file_path)
    df[CONFIG['date_col']] = pd.to_datetime(df[CONFIG['date_col']])
    df = df.sort_values(CONFIG['date_col'])

    max_date = df[CONFIG['date_col']].max()
    test_cutoff = max_date - pd.Timedelta(days=CONFIG['test_days'])
    val_cutoff = test_cutoff - pd.Timedelta(days=CONFIG['val_days'])

    train_df = df[df[CONFIG['date_col']] <= val_cutoff].copy()
    val_df   = df[(df[CONFIG['date_col']] > val_cutoff) & (df[CONFIG['date_col']] <= test_cutoff)].copy()
    test_df  = df[df[CONFIG['date_col']] > test_cutoff].copy()
    
    return train_df, val_df, test_df

def select_features(df):
    # Same raw features as before to match Scraper
    features = [
        'horse_age', 'distance_m', 'declared_runners_count', 
        'career_winnings', 'relative_winnings', 
        'winnings_rank_in_race', 'odds_rank_in_race', 'reference_odds',
        'race_month', 'race_day_of_week',
        'shoeing_status', 'jockey_name', 'trainer_name', 'sex', 'discipline', 'breed',
        'is_debutant', 'is_clinker'
    ]
    selected_feats = [f for f in features if f in df.columns]
    return selected_feats

def synchronize_categories(train_df, val_df, test_df, features):
    print("Synchronizing categories...")
    for col in features:
        if train_df[col].dtype == 'object' or train_df[col].dtype.name == 'category':
            train_df[col] = train_df[col].astype('category')
            known_cats = train_df[col].cat.categories
            for df_split in [val_df, test_df]:
                df_split[col] = df_split[col].astype('category')
                df_split[col] = df_split[col].cat.set_categories(known_cats)
    return train_df, val_df, test_df

# ==========================================
# 2. ADVANCED TRAINING
# ==========================================
def train_model(train_df, val_df, features):
    X_train = train_df[features]
    y_train = train_df[CONFIG['target']]
    X_val = val_df[features]
    y_val = val_df[CONFIG['target']]

    # 1. Monotonic Constraints (The "Logic" Layer)
    # We force the model: Lower odds_rank (1) must imply higher probability than Rank 10
    monotone_constraints = {}
    if 'odds_rank_in_race' in features:
        monotone_constraints['odds_rank_in_race'] = -1  # Negative relationship
    
    # 2. Weights
    neg = len(y_train) - sum(y_train)
    pos = sum(y_train)
    scale_weight = neg / pos if pos > 0 else 1.0

    params = CONFIG['model_params'].copy()
    params['scale_pos_weight'] = scale_weight
    if monotone_constraints:
        params['monotone_constraints'] = monotone_constraints

    print("\n1. Training Base XGBoost (Logic Constrained)...")
    base_model = xgb.XGBClassifier(**params)
    base_model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=100
    )

    # 3. Probability Calibration (The "Accuracy" Layer)
    # Uses the Validation set to map "Raw Scores" to "Real Probabilities"
    print("2. Calibrating Probabilities (Isotonic Regression)...")
    calibrator = CalibratedClassifierCV(base_model, method='isotonic', cv='prefit')
    calibrator.fit(X_val, y_val)
    
    return base_model, calibrator

# ==========================================
# 3. EVALUATION
# ==========================================
def evaluate_model(calibrator, test_df, features):
    print("\n" + "="*40)
    print("EVALUATION (Calibrated)")
    print("="*40)
    
    X_test = test_df[features]
    test_df = test_df.copy()
    
    # IMPORTANT: Predict using the CALIBRATOR, not the raw model
    test_df['proba'] = calibrator.predict_proba(X_test)[:, 1]
    test_df['model_rank'] = test_df.groupby(CONFIG['id_col'])['proba'].rank(ascending=False, method='min')

    # Sniper Strategy Check
    if 'reference_odds' in test_df.columns:
        test_df['implied_prob'] = 1 / test_df['reference_odds']
        test_df['edge'] = test_df['proba'] - test_df['implied_prob']
        
        bets = test_df[
            (test_df['model_rank'] == 1) & 
            (test_df['edge'] > CONFIG['min_edge']) & 
            (test_df['reference_odds'] >= CONFIG['min_odds']) & 
            (test_df['reference_odds'] < CONFIG['max_odds'])
        ].copy()
        
        bets['profit'] = np.where(bets[CONFIG['target']] == 1, bets['reference_odds'] - 1, -1)
        
        print(f"Sniper Strategy Bets: {len(bets)}")
        print(f"ROI: {bets['profit'].sum() / len(bets):.2%}" if len(bets)>0 else "ROI: 0%")
        
        # Reliability Check (Are 80% confident bets winning 80% of the time?)
        print("\n--- Reliability Check ---")
        bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        test_df['bin'] = pd.cut(test_df['proba'], bins=bins)
        reliability = test_df.groupby('bin', observed=False).agg(
            Predicted=('proba', 'mean'),
            Actual=('is_winner', 'mean'),
            Count=('race_id', 'count')
        )
        print(reliability[reliability['Count'] > 0])

    return test_df

# ==========================================
# 4. SAVING
# ==========================================
def save_artifacts(base_model, calibrator, train_df, features):
    print(f"\nSaving base model to {CONFIG['model_file']}...")
    base_model.save_model(CONFIG['model_file'])
    
    print(f"Saving calibrator to {CONFIG['calibrator_file']}...")
    with open(CONFIG['calibrator_file'], "wb") as f:
        pickle.dump(calibrator, f)
        
    print("Saving artifacts...")
    category_map = {}
    for col in features:
        if train_df[col].dtype.name == 'category':
            category_map[col] = train_df[col].cat.categories
            
    artifacts = {
        'features': features,
        'categories': category_map,
        'config': CONFIG
    }
    
    with open(CONFIG['artifacts_file'], "wb") as f:
        pickle.dump(artifacts, f)
    print("Done. System upgraded.")

def main():
    train_df, val_df, test_df = load_and_split_data(CONFIG['data_path'])
    features = select_features(train_df)
    train_df, val_df, test_df = synchronize_categories(train_df, val_df, test_df, features)
    
    # Updated Training returns TWO objects
    base_model, calibrator = train_model(train_df, val_df, features)
    
    evaluate_model(calibrator, test_df, features)
    
    # Save both
    save_artifacts(base_model, calibrator, train_df, features)

if __name__ == "__main__":
    main()