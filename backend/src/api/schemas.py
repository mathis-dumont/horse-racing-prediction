"""
Pydantic schemas for API request and response validation.
"""
from typing import Optional
from pydantic import BaseModel

class RaceSummary(BaseModel):
    """Schema representing a summary of a race."""
    race_id: int
    meeting_number: int
    race_number: int
    discipline: Optional[str] = None
    distance_m: Optional[int] = None
    racetrack_code: Optional[str] = None
    name: Optional[str] = None

class ParticipantSummary(BaseModel):
    """Schema representing a participant in a race (basic details)."""
    pmu_number: int
    horse_name: str
    driver_name: Optional[str] = None
    trainer_name: Optional[str] = None
    odds: Optional[float] = None

class PredictionResult(BaseModel):
    """Schema representing the machine learning prediction result for a participant."""
    pmu_number: int
    horse_name: str
    win_probability: float
    predicted_rank: int
    
class BetRecommendation(BaseModel):
    race_id: int
    race_num: int
    horse_name: str
    pmu_number: int
    odds: float
    win_probability: float
    edge: float
    strategy: str = "Sniper"