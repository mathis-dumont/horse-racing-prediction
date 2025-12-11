"""
Ingest PMU programme JSON (JSON 1) for a given day.
Scope: Daily Program -> Meetings -> Races.

Logic:
    - Fetches the programme from the API.
    - Inserts data into daily_program, race_meeting, and race.
    - Uses ON CONFLICT DO NOTHING to avoid updates on duplicates.

Usage:
    python scripts/ingest_programme_day.py --date 05112025
"""

import argparse
import datetime as dt
import json
import logging
import os
import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# API URL Template
PROGRAMME_URL_TEMPLATE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{date_code}"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def get_db_connection():
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL environment variable is not set")
    return psycopg2.connect(db_url)

def fetch_programme_json(date_code: str) -> dict:
    url = PROGRAMME_URL_TEMPLATE.format(date_code=date_code)
    logging.info("Fetching programme JSON from %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()

def insert_daily_program(cur, program_date: dt.date) -> int:
    """Insert daily_program if not exists, return program_id."""
    cur.execute(
        """
        INSERT INTO daily_program (program_date)
        VALUES (%s)
        ON CONFLICT (program_date) DO NOTHING
        RETURNING program_id;
        """,
        (program_date,),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    
    # If it existed, fetch the ID
    cur.execute("SELECT program_id FROM daily_program WHERE program_date = %s", (program_date,))
    return cur.fetchone()[0]

def insert_race_meeting(cur, program_id: int, reunion: dict) -> int:
    """Insert race_meeting if not exists, return meeting_id."""
    num_officiel = reunion.get("numOfficiel")
    meeting_type = reunion.get("nature")
    racetrack_code = (reunion.get("hippodrome") or {}).get("code")
    temp = (reunion.get("meteo") or {}).get("temperature")
    wind = (reunion.get("meteo") or {}).get("directionVent")

    cur.execute(
        """
        INSERT INTO race_meeting (
            program_id, meeting_number, meeting_type, 
            racetrack_code, weather_temperature, weather_wind
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (program_id, meeting_number) DO NOTHING
        RETURNING meeting_id;
        """,
        (program_id, num_officiel, meeting_type, racetrack_code, temp, wind),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    
    cur.execute(
        "SELECT meeting_id FROM race_meeting WHERE program_id = %s AND meeting_number = %s",
        (program_id, num_officiel)
    )
    return cur.fetchone()[0]

def insert_race(cur, meeting_id: int, course: dict):
    """Insert race if not exists."""
    race_number = course.get("numOrdre")
    discipline = course.get("discipline")
    race_category = course.get("categorieParticularite")
    age_condition = course.get("conditionAge")
    distance_m = course.get("distance")
    track_type = course.get("typePiste")
    
    # Penetrometer handling
    penetrometre = course.get("penetrometre") or {}
    raw_val = penetrometre.get("valeurMesure")
    terrain_label = penetrometre.get("intitule")
    penetrometer_value = None
    if raw_val is not None:
        try:
            penetrometer_value = float(str(raw_val).replace(",", "."))
        except (ValueError, TypeError):
            pass

    declared_runners = course.get("nombreDeclaresPartants")
    conditions = course.get("conditions")
    race_status = course.get("statut")
    finish_order = json.dumps(course.get("ordreArrivee")) if course.get("ordreArrivee") else None
    
    duration_raw = course.get("dureeCourse")
    race_duration_s = int(duration_raw) // 1000 if duration_raw else None
    race_status_cat = course.get("categorieStatut")

    cur.execute(
        """
        INSERT INTO race (
            meeting_id, race_number, discipline, race_category, age_condition,
            distance_m, track_type, terrain_label, penetrometer,
            declared_runners_count, conditions_text, race_status,
            finish_order_raw, race_duration_s, race_status_category
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (meeting_id, race_number) DO NOTHING;
        """,
        (
            meeting_id, race_number, discipline, race_category, age_condition,
            distance_m, track_type, terrain_label, penetrometer_value,
            declared_runners, conditions, race_status,
            finish_order, race_duration_s, race_status_cat
        ),
    )

def ingest_programme_for_date(date_code: str):
    logger = logging.getLogger(__name__)
    logger.info("Starting PROGRAMME ingestion for date=%s", date_code)

    data = fetch_programme_json(date_code)
    programme = data.get("programme") or {}
    
    # Convert timestamp to date
    ts = programme.get("date")
    if not ts:
        logger.error("No date found in JSON.")
        return
    program_date = dt.datetime.utcfromtimestamp(ts / 1000).date()
    
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Daily Program
                program_id = insert_daily_program(cur, program_date)
                
                # 2. Meetings & Races
                reunions = programme.get("reunions", [])
                logger.info("Found %d meetings", len(reunions))
                
                count_races = 0
                for reunion in reunions:
                    meeting_id = insert_race_meeting(cur, program_id, reunion)
                    courses = reunion.get("courses", [])
                    for course in courses:
                        insert_race(cur, meeting_id, course)
                        count_races += 1
                
                logger.info("Ingested %d races for date %s", count_races, program_date)
    finally:
        conn.close()

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_programme_for_date(args.date)