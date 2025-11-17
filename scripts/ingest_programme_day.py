"""
Ingest PMU programme JSON (JSON 1) for a given day
into PostgreSQL (Supabase) tables:

- daily_program
- race_meeting
- race

Usage:
    python ingest_programme_day.py --date 05112025
"""

import argparse
import datetime as dt
import json
import logging
import os

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv()

PROGRAMME_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{date_code}"
)


def setup_logging() -> None:
    """Configure basic logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_db_connection():
    """
    Create a PostgreSQL connection using the DB_URL environment variable.

    Example:
        export DB_URL="postgresql://USER:PASSWORD@HOST:PORT/postgres"
    """
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL environment variable is not set")
    return psycopg2.connect(db_url)


def fetch_programme_json(date_code: str) -> dict:
    """
    Fetch the programme JSON for a given PMU date code (e.g. '05112025').

    Returns the parsed JSON as a Python dict.
    """
    url = PROGRAMME_URL_TEMPLATE.format(date_code=date_code)
    logging.info("Fetching programme JSON from %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data


def convert_program_timestamp_to_date(ms_timestamp: int) -> dt.date:
    """
    Convert PMU programme timestamp in milliseconds to a Python date.

    The 'programme.date' field is a timestamp in milliseconds since epoch.
    """
    # Using UTC since we only care about the calendar day.
    return dt.datetime.utcfromtimestamp(ms_timestamp / 1000).date()


def upsert_daily_program(cur, program_date: dt.date) -> int:
    """
    Insert or update a row in daily_program for the given date.

    Returns the program_id.
    """
    logging.info("Upserting daily_program for date %s", program_date)

    cur.execute(
        """
        INSERT INTO daily_program (program_date)
        VALUES (%s)
        ON CONFLICT (program_date)
        DO UPDATE SET program_date = EXCLUDED.program_date
        RETURNING program_id;
        """,
        (program_date,),
    )
    program_id = cur.fetchone()[0]
    return program_id


def upsert_race_meeting(cur, program_id: int, reunion: dict) -> int:
    """
    Insert or update a race_meeting row based on programme JSON reunion object.

    Returns meeting_id.
    """
    num_officiel = reunion.get("numOfficiel")
    meeting_type = reunion.get("nature")
    racetrack_code = (
        (reunion.get("hippodrome") or {}).get("code")
        if reunion.get("hippodrome")
        else None
    )
    meteo = reunion.get("meteo") or {}
    temp = meteo.get("temperature")
    wind = meteo.get("directionVent")

    logging.info(
        "Upserting race_meeting (program_id=%s, meeting_number=%s)",
        program_id,
        num_officiel,
    )

    cur.execute(
        """
        INSERT INTO race_meeting (
            program_id,
            meeting_number,
            meeting_type,
            racetrack_code,
            weather_temperature,
            weather_wind
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (program_id, meeting_number)
        DO UPDATE SET
            meeting_type = EXCLUDED.meeting_type,
            racetrack_code = EXCLUDED.racetrack_code,
            weather_temperature = EXCLUDED.weather_temperature,
            weather_wind = EXCLUDED.weather_wind
        RETURNING meeting_id;
        """,
        (program_id, num_officiel, meeting_type, racetrack_code, temp, wind),
    )
    meeting_id = cur.fetchone()[0]
    return meeting_id


def upsert_race(cur, meeting_id: int, course: dict) -> int:
    """
    Insert or update a race row based on programme JSON course object.

    Returns race_id.
    """
    race_number = course.get("numOrdre") or course.get("numExterne") or course.get(
        "numCourse"
    )

    discipline = course.get("discipline")
    race_category = course.get("categorieParticularite")
    age_condition = course.get("conditionAge")
    distance_m = course.get("distance")
    track_type = course.get("typePiste")

    penetrometre = course.get("penetrometre") or {}
    raw_penetrometer_value = penetrometre.get("valeurMesure")
    terrain_label = penetrometre.get("intitule")

    penetrometer_value = None
    if raw_penetrometer_value is not None:
        # Some values come as strings with comma (e.g. "4,2").
        # We normalize them to a float with dot (4.2).
        try:
            if isinstance(raw_penetrometer_value, str):
                raw_norm = raw_penetrometer_value.replace(",", ".")
            else:
                raw_norm = str(raw_penetrometer_value)
            penetrometer_value = float(raw_norm)
        except (ValueError, TypeError):
            logging.warning(
                "Could not parse penetrometer value %r for meeting_id=%s, race_number=%s",
                raw_penetrometer_value,
                meeting_id,
                course.get("numOrdre") or course.get("numExterne") or course.get("numCourse"),
            )
            penetrometer_value = None
            

    declared_runners_count = course.get("nombreDeclaresPartants")
    conditions_text = course.get("conditions")
    race_status = course.get("statut")
    race_status_category = course.get("categorieStatut")

    finish_order = course.get("ordreArrivee")
    # Store finish_order as JSONB; psycopg2 will pass it as text and PostgreSQL will cast.
    finish_order_raw = json.dumps(finish_order) if finish_order is not None else None

    duration_raw = course.get("dureeCourse")
    # Based on PMU, dureeCourse seems to be in milliseconds (e.g. 228770).
    # We store it as integer seconds.
    race_duration_s = None
    if duration_raw is not None:
        try:
            race_duration_s = int(duration_raw) // 1000
        except (ValueError, TypeError):
            race_duration_s = None

    logging.info(
        "Upserting race (meeting_id=%s, race_number=%s)", meeting_id, race_number
    )

    cur.execute(
        """
        INSERT INTO race (
            meeting_id,
            race_number,
            discipline,
            race_category,
            age_condition,
            distance_m,
            track_type,
            terrain_label,
            penetrometer,
            declared_runners_count,
            conditions_text,
            race_status,
            finish_order_raw,
            race_duration_s,
            race_status_category
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (meeting_id, race_number)
        DO UPDATE SET
            discipline = EXCLUDED.discipline,
            race_category = EXCLUDED.race_category,
            age_condition = EXCLUDED.age_condition,
            distance_m = EXCLUDED.distance_m,
            track_type = EXCLUDED.track_type,
            terrain_label = EXCLUDED.terrain_label,
            penetrometer = EXCLUDED.penetrometer,
            declared_runners_count = EXCLUDED.declared_runners_count,
            conditions_text = EXCLUDED.conditions_text,
            race_status = EXCLUDED.race_status,
            finish_order_raw = EXCLUDED.finish_order_raw,
            race_duration_s = EXCLUDED.race_duration_s,
            race_status_category = EXCLUDED.race_status_category
        RETURNING race_id;
        """,
        (
            meeting_id,
            race_number,
            discipline,
            race_category,
            age_condition,
            distance_m,
            track_type,
            terrain_label,
            penetrometer_value,
            declared_runners_count,
            conditions_text,
            race_status,
            finish_order_raw,
            race_duration_s,
            race_status_category,
        ),
    )
    race_id = cur.fetchone()[0]
    return race_id


def ingest_programme_for_date(date_code: str) -> None:
    """
    Main orchestration function for ingesting JSON 1 for a given date code.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting ingestion for date_code=%s", date_code)

    data = fetch_programme_json(date_code)
    programme = data.get("programme") or {}
    programme_ts = programme.get("date")
    if programme_ts is None:
        raise ValueError("programme.date is missing in JSON response")

    program_date = convert_program_timestamp_to_date(programme_ts)
    reunions = programme.get("reunions") or []
    logger.info("Programme date resolved to %s, %d meetings found", program_date, len(reunions))

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                program_id = upsert_daily_program(cur, program_date)
                total_races = 0

                for reunion in reunions:
                    meeting_id = upsert_race_meeting(cur, program_id, reunion)
                    courses = reunion.get("courses") or []
                    for course in courses:
                        upsert_race(cur, meeting_id, course)
                        total_races += 1

        logger.info(
            "Ingestion completed for date %s: %d meetings, %d races",
            program_date,
            len(reunions),
            total_races,
        )
    finally:
        conn.close()
        logger.info("Database connection closed")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest PMU programme (JSON 1) for a given PMU date code."
    )
    parser.add_argument(
        "--date",
        required=True,
        help="PMU date code (e.g. 05112025 for 05/11/2025)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    ingest_programme_for_date(args.date)
