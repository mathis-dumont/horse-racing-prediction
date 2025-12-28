"""
Main entry point for the FastAPI application.
"""
import logging
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status
import pandas as pd # Ensure pandas is imported

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
        # PATH Points to data/model_calibrated.pkl
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        model_path = project_root / "data" / "model_calibrated.pkl"
        
        # Pass the path as a string to the Predictor
        ml_models["predictor"] = RacePredictor(str(model_path))
        
        # Small health check of the internal pipeline
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


@app.get("/bets/sniper/{date_code}", response_model=List[BetRecommendation])
def get_sniper_bets(date_code: str, repository: RaceRepository = Depends(get_repository)):
    # 1. Check Model Availability
    predictor = ml_models.get("predictor")
    if not predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="ML Model is strictly required for betting calculations."
        )

    # 2. Data Retrieval
    raw_participants = repository.get_daily_data_for_ml(date_code)
    if not raw_participants:
        return []

    # 3. Vectorized Prediction
    try:
        # Assuming predict_race handles the list of dicts correctly
        probs = predictor.predict_race(raw_participants)
    except Exception as e:
        logger.error(f"Prediction failure: {e}")
        raise HTTPException(status_code=500, detail="Inference engine failed.")

    # 4. DataFrame Construction
    df = pd.DataFrame(raw_participants)
    df['win_probability'] = probs

    # Clean Odds: Replace 0 or NaN with 1.1 (basically impossible to win, to avoid 1/0 error)
    df['reference_odds'] = df['reference_odds'].fillna(1.0)
    df['reference_odds'] = df['reference_odds'].clip(lower=1.05)

    # Vectorized Math
    df['implied_prob'] = 1 / df['reference_odds']
    df['edge'] = df['win_probability'] - df['implied_prob']

    # Filter Strategy (Vectorized Filtering is faster than iterating)
    sniper_filter = (
        (df['edge'] >= MIN_EDGE) & 
        (df['reference_odds'] >= MIN_ODDS) & 
        (df['reference_odds'] <= MAX_ODDS)
    )
    
    candidates = df[sniper_filter].copy()

    recommendations = []
    
    # Select best horse per race from the filtered candidates
    # We group by race_id and take the one with the highest edge
    # (Alternatively, you can take the one with highest win_probability)
    for race_id, group in candidates.groupby('race_id'):
        best_bet = group.sort_values('win_probability', ascending=False).iloc[0]
        
        recommendations.append({
            "race_id": int(best_bet['race_id']),
            "race_num": int(best_bet['race_number']),
            "horse_name": best_bet['horse_name'],
            "pmu_number": int(best_bet['pmu_number']),
            "odds": float(best_bet['reference_odds']),
            "win_probability": float(best_bet['win_probability']),
            "edge": float(best_bet['edge']),
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