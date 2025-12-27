"""
Inference module for loading the calibrated XGBoost model and generating predictions.
Handles feature synchronization using training artifacts.
"""
import pickle
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

class RacePredictor:
    """
    Wrapper around the CalibratedClassifierCV (XGBoost + Isotonic) 
    that handles feature alignment and categorical synchronization.
    """

    def __init__(self, model_path: str) -> None:
        """
        Initializes the predictor, loads the calibrator and the artifacts.

        Args:
            model_path (str): Path to 'probability_calibrator.pkl'. 
                              It assumes 'model_artifacts.pkl' is in the same directory.
        """
        self.logger = logging.getLogger("ML.Predictor")
        self.model_path = Path(model_path)
        self.artifacts_path = self.model_path.parent / "model_artifacts.pkl"
        
        self.calibrator = None
        self.artifacts = None
        
        self._load_system()

    def _load_system(self) -> None:
        """Internal method to load both the Pickle model and the Artifacts dictionary."""
        try:
            # 1. Load Calibrator
            if not self.model_path.exists():
                self.logger.error(f"Model file missing: {self.model_path}")
                return

            with open(self.model_path, "rb") as f:
                self.calibrator = pickle.load(f)
            
            # 2. Load Artifacts
            if not self.artifacts_path.exists():
                self.logger.error(f"Artifacts file missing: {self.artifacts_path}")
                return

            with open(self.artifacts_path, "rb") as f:
                self.artifacts = pickle.load(f)
                
            self.logger.info(f"ML System loaded successfully (Features: {len(self.artifacts['features'])})")

        except Exception as exc:
            self.logger.error(f"Critical Error loading ML system: {exc}")
            self.calibrator = None
            self.artifacts = None

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aligns the input DataFrame with the training requirements.
        - Fills missing columns with NaN.
        - Orders columns correctly.
        - Synchronizes Categorical types (handling unseen values).
        """
        features = self.artifacts['features']
        known_cats = self.artifacts['categories']
        
        # 1. Ensure all required columns exist
        missing = [f for f in features if f not in df.columns]
        if missing:
            # Create missing columns with NaN to prevent crash
            for col in missing:
                df[col] = np.nan
        
        # 2. Reorder columns to match training exactly
        X = df[features].copy()
        
        # 3. Synchronize Categories (The Anti-Crash Logic)
        for col, categories in known_cats.items():
            if col in X.columns:
                # Force column to category dtype
                X[col] = X[col].astype('category')
                # Force strict categories (Unseen values -> NaN)
                X[col] = X[col].cat.set_categories(categories)
        
        return X

    def predict_race(self, participants: List[Dict[str, Any]]) -> List[float]:
        """
        Predicts winning probabilities for a list of participants.

        Args:
            participants: List of dicts (raw data from DB).

        Returns:
            List of probabilities (0.0 to 1.0).
        """
        # Safety Checks
        if not self.calibrator or not self.artifacts:
            self.logger.warning("Prediction attempted with unloaded model.")
            return [0.0] * len(participants)
            
        if not participants:
            return []

        try:
            # 1. Convert to DataFrame
            input_df = pd.DataFrame(participants)
            
            # 2. Preprocess (Sync categories & columns)
            processed_df = self._prepare_features(input_df)
            
            # 3. Predict (Index 1 is the probability of Class 1 aka 'Winner')
            # CalibratedClassifierCV returns [Prob_Loss, Prob_Win]
            win_probabilities = self.calibrator.predict_proba(processed_df)[:, 1]
            
            return win_probabilities.tolist()

        except Exception as exc:
            self.logger.error(f"Prediction Runtime Error: {exc}")
            # Fallback to 0.0 on error to keep API alive
            return [0.0] * len(participants)

    @property
    def pipeline(self):
        """Property to maintain compatibility with legacy checks in main.py"""
        return self.calibrator