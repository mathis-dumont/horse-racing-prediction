"""
Main entry point for the FastAPI application.
Handles routing, model lifecycle management, and betting logic.
"""
import logging
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status
import pandas as pd

from src.api.schemas import (
    RaceSummary, 
    ParticipantSummary, 
    PredictionResult, 
    BetRecommendation
)
from src.api.repositories import RaceRepository
from src.ml.predictor import RacePredictor

# --- CONFIGURATION: SNIPER STRATEGY ---
MIN_EDGE = 0.05       # Minimum expected value (5%)
MIN_ODDS = 5.0        # Minimum decimal odds
MAX_ODDS = 20.0       # Maximum decimal odds (to avoid longshots)
DEFAULT_ODDS_IF_MISSING = 1.1

# Logger Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("API")

# --- LIFESPAN: ML Model Management ---
ml_models: Dict[str, Optional[RacePredictor]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the application.
    Loads the Machine Learning model into memory on startup.
    """
    logger.info("Initializing ML Pipeline...")
    try:
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        model_path = project_root / "data" / "model_calibrated.pkl"
        
        # Initialize Predictor
        ml_models["predictor"] = RacePredictor(str(model_path))
        
        # Safe access to check pipeline existence
        predictor = ml_models["predictor"]
        if predictor and predictor.pipeline:
            logger.info(f"Model successfully loaded from {model_path}")
        else:
            logger.warning("Model file found, but the pipeline is empty/invalid.")
            
    except Exception as exc:
        logger.error(f"CRITICAL: Failed to load ML model ({exc}). Inference endpoints will fail.")
        ml_models["predictor"] = None
    
    yield
    ml_models.clear()
    logger.info("ML Pipeline shut down.")

app = FastAPI(title="PMU Predictor API", lifespan=lifespan)

# --- DEPENDENCY INJECTION ---
def get_repository() -> RaceRepository:
    """Dependency provider for the RaceRepository."""
    return RaceRepository()

# --- ROUTES ---

@app.get("/", tags=["System"])
def health_check() -> Dict[str, str]:
    """Returns the operational status of the API and the ML Engine."""
    predictor = ml_models.get("predictor")
    
    # Mypy Safe Check: Ensure predictor is not None before accessing attributes
    if predictor is not None and predictor.pipeline:
        model_status = "loaded"
    else:
        model_status = "failed"
        
    return {"status": "online", "ml_engine": model_status}

@app.get("/races/{date_code}", response_model=List[RaceSummary], tags=["Races"])
def get_races(date_code: str, repository: RaceRepository = Depends(get_repository)) -> List[Dict[str, Any]]:
    """Fetches all races for a given date (DDMMYYYY)."""
    return repository.get_races_by_date(date_code)

@app.get("/races/{race_id}/participants", response_model=List[ParticipantSummary], tags=["Races"])
def get_race_participants(race_id: int, repository: RaceRepository = Depends(get_repository)) -> List[Dict[str, Any]]:
    """Fetches participants for a specific race."""
    return repository.get_participants_by_race(race_id)


@app.get("/bets/sniper/{date_code}", response_model=List[BetRecommendation], tags=["Betting"])
def get_sniper_bets(date_code: str, repository: RaceRepository = Depends(get_repository)) -> List[Dict[str, Any]]:
    """
    Generates betting recommendations using the 'Sniper' strategy.
    """
    predictor = ml_models.get("predictor")
    
    # Mypy Safe Check
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="ML Model is unavailable. Betting calculations cannot proceed."
        )

    # 1. Retrieve Raw Data
    raw_participants = repository.get_daily_data_for_ml(date_code)
    if not raw_participants:
        logger.info(f"No data found for date {date_code}")
        return []

    # 2. Vectorized Prediction
    try:
        probabilities = predictor.predict_race(raw_participants)
    except Exception as exc:
        logger.error(f"Inference engine failure: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Inference engine failed."
        )

    # 3. DataFrame Construction & Logic Application
    df = pd.DataFrame(raw_participants)
    df['win_probability'] = probabilities

    # Clean Odds: Sanitize missing values
    df['reference_odds'] = df['reference_odds'].fillna(1.0).infer_objects(copy=False)
    df['reference_odds'] = df['reference_odds'].clip(lower=1.05)

    # Calculate Edge
    df['implied_prob'] = 1 / df['reference_odds']
    df['edge'] = df['win_probability'] - df['implied_prob']

    # Filter Strategy (Vectorized)
    sniper_mask = (
        (df['edge'] >= MIN_EDGE) & 
        (df['reference_odds'] >= MIN_ODDS) & 
        (df['reference_odds'] <= MAX_ODDS)
    )
    
    candidates = df[sniper_mask].copy()

    recommendations = []
    
    # Selection: Choose the single best bet per race based on Probability
    for race_id, group in candidates.groupby('race_id'):
        best_bet = group.sort_values('win_probability', ascending=False).iloc[0]
        
        recommendations.append({
            "race_id": int(best_bet['race_id']),
            "race_num": int(best_bet['race_number']),
            "horse_name": best_bet['horse_name'],
            "program_number": int(best_bet['program_number']),
            "odds": float(best_bet['reference_odds']),
            "win_probability": float(best_bet['win_probability']),
            "edge": float(best_bet['edge']),
            "strategy": "Sniper"
        })

    return recommendations

@app.get("/races/{race_id}/predict", response_model=List[PredictionResult], tags=["Predictions"])
def predict_race(race_id: int, repository: RaceRepository = Depends(get_repository)) -> List[Dict[str, Any]]:
    """
    Returns ML predictions (Win Probability and Rank) for a specific race.
    """
    predictor = ml_models.get("predictor")
    
    # Mypy Safe Check: Ensure predictor exists AND has a pipeline
    if predictor is None or not predictor.pipeline:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="ML Model unavailable."
        )

    raw_participants = repository.get_race_data_for_ml(race_id)
    if not raw_participants:
        raise HTTPException(status_code=404, detail="Race not found.")

    try:
        win_probabilities = predictor.predict_race(raw_participants)
    except Exception as exc:
        logger.error(f"ML Error during single race prediction: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Prediction process failed."
        )

    results = []
    for index, participant in enumerate(raw_participants):
        results.append({
            "program_number": participant["program_number"],
            "horse_name": participant["horse_name"],
            "win_probability": win_probabilities[index],
            "predicted_rank": 0 # Placeholder, calculated below
        })

    # Sort by probability descending to determine rank
    results.sort(key=lambda x: x["win_probability"], reverse=True)
    
    for rank, res in enumerate(results, 1):
        res["predicted_rank"] = rank
        
    return results