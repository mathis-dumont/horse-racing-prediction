"""
Ingest PMU programme JSON (JSON 1) for a given day.
Scope: Daily Program -> Meetings -> Races.

Improvements:
- Implemented robust Retry logic (HTTPAdapter) for API resilience.
- Professional logging and error handling.
- DATA OPTIMIZATION: Maps verbose status/track strings to short codes.
"""

import argparse
import datetime as dt
import json
import logging
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
PROGRAMME_URL_TEMPLATE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{date_code}"

# --- OPTIMIZED MAPPINGS (Storage Efficiency) ---

# "race_status": Normalizes verbose API status strings into short database codes.
STATUS_MAP = {
    "ARRIVEE_DEFINITIVE_COMPLETE": "FIN",
    "ARRIVEE_DEFINITIVE_C": "FIN", # Handle truncated API responses
    "FIN_COURSE": "FIN",
    "COURSE_ANNULEE": "ANN",
    "A_PARTIR": "FUT",  # Future
    "EN_COURS": "LIVE",
    "ARRIVEE_PROVISOIRE": "PROV"
}

# "track_type": Maps surface types to single-character codes (e.g., SABLE -> S).
TRACK_MAP = {
    "SABLE": "S",
    "POUZZOLANE": "P",
    "HERBE": "H",
    "CENDREE": "C",
    "MACHEFER": "M"
}

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

def get_db_connection():
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL environment variable is not set")
    return psycopg2.connect(db_url)

def get_http_session():
    """
    Creates a requests Session with automatic retry logic.
    Configured to handle transient network errors (429, 5xx) with exponential backoff.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1, # Wait 1s, 2s, 4s...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_programme_json(date_code: str) -> dict:
    """
    Fetches the daily programme using browser-mimicking headers to avoid ACL blocks.
    Delegates network resilience to the configured HTTP session.
    """
    url = PROGRAMME_URL_TEMPLATE.format(date_code=date_code)
    logging.info("Fetching programme JSON from %s", url)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.pmu.fr/",
        "Origin": "https://www.pmu.fr"
    }

    session = get_http_session()

    try:
        resp = session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logging.error("CRITICAL: Failed to fetch programme after retries: %s", e)
        raise e

def insert_daily_program(cur, program_date: dt.date) -> int:
    """
    Idempotent insert for the Daily Program entity.
    Returns the PK (program_id) whether created or existing.
    """
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
    
    cur.execute("SELECT program_id FROM daily_program WHERE program_date = %s", (program_date,))
    return cur.fetchone()[0]

def safe_truncate(field_name, value, max_length=20):
    """
    Defensive programming utility.
    Truncates strings exceeding schema limits to prevent 'value too long' SQL errors.
    Logs a warning when data loss occurs.
    """
    if value and isinstance(value, str) and len(value) > max_length:
        truncated = value[:max_length]
        logging.warning(f"OVERFLOW DETECTED [{field_name}]: '{value}' ({len(value)} chars) -> Truncated to '{truncated}'")
        return truncated
    return value

def insert_race_meeting(cur, program_id: int, reunion: dict) -> int:
    num_officiel = reunion.get("numOfficiel")
    
    # Defensive truncation for variable-length text fields
    meeting_type = safe_truncate("meeting_type", reunion.get("nature"), 50)
    
    # racetrack_code is strictly VARCHAR(10)
    racetrack_code = safe_truncate("racetrack_code", (reunion.get("hippodrome") or {}).get("code"), 10)
    
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
    race_number = course.get("numOrdre")
    
    # 1. STATUS MAPPING (Optimization)
    raw_status = course.get("statut")
    # Apply short code map, fallback to truncation if unknown status
    race_status = STATUS_MAP.get(raw_status, raw_status[:10] if raw_status else None)

    # 2. TRACK MAPPING (Optimization)
    raw_track = course.get("typePiste")
    track_type = TRACK_MAP.get(raw_track, raw_track[:10] if raw_track else None)

    # Sanitize text fields
    discipline = safe_truncate("discipline", course.get("discipline"), 20)
    race_status_category = safe_truncate("race_status_category", course.get("categorieStatut"), 50)
    
    race_category = course.get("categorieParticularite") # VARCHAR(50)
    distance_m = course.get("distance")
    
    # Safe Float Conversion for Penetrometer (handles European comma decimal format)
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
    
    # Time conversion: API provides milliseconds, DB expects seconds
    duration_raw = course.get("dureeCourse")
    race_duration_s = int(duration_raw) // 1000 if duration_raw else None

    cur.execute(
        """
        INSERT INTO race (
            meeting_id, race_number, discipline, race_category,
            distance_m, track_type, terrain_label, penetrometer,
            declared_runners_count, conditions_text, race_status,
            race_duration_s, race_status_category
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (meeting_id, race_number) DO NOTHING;
        """,
        (
            meeting_id, race_number, discipline, race_category,
            distance_m, track_type, terrain_label, penetrometer_value,
            declared_runners, conditions, race_status,
            race_duration_s, race_status_category
        ),
    )

def ingest_programme_for_date(date_code: str):
    """
    Main Orchestrator function.
    Downloads the full program and performs a hierarchical insert (Program -> Meeting -> Race)
    within a single atomic database transaction.
    """
    logger = logging.getLogger("ProgramIngest")
    logger.info("Starting PROGRAMME ingestion for date=%s", date_code)

    try:
        data = fetch_programme_json(date_code)
    except Exception:
        logger.error("Skipping date %s due to API failure.", date_code)
        return

    programme = data.get("programme") or {}
    
    try:
        program_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    except ValueError:
        ts = programme.get("date")
        program_date = dt.datetime.fromtimestamp(ts / 1000).date()
    
    conn = get_db_connection()
    try:
        with conn: # Begins atomic transaction
            with conn.cursor() as cur:
                program_id = insert_daily_program(cur, program_date)
                reunions = programme.get("reunions", [])
                logger.info("Found %d meetings.", len(reunions))
                
                count_races = 0
                for reunion in reunions:
                    meeting_id = insert_race_meeting(cur, program_id, reunion)
                    courses = reunion.get("courses", [])
                    for course in courses:
                        # Business Rule: Filter only Trot races (ATTELE/MONTE)
                        discipline = course.get("discipline", "").upper()
                        if discipline in ["ATTELE", "MONTE"]:
                            insert_race(cur, meeting_id, course)
                            count_races += 1
                
                logger.info("Ingested %d trot races for date %s", count_races, program_date)
    finally:
        conn.close()

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_programme_for_date(args.date)