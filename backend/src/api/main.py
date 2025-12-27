"""
Main entry point for the FastAPI application.
Handles lifecycle management, dependency injection, and route definitions.
"""
import logging
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from src.api.schemas import RaceSummary, ParticipantSummary, PredictionResult
from src.api.repositories import RaceRepository
from src.ml.predictor import RacePredictor
from pathlib import Path
from src.api.schemas import BetRecommendation 

# --- SNIPER STRATEGY CONFIG ---
MIN_EDGE = 0.05 # Change to -0.50 (negative edge)
MIN_ODDS = 5.0   # Change to 1.1 (all odds)
MAX_ODDS = 20.0

# Logger Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("API")

# --- LIFESPAN (ML Model Management) ---
# Dictionary to hold the ML model instance in memory
ml_models: Dict[str, Optional[RacePredictor]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Loads the XGBoost model once at startup to optimize performance.
    """
    logger.info("LOADING XGBOOST MODEL...")
    try:
        # 1. Calculate Dynamic Path
                
        current_file = Path(__file__).resolve()
        src_root = current_file.parent.parent  # Go up from 'api' to 'src'
        model_path = src_root / "ml" / "probability_calibrator.pkl"
        
        ml_models["predictor"] = RacePredictor(str(model_path))
        logger.info(f"Model loaded successfully from {model_path}")
    except Exception as exc:
        logger.error(f"WARNING: Failed to load ML model ({exc}). API will run without predictions.")
        ml_models["predictor"] = None
    
    yield # API runs here
    
    # Cleanup on shutdown
    ml_models.clear()

# Initialize App with Lifespan
app = FastAPI(title="PMU Predictor API", lifespan=lifespan)

# Dependency Injection
def get_repository() -> RaceRepository:
    """Dependency provider for RaceRepository."""
    return RaceRepository()

# --- ROUTES ---
# --- ROOT ROUTE (Health Check) ---
@app.get("/")
def health_check():
    """
    Simple health check to verify API status and Model loading.
    """
    model_status = "loaded" if ml_models.get("predictor") else "failed"
    return {
        "status": "online", 
        "application": "PMU Predictor API", 
        "ml_engine": model_status
    }

@app.get("/races/{date_code}", response_model=List[RaceSummary])
def get_races(
    date_code: str, 
    repository: RaceRepository = Depends(get_repository)
):
    """
    Get all races for a specific date.
    
    Args:
        date_code: Date in 'DDMMYYYY' format.
    """
    return repository.get_races_by_date(date_code)

@app.get("/races/{race_id}/participants", response_model=List[ParticipantSummary])
def get_race_participants(
    race_id: int, 
    repository: RaceRepository = Depends(get_repository)
):
    """
    Get participants for a specific race.
    """
    return repository.get_participants_by_race(race_id)

# --- ML PREDICTION ROUTE ---
@app.get("/bets/sniper/{date_code}", response_model=List[BetRecommendation])
@app.get("/bets/sniper/{date_code}", response_model=List[BetRecommendation])
def get_sniper_bets(
    date_code: str,
    repository: RaceRepository = Depends(get_repository)
):
    """
    Scans ALL races for a specific date and returns bets matching the Sniper Strategy.
    """
    predictor = ml_models.get("predictor")
    if not predictor:
        raise HTTPException(status_code=503, detail="ML Model not loaded.")

    races = repository.get_races_by_date(date_code)
    recommendations = []

    for race in races:
        # --- FIX: USE 'race_id' KEY ---
        if isinstance(race, dict):
            race_id = race.get('race_id') or race.get('id')
            race_num = race.get('race_number')
        else:
            race_id = getattr(race, 'race_id', getattr(race, 'id', None))
            race_num = getattr(race, 'race_number', None)

        if not race_id:
            continue

        # 2. Get Data
        raw_participants = repository.get_race_data_for_ml(race_id)
        if not raw_participants:
            continue
            
        # 3. Predict
        try:
            probs = predictor.predict_race(raw_participants)
        except:
            continue

        # 4. Analyze
        race_results = []
        for i, p in enumerate(raw_participants):
            prob = float(probs[i]) if i < len(probs) else 0.0
            odds = float(p.get('reference_odds') or 10.0)
            implied_prob = 1 / odds if odds > 0 else 0
            edge = prob - implied_prob
            
            race_results.append({
                "participant": p,
                "prob": prob,
                "edge": edge,
                "odds": odds
            })

        race_results.sort(key=lambda x: x["prob"], reverse=True)
        
        if not race_results:
            continue

        top_pick = race_results[0]

        # 5. Filter (Using Nuclear Settings to verify UI, revert to 0.05 / 5.0 later)
        if (top_pick["edge"] > MIN_EDGE and 
            MIN_ODDS <= top_pick["odds"] < MAX_ODDS):
            
            recommendations.append({
                "race_id": race_id,
                "race_num": race_num,
                "horse_name": top_pick["participant"]["horse_name"],
                "pmu_number": top_pick["participant"]["pmu_number"],
                "odds": top_pick["odds"],
                "win_probability": top_pick["prob"],
                "edge": top_pick["edge"],
                "strategy": "Sniper"
            })

    return recommendations

@app.get("/races/{race_id}/predict", response_model=List[PredictionResult])
def predict_race(
    race_id: int, 
    repository: RaceRepository = Depends(get_repository)
):
    """
    Generates predictions for a specific race using the loaded ML model.
    Fetches raw data from the database, processes it, and returns ranked probabilities.
    """
    predictor = ml_models.get("predictor")
    
    # Check if predictor is loaded and has a valid pipeline
    if not predictor or not predictor.pipeline:
        raise HTTPException(
            status_code=503, 
            detail="Prediction model is unavailable (missing .pkl file?)."
        )

    # 1. Fetch enriched raw data from PostgreSQL
    raw_participants = repository.get_race_data_for_ml(race_id)
    
    if not raw_participants:
        raise HTTPException(
            status_code=404, 
            detail="Race not found or no participants available."
        )

    # 2. Prediction via Pipeline (Transformation + XGBoost)
    try:
        # Repository returns RealDictRow, compatible with list(dict)
        win_probabilities = predictor.predict_race(raw_participants)
    except Exception as exc:
        logger.error(f"ML Error: {exc}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal prediction engine error: {str(exc)}"
        )

    # 3. Construct Response
    results = []
    for index, participant in enumerate(raw_participants):
        results.append({
            "pmu_number": participant["pmu_number"],
            "horse_name": participant["horse_name"],
            "win_probability": float(win_probabilities[index]), # numpy -> float
            "predicted_rank": 0 # Calculated below
        })

    # 4. Sorting and Ranking
    # Sort by probability descending
    results.sort(key=lambda x: x["win_probability"], reverse=True)
    
    # Assign rank based on sort order
    for rank, res in enumerate(results, 1):
        res["predicted_rank"] = rank

    return results