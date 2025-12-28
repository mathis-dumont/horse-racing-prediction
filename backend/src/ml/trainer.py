import joblib
import logging
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import log_loss, roc_auc_score

from src.ml.loader import DataLoader
from src.ml.features import PmuFeatureEngineer

class XGBoostTrainer:
    """
    Entraîneur Avancé avec Calibration de Probabilités.
    Correction : Gestion explicite des arguments pour Sklearn récents.
    """

    def __init__(self, model_path: str = "data/model_calibrated.pkl") -> None:
        self.logger = logging.getLogger("ML.Trainer")
        self.model_path = model_path
        self.loader = DataLoader()
        
        # Configuration des Features
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
        """
        Workflow d'entraînement : Train -> Calibrate -> Evaluate.
        """
        # 1. Chargement
        try:
            raw_df = self.loader.get_training_data()
        except Exception as e:
            self.logger.error(f"Impossible de charger les données: {e}")
            return

        if raw_df.empty:
            self.logger.error("Aucune donnée retournée par le loader.")
            return

        # 2. Feature Engineering
        engineer = PmuFeatureEngineer()
        full_df = engineer.fit_transform(raw_df)
        
        # 3. Split Temporel
        max_date = full_df['program_date'].max()
        test_cutoff = max_date - pd.Timedelta(days=test_days)
        val_cutoff = test_cutoff - pd.Timedelta(days=val_days)

        train_df = full_df[full_df['program_date'] <= val_cutoff]
        val_df = full_df[(full_df['program_date'] > val_cutoff) & (full_df['program_date'] <= test_cutoff)]
        test_df = full_df[full_df['program_date'] > test_cutoff]

        self.logger.info(f"Split: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")

        features = self.numerical_features + self.categorical_features
        X_train, y_train = train_df[features], train_df['is_winner']
        X_val, y_val = val_df[features], val_df['is_winner']
        X_test, y_test = test_df[features], test_df['is_winner']

        # 4. Preprocessing (Encoding)
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), self.categorical_features),
                ('num', 'passthrough', self.numerical_features)
            ]
        )

        # On encode manuellement pour le modèle de base (étape intermédiaire)
        self.logger.info("Preprocessing des données...")
        X_train_enc = preprocessor.fit_transform(X_train, y_train)
        X_val_enc = preprocessor.transform(X_val)
        X_test_enc = preprocessor.transform(X_test)

        # 5. Modèle de Base XGBoost
        base_xgb = XGBClassifier(
            n_estimators=2500,
            max_depth=5,
            learning_rate=0.015,
            subsample=0.7,
            colsample_bytree=0.7,
            tree_method='hist',
            early_stopping_rounds=50,
            random_state=42,
            n_jobs=-1,
            eval_metric='logloss'
        )

        self.logger.info("Entraînement du modèle de base XGBoost...")
        base_xgb.fit(
            X_train_enc, y_train,
            eval_set=[(X_val_enc, y_val)],
            verbose=100
        )

        # 6. Calibration (CORRECTION ICI)
        self.logger.info("Calibration des probabilités (Isotonic Regression)...")
        
        # CORRECTION : On passe explicitement 'estimator=' pour éviter le bug InvalidParameterError
        calibrated_model = CalibratedClassifierCV(
            estimator=base_xgb,  # <--- C'était implicite avant, maintenant obligatoire pour 'prefit'
            method='isotonic', 
            cv='prefit'
        )
        
        calibrated_model.fit(X_val_enc, y_val)

        # 7. Evaluation
        probs = calibrated_model.predict_proba(X_test_enc)[:, 1]
        loss = log_loss(y_test, probs)
        try:
            auc = roc_auc_score(y_test, probs)
        except ValueError:
            auc = 0.0
        
        self.logger.info(f"TEST RESULTS -> LogLoss: {loss:.4f} | AUC: {auc:.4f}")

        # 8. Sauvegarde Pipeline Final
        full_inference_pipeline = Pipeline([
            ('engineer', engineer),
            ('preprocessor', preprocessor),
            ('model', calibrated_model)
        ])

        joblib.dump(full_inference_pipeline, self.model_path)
        self.logger.info(f"Modèle calibré sauvegardé sous: {self.model_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    trainer = XGBoostTrainer()
    trainer.train()