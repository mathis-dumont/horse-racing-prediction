import joblib
import logging
import sys
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import log_loss, roc_auc_score

# Ensure python finds the source modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.ml.loader import DataLoader
from src.ml.features import PmuFeatureEngineer

# Set up logging to stdout for Docker
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class XGBoostTrainer:
    def __init__(self, model_path: str = "data/model_calibrated.pkl") -> None:
        self.logger = logging.getLogger("ML.Trainer")
        self.model_path = model_path
        self.loader = DataLoader()
        
        self.categorical_features = [
            'racetrack_code', 'discipline', 'track_type', 'sex', 
            'shoeing_status', 'jockey_name', 'trainer_name', 'terrain_label'
        ]
        
        self.numerical_features = [
            'horse_age_at_race', 'distance_m', 'declared_runners_count', 
            'career_winnings', 'relative_winnings', 'winnings_per_race', 
            'winnings_rank_in_race', 'odds_rank_in_race', 'reference_odds', 
            'is_debutant', 'race_month', 'hist_avg_speed', 'hist_earnings'
        ]

    def train(self, test_days: int = 60, val_days: int = 30) -> None:
        self.logger.info("--- STARTING TRAINING PIPELINE ---")
        
        # 1. Loading
        try:
            # We assume get_training_data returns a DataFrame with 'is_winner' and 'program_date'
            raw_df = self.loader.get_training_data()
            self.logger.info(f"Data Loaded: {raw_df.shape} rows")
        except Exception as e:
            self.logger.error(f"CRITICAL: Database connection failed. {e}")
            return

        if raw_df.empty:
            self.logger.error("No data returned by the loader.")
            return

        # 2. Feature Engineering (Fit once to get global stats if needed)
        self.logger.info("Engineering features...")
        engineer = PmuFeatureEngineer()
        # We process the whole DF first to handle lag features correctly before splitting
        full_df = engineer.fit_transform(raw_df)
        
        # 3. Temporal Split
        max_date = full_df['program_date'].max()
        test_cutoff = max_date - pd.Timedelta(days=test_days)
        val_cutoff = test_cutoff - pd.Timedelta(days=val_days)

        train_df = full_df[full_df['program_date'] <= val_cutoff]
        val_df = full_df[(full_df['program_date'] > val_cutoff) & (full_df['program_date'] <= test_cutoff)]
        test_df = full_df[full_df['program_date'] > test_cutoff]

        self.logger.info(f"Split -> Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

        # Select Features
        features = self.numerical_features + self.categorical_features
        X_train, y_train = train_df[features], train_df['is_winner']
        X_val, y_val = val_df[features], val_df['is_winner']
        X_test, y_test = test_df[features], test_df['is_winner']

        # 4. Preprocessing
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), self.categorical_features),
                ('num', 'passthrough', self.numerical_features)
            ]
        )

        self.logger.info("Encoding Data...")
        X_train_enc = preprocessor.fit_transform(X_train, y_train)
        X_val_enc = preprocessor.transform(X_val)
        X_test_enc = preprocessor.transform(X_test)

        # 5. Base XGBoost
        self.logger.info("Training Base XGBoost...")
        base_xgb = XGBClassifier(
            n_estimators=1000, # Reduced slightly for speed, increase for prod
            max_depth=6,
            learning_rate=0.02,
            subsample=0.8,
            colsample_bytree=0.8,
            # 'hist' is faster and often more accurate for larger datasets
            tree_method='hist',
            early_stopping_rounds=50,
            random_state=42,
            n_jobs=-1,
            eval_metric='logloss'
        )

        base_xgb.fit(
            X_train_enc, y_train,
            eval_set=[(X_val_enc, y_val)],
            verbose=100
        )

        # 6. Calibration
        self.logger.info("Calibrating (Isotonic)...")
        calibrated_model = CalibratedClassifierCV(
            estimator=base_xgb,
            method='isotonic',
            cv='prefit'
        )
        calibrated_model.fit(X_val_enc, y_val)

        # 7. Evaluation
        self.logger.info("Evaluating on Test Set...")
        probs = calibrated_model.predict_proba(X_test_enc)[:, 1]
        loss = log_loss(y_test, probs)
        try:
            auc = roc_auc_score(y_test, probs)
        except ValueError:
            auc = 0.5
        
        self.logger.info(f"FINAL METRICS -> LogLoss: {loss:.4f} | AUC: {auc:.4f}")

        # 8. Save Pipeline
        # Note: We pass 'engineer' as a step. It must implement fit/transform.
        full_inference_pipeline = Pipeline([
            ('engineer', engineer),
            ('preprocessor', preprocessor),
            ('model', calibrated_model)
        ])

        # Ensure directory exists
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(full_inference_pipeline, self.model_path)
        self.logger.info(f"SUCCESS: Model saved to {self.model_path}")

if __name__ == "__main__":
    trainer = XGBoostTrainer()
    trainer.train()