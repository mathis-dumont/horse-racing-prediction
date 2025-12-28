import joblib
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union

class RacePredictor:
    """
    Simplified inference module.
    Loads the complete Pipeline (Feature Engineering -> Preprocessing -> Calibration).
    """

    def __init__(self, model_path: str = "data/model_calibrated.pkl") -> None:
        """
        Initializes the predictor by loading the serialized pipeline.
        """
        self.logger = logging.getLogger("ML.Predictor")
        self.model_path = model_path
        self.pipeline = None
        
        self._load_model()

    def _load_model(self) -> None:
        """Loads the single file containing the entire pipeline."""
        try:
            self.logger.info(f"Loading model from {self.model_path}...")
            self.pipeline = joblib.load(self.model_path)
            self.logger.info("Model loaded successfully.")
        except FileNotFoundError:
            self.logger.error(f"Model file not found: {self.model_path}")
        except Exception as exc:
            self.logger.error(f"Critical error loading model: {exc}")

    def predict_race(self, participants: List[Dict[str, Any]]) -> List[float]:
        """
        Predicts win probabilities for a list of raw participants (from API/DB).

        Args:
            participants: List of dictionaries containing raw data 
                          (e.g., {'program_date': '2023...', 'career_winnings': 5000, ...})

        Returns:
            List[float]: Calibrated probabilities (between 0.0 and 1.0).
        """
        if not self.pipeline:
            self.logger.warning("Attempted prediction without a loaded model.")
            return [0.0] * len(participants)

        if not participants:
            return []

        try:
            # 1. Convert to DataFrame
            # The pipeline expects raw columns (it will handle cleaning itself)
            df = pd.DataFrame(participants)

            # 2. Predictions
            # The pipeline executes in order:
            #   a. PmuFeatureEngineer.transform() -> Calculates ratios, handles dates
            #   b. ColumnTransformer -> Encodes categories (handles unknowns automatically)
            #   c. CalibratedClassifierCV -> Predicts actual probability
            
            # predict_proba returns a matrix (N_samples, 2). Column 1 is the "Winner" class
            probabilities = self.pipeline.predict_proba(df)[:, 1]

            # Explicit conversion to native float list for easy JSON serialization
            return probabilities.tolist()

        except Exception as exc:
            self.logger.error(f"Error during prediction: {exc}")
            # In case of crash (critical missing column), return zeros to avoid breaking the API
            return [0.0] * len(participants)