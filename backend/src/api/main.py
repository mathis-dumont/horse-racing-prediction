"""
Main entry point for the FastAPI application.
"""
import logging
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from src.api.schemas import RaceSummary, ParticipantSummary, PredictionResult, BetRecommendation
from src.api.repositories import RaceRepository
from src.ml.predictor import RacePredictor

# --- SNIPER STRATEGY CONFIG ---
MIN_EDGE = 0.05
MIN_ODDS = 5.0
MAX_ODDS = 20.0

# Logger Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("API")

# --- LIFESPAN (ML Model Management) ---
ml_models: Dict[str, Optional[RacePredictor]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    """
    logger.info("LOADING ML PIPELINE...")
    try:
        # CORRECTION DU PATH : On pointe vers data/model_calibrated.pkl
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent # remonte de src/api/ -> root
        model_path = project_root / "data" / "model_calibrated.pkl"
        
        # On passe le chemin sous forme de string au Predictor
        ml_models["predictor"] = RacePredictor(str(model_path))
        
        # Petit check de santé du pipeline interne
        if ml_models["predictor"].pipeline:
            logger.info(f"Model loaded successfully from {model_path}")
        else:
            logger.warning(f"Model file found but pipeline is empty.")
            
    except Exception as exc:
        logger.error(f"WARNING: Failed to load ML model ({exc}). API will run without predictions.")
        ml_models["predictor"] = None
    
    yield
    ml_models.clear()

app = FastAPI(title="PMU Predictor API", lifespan=lifespan)

def get_repository() -> RaceRepository:
    return RaceRepository()

# --- ROUTES ---

@app.get("/")
def health_check():
    status = "loaded" if ml_models.get("predictor") and ml_models["predictor"].pipeline else "failed"
    return {"status": "online", "ml_engine": status}

@app.get("/races/{date_code}", response_model=List[RaceSummary])
def get_races(date_code: str, repository: RaceRepository = Depends(get_repository)):
    return repository.get_races_by_date(date_code)

@app.get("/races/{race_id}/participants", response_model=List[ParticipantSummary])
def get_race_participants(race_id: int, repository: RaceRepository = Depends(get_repository)):
    return repository.get_participants_by_race(race_id)

# Dans src/api/main.py

import pandas as pd # Assure-toi d'avoir importé pandas

@app.get("/bets/sniper/{date_code}", response_model=List[BetRecommendation])
def get_sniper_bets(date_code: str, repository: RaceRepository = Depends(get_repository)):
    """
    VERSION OPTIMISÉE (BATCH): Scan toutes les courses en un coup.
    """
    predictor = ml_models.get("predictor")
    if not predictor or not predictor.pipeline:
        raise HTTPException(status_code=503, detail="ML Model not loaded.")

    # 1. Récupération massive (1 seule requête SQL)
    raw_participants = repository.get_daily_data_for_ml(date_code)
    
    if not raw_participants:
        return []

    # 2. Prédiction massive (Vectorisée)
    # Le modèle prédit 1000 chevaux d'un coup en une fraction de seconde
    probs = predictor.predict_race(raw_participants)

    # 3. Assemblage et Analyse (en mémoire)
    # On crée un DataFrame temporaire pour manipuler facilement les groupes
    df = pd.DataFrame(raw_participants)
    df['win_probability'] = probs
    
    # Gestion sécurisée des cotes manquantes ou nulles
    df['reference_odds'] = df['reference_odds'].fillna(10.0)
    df.loc[df['reference_odds'] <= 1.0, 'reference_odds'] = 1.1 # Sécurité division par zéro
    
    df['implied_prob'] = 1 / df['reference_odds']
    df['edge'] = df['win_probability'] - df['implied_prob']

    recommendations = []

    # 4. GroupBy Race ID pour trouver le meilleur cheval de chaque course
    for race_id, group in df.groupby('race_id'):
        # On trie par probabilité décroissante
        sorted_group = group.sort_values('win_probability', ascending=False)
        
        if sorted_group.empty:
            continue
            
        # On prend le top 1
        top_pick = sorted_group.iloc[0]
        
        # Filtres Stratégie Sniper
        if (top_pick['edge'] > MIN_EDGE and 
            MIN_ODDS <= top_pick['reference_odds'] < MAX_ODDS):
            
            recommendations.append({
                "race_id": int(top_pick['race_id']), # Conversion int importante pour Pydantic
                "race_num": int(top_pick['race_number']),
                "horse_name": top_pick['horse_name'],
                "pmu_number": int(top_pick['pmu_number']),
                "odds": float(top_pick['reference_odds']),
                "win_probability": float(top_pick['win_probability']),
                "edge": float(top_pick['edge']),
                "strategy": "Sniper"
            })

    return recommendations

@app.get("/races/{race_id}/predict", response_model=List[PredictionResult])
def predict_race(race_id: int, repository: RaceRepository = Depends(get_repository)):
    predictor = ml_models.get("predictor")
    if not predictor or not predictor.pipeline:
        raise HTTPException(status_code=503, detail="ML Model unavailable.")

    raw_participants = repository.get_race_data_for_ml(race_id)
    if not raw_participants:
        raise HTTPException(status_code=404, detail="Race not found.")

    try:
        win_probabilities = predictor.predict_race(raw_participants)
    except Exception as exc:
        logger.error(f"ML Error: {exc}")
        raise HTTPException(status_code=500, detail="Prediction failed.")

    results = []
    for index, participant in enumerate(raw_participants):
        results.append({
            "pmu_number": participant["pmu_number"],
            "horse_name": participant["horse_name"],
            "win_probability": win_probabilities[index],
            "predicted_rank": 0
        })

    results.sort(key=lambda x: x["win_probability"], reverse=True)
    for rank, res in enumerate(results, 1):
        res["predicted_rank"] = rank

    return results