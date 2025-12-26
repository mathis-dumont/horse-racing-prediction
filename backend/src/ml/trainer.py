"""
Training module for the XGBoost model.
Handles feature selection, pipeline construction, training, and serialization.
"""
import joblib
import logging
import pandas as pd
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.metrics import roc_auc_score

from src.ml.loader import DataLoader
from src.ml.features import PmuFeatureEngineer

class XGBoostTrainer:
    """
    Manages the end-to-end training process for the race prediction model.
    """

    def __init__(self, model_path: str = "data/model_xgboost.pkl") -> None:
        """
        Initialize the trainer.

        Args:
            model_path (str): Destination path for the saved model.
        """
        self.logger = logging.getLogger("ML.Trainer")
        self.model_path = model_path
        self.loader = DataLoader()
        
        # 1. Define Feature Sets
        self.categorical_features = [
            'racetrack_code', 'discipline', 'track_type', 'sex', 
            'shoeing_status', 'jockey_name', 'trainer_name'
        ]
        
        self.numerical_features = [
            'horse_age_at_race', 'distance_m', 'declared_runners_count', 
            'career_winnings', 'relative_winnings', 'winnings_per_race', 
            'winnings_rank_in_race', 'odds_rank_in_race', 'reference_odds', 
            'is_debutant', 'race_month', 'race_day_of_week'
        ]

    def train(self) -> None:
        """
        Executes the training workflow:
        1. Load data
        2. Feature Engineering
        3. Train/Test Split
        4. Pipeline construction
        5. Fitting & Evaluation
        6. Serialization
        """
        # 1. Load & Global Engineering
        input_dataframe = self.loader.get_training_data()
        if input_dataframe.empty:
            self.logger.error("No training data available. Aborting.")
            return

        input_dataframe = input_dataframe.sort_values('program_date')
        
        # Apply engineering BEFORE split for rank/ratio calculations
        # (Acceptable as ranks are intra-race and do not leak future data)
        engineer = PmuFeatureEngineer()
        engineered_dataframe = engineer.transform(input_dataframe)

        # 2. Prepare X (Features) and y (Target)
        valid_numeric = [c for c in self.numerical_features if c in engineered_dataframe.columns]
        valid_categorical = [c for c in self.categorical_features if c in engineered_dataframe.columns]
        
        features_list = valid_numeric + valid_categorical
        X = engineered_dataframe[features_list]
        y = engineered_dataframe['is_winner']

        # 3. Time-based Split (80/20 rule)
        cutoff_index = int(len(input_dataframe) * 0.8)
        X_train, X_test = X.iloc[:cutoff_index], X.iloc[cutoff_index:]
        y_train, y_test = y.iloc[:cutoff_index], y.iloc[cutoff_index:]

        self.logger.info(f"Train Set: {len(X_train)} samples | Test Set: {len(X_test)} samples")

        # 4. Construct Transformation Pipeline
        # OrdinalEncoder transforms strings to integers
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), valid_categorical),
                ('num', 'passthrough', valid_numeric)
            ]
        )

        # 5. Define Model (Hyperparameters preserved)
        model = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            scale_pos_weight=10,  # Handle class imbalance
            tree_method='hist',   # Optimized for speed
            random_state=42,
            n_jobs=-1
        )

        # 6. Assemble Training Pipeline
        training_pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('model', model)
        ])

        # 7. Train
        self.logger.info("Starting XGBoost training...")
        training_pipeline.fit(X_train, y_train)

        # 8. Evaluate
        probabilities = training_pipeline.predict_proba(X_test)[:, 1]
        auc_score = roc_auc_score(y_test, probabilities)
        self.logger.info(f"XGBoost ROC AUC Score: {auc_score:.4f}")

        # 9. Save Full Inference Pipeline
        # We wrap the training pipeline with the feature engineer so the API
        # only needs to input raw data.
        full_inference_pipeline = Pipeline([
            ('engineer', PmuFeatureEngineer()), # Generates features (ratios, ranks)
            ('training_pipeline', training_pipeline)     # Encodes and Predicts
        ])

        joblib.dump(full_inference_pipeline, self.model_path)
        self.logger.info(f"Model successfully saved to: {self.model_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    trainer = XGBoostTrainer()
    trainer.train()