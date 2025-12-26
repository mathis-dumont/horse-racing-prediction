"""
Inference module for loading the trained model and generating predictions.
"""
import joblib
import pandas as pd
import logging
from typing import List, Dict, Any, Optional

class RacePredictor:
    """
    Wrapper around the trained Scikit-Learn/XGBoost pipeline to perform inference.
    """

    def __init__(self, model_path: str = "data/model_xgboost.pkl") -> None:
        """
        Initializes the predictor and attempts to load the model.

        Args:
            model_path (str): Path to the serialized .pkl model file.
        """
        self.logger = logging.getLogger("ML.Predictor")
        self.model_path = model_path
        self.pipeline = self._load_model()

    def _load_model(self) -> Any:
        """Internal method to safely load the model file."""
        try:
            return joblib.load(self.model_path)
        except FileNotFoundError:
            self.logger.error(f"Model file not found at: {self.model_path}")
            return None
        except Exception as exc:
            self.logger.error(f"Error loading model: {exc}")
            return None

    def predict_race(self, participants: List[Dict[str, Any]]) -> List[float]:
        """
        Predicts winning probabilities for a list of participants in a single race.

        Args:
            participants (List[Dict[str, Any]]): List of dictionaries containing 
                raw participant data (as returned by the repository).

        Returns:
            List[float]: A list of float probabilities (0.0 to 1.0) corresponding 
                to the input list order. Returns 0.0s on failure.
        """
        if not self.pipeline:
            self.logger.warning("Attempted prediction with no loaded model.")
            return [0.0] * len(participants)
            
        if not participants:
            return []

        try:
            # Convert raw dicts to DataFrame
            input_dataframe = pd.DataFrame(participants)
            
            # The pipeline handles all steps:
            # 1. PmuFeatureEngineer -> Ratios, Ranks, Missing Values
            # 2. OrdinalEncoder -> Categorical encoding
            # 3. XGBoost -> Prediction
            win_probabilities = self.pipeline.predict_proba(input_dataframe)[:, 1]
            
            return win_probabilities.tolist()

        except Exception as exc:
            self.logger.error(f"Prediction crash: {exc}")
            # Return safe fallback to prevent API 500
            return [0.0] * len(participants)