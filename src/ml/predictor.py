# FILE: src/ml/predictor.py
import pickle
import logging
import random
from typing import Dict, Any

class RacePredictor:
    """
    Classe responsable de charger le modèle ML et de faire des prédictions.
    Pattern: Facade / Adapter.
    """
    def __init__(self, model_path: str = "data/model_latest.pkl"):
        self.logger = logging.getLogger("MLPredictor")
        self.model_path = model_path
        self.model = self._load_model()

    def _load_model(self):
        """Essaie de charger un pickle, sinon renvoie None (Mode Mock)"""
        try:
            with open(self.model_path, "rb") as f:
                self.logger.info(f"Modèle chargé depuis {self.model_path}")
                return pickle.load(f)
        except FileNotFoundError:
            self.logger.warning(f"⚠️ Modèle non trouvé à {self.model_path}. Mode DÉMO (Mock) activé.")
            return None

    def predict_probability(self, features: Dict[str, Any]) -> float:
        """
        Reçoit un dictionnaire de features (ex: {'age': 5, 'driver_id': 12})
        Retourne une probabilité de gagner (0.0 à 1.0)
        """
        if self.model:
            # Ici, transformation du dict en array numpy si nécessaire
            # return self.model.predict_proba([list(features.values())])[0][1]
            pass
        
        # --- MOCK (Simulation pour l'API tant que le modèle n'est pas prêt) ---
        # Logique bidon : si le cheval a une bonne musique, il a plus de chance
        musique = features.get("musique", "")
        base_prob = 0.1
        if "1a" in musique: base_prob += 0.3
        if "Da" in musique: base_prob -= 0.05
        
        return min(0.95, max(0.01, base_prob + random.uniform(-0.05, 0.05)))