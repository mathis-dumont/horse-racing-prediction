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
        # Ensure the path is correct relative to the execution directory
        ml_models["predictor"] = RacePredictor("data/model_xgboost.pkl")
        logger.info("Model loaded successfully.")
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