from typing import Optional
from pydantic import BaseModel

class RaceSummary(BaseModel):
    race_id: int
    meeting_number: int
    race_number: int
    discipline: Optional[str] = None
    distance_m: Optional[int] = None
    racetrack_code: Optional[str] = None

class ParticipantSummary(BaseModel):
    pmu_number: int
    horse_name: str
    driver_name: Optional[str] = None
    trainer_name: Optional[str] = None
    odds: Optional[float] = None