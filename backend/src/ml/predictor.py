import joblib
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union

class RacePredictor:
    """
    Module d'inférence simplifié.
    Charge le Pipeline complet (Feature Engineering -> Preprocessing -> Calibration).
    Plus besoin de gérer manuellement les catégories ou les artefacts.
    """

    def __init__(self, model_path: str = "data/model_calibrated.pkl") -> None:
        """
        Initialise le prédicteur en chargeant le pipeline sérialisé.
        """
        self.logger = logging.getLogger("ML.Predictor")
        self.model_path = model_path
        self.pipeline = None
        
        self._load_model()

    def _load_model(self) -> None:
        """Charge le fichier unique contenant tout le pipeline."""
        try:
            self.logger.info(f"Chargement du modèle depuis {self.model_path}...")
            # joblib est souvent plus efficace que pickle pour les gros objets numpy/sklearn
            self.pipeline = joblib.load(self.model_path)
            self.logger.info("Modèle chargé avec succès.")
        except FileNotFoundError:
            self.logger.error(f"Fichier modèle introuvable : {self.model_path}")
        except Exception as exc:
            self.logger.error(f"Erreur critique lors du chargement du modèle : {exc}")

    def predict_race(self, participants: List[Dict[str, Any]]) -> List[float]:
        """
        Prédit les probabilités de victoire pour une liste de participants bruts (venant de l'API/DB).

        Args:
            participants: Liste de dictionnaires contenant les données brutes 
                          (ex: {'program_date': '2023...', 'career_winnings': 5000, ...})

        Returns:
            List[float]: Probabilités calibrées (entre 0.0 et 1.0).
        """
        if not self.pipeline:
            self.logger.warning("Tentative de prédiction sans modèle chargé.")
            return [0.0] * len(participants)

        if not participants:
            return []

        try:
            # 1. Conversion en DataFrame
            # Le pipeline s'attend à recevoir les colonnes brutes (il fera le nettoyage lui-même)
            df = pd.DataFrame(participants)

            # 2. Prédictions
            # Le pipeline exécute dans l'ordre :
            #   a. PmuFeatureEngineer.transform() -> Calcule les ratios, gère les dates
            #   b. ColumnTransformer -> Encode les catégories (gère les inconnus automatiquement)
            #   c. CalibratedClassifierCV -> Predit la probabilité réelle
            
            # predict_proba renvoie une matrice (N_samples, 2). La colonne 1 est la classe "Winner"
            probabilities = self.pipeline.predict_proba(df)[:, 1]

            # Conversion explicite en liste de float natifs pour JSON serialization facile
            return probabilities.tolist()

        except Exception as exc:
            self.logger.error(f"Erreur lors de la prédiction : {exc}")
            # En cas de crash (colonne manquante critique), on renvoie des zéros pour ne pas casser l'API
            return [0.0] * len(participants)