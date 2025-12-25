from typing import List
from fastapi import FastAPI, Depends
from src.api.schemas import RaceSummary, ParticipantSummary
from src.api.repositories import RaceRepository

app = FastAPI()

def get_repository():
    return RaceRepository()

@app.get("/races/{date_code}", response_model=List[RaceSummary])
def get_races(date_code: str, repo: RaceRepository = Depends(get_repository)):
    return repo.get_races_by_date(date_code)

@app.get("/races/{race_id}/participants", response_model=List[ParticipantSummary])
def get_race_participants(race_id: int, repo: RaceRepository = Depends(get_repository)):
    return repo.get_participants_by_race(race_id)