"""
Pydantic schemas for API request and response validation.
Defines the data contract for race summaries, participants, and betting recommendations.
"""
from typing import Optional
from pydantic import BaseModel, Field

class RaceSummary(BaseModel):
    """
    Represents a high-level summary of a horse race.
    """
    race_id: int
    meeting_number: int
    race_number: int
    discipline: Optional[str] = None
    distance_m: Optional[int] = Field(None, description="Distance of the race in meters.")
    racetrack_code: Optional[str] = None
    name: Optional[str] = None
    declared_runners_count: Optional[int] = Field(None, description="Number of declared runners.")

class ParticipantSummary(BaseModel):
    """
    Represents basic details of a participant (horse/driver) in a specific race.
    """
    program_number: int = Field(..., description="The number worn by the horse (formerly PMU number).")
    horse_name: str
    driver_name: Optional[str] = None
    trainer_name: Optional[str] = None
    odds: Optional[float] = Field(None, description="Current live odds for the participant.")

class PredictionResult(BaseModel):
    """
    Represents the output of the machine learning prediction model.
    """
    program_number: int
    horse_name: str
    win_probability: float
    predicted_rank: int

class BetRecommendation(BaseModel):
    """
    Represents a betting opportunity identified by the strategy engine.
    """
    race_id: int
    race_num: int
    horse_name: str
    program_number: int
    odds: float
    win_probability: float
    edge: float
    strategy: str = "Sniper"