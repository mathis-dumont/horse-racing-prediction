"""
Ingest horse_race_history from PMU JSON (JSON 3)
Ensures foreign key consistency with the horse table.

Usage:
    python ingest_horse_history.py --date 05112025 --meeting 1 --race 1
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

load_dotenv("../.env")

PERFORMANCE_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/performances-detaillees/pretty"
)

missing_horse_counter = 0

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

def fetch_performance_json(date: str):
    url = PERFORMANCE_URL_TEMPLATE.format(date=date)
    logging.info("Fetching performance JSON from %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()

def safe_get(obj, path, default=None):
    keys = path.split(".")
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur

def safe_int(value, default=None):
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_float(value, default=None):
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def get_or_create_horse(cur, horse_name):
    """Ensure the horse exists in the horse table and return horse_id."""
    global missing_horse_counter
    if not horse_name:
        missing_horse_counter += 1
        horse_name = f"Unknown_{missing_horse_counter}"
        logging.warning("Horse name missing. Using placeholder: %s", horse_name)

    cur.execute(
        "INSERT INTO horse (horse_name) VALUES (%s) ON CONFLICT (horse_name) DO NOTHING RETURNING horse_id",
        (horse_name,)
    )
    row = cur.fetchone()
    if row:
        return row[0]

    # Fetch existing horse_id
    cur.execute("SELECT horse_id FROM horse WHERE horse_name=%s", (horse_name,))
    return cur.fetchone()[0]

def insert_horse_race_history(cur, horse_id, course_json):
    participants = course_json.get("participants", [])
    course_date_ts = course_json.get("date")
    course_date = dt.datetime.fromtimestamp(course_date_ts / 1000, dt.timezone.utc).date() if course_date_ts else None

    discipline = course_json.get("discipline")
    prize_money = safe_float(course_json.get("allocation"))
    distance_m = safe_int(course_json.get("distance"))
    first_place_time_s = safe_int(course_json.get("tempsDuPremier"))

    for hp in participants:
        finish_place = safe_int(safe_get(hp, "place.place"))
        finish_status = safe_get(hp, "place.statusArrivee")
        jockey_weight = safe_float(hp.get("poidsJockey"))
        draw_number = safe_int(hp.get("corde"))
        reduction_km = safe_float(hp.get("reductionKilometrique"))
        distance_traveled_m = safe_int(hp.get("distanceParcourue"))

        cur.execute(
            """
            INSERT INTO horse_race_history (
                horse_id, race_date, discipline, distance_m,
                prize_money, first_place_time_s,
                finish_place, finish_status,
                jockey_weight, draw_number,
                reduction_km, distance_traveled_m
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (horse_id, race_date, discipline, distance_m)
            DO UPDATE SET
                prize_money = EXCLUDED.prize_money,
                first_place_time_s = EXCLUDED.first_place_time_s,
                finish_place = EXCLUDED.finish_place,
                finish_status = EXCLUDED.finish_status,
                jockey_weight = EXCLUDED.jockey_weight,
                draw_number = EXCLUDED.draw_number,
                reduction_km = EXCLUDED.reduction_km,
                distance_traveled_m = EXCLUDED.distance_traveled_m
            """,
            (
                horse_id, course_date, discipline, distance_m,
                prize_money, first_place_time_s,
                finish_place, finish_status,
                jockey_weight, draw_number,
                reduction_km, distance_traveled_m
            )
        )

def ingest_horse_race_history_for_date(date: str):
    logger = logging.getLogger(__name__)
    logger.info("Starting ingestion of horse_race_history for date_code=%s", date)

    data = fetch_performance_json(date)
    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                participants_json = data.get("participants", [])
                logger.info("Found %d participants", len(participants_json))

                for p in participants_json:
                    horse_name = p.get("nomCheval") or p.get("nom")
                    horse_id = get_or_create_horse(cur, horse_name)

                    courses = p.get("coursesCourues", [])
                    for course_json in courses:
                        insert_horse_race_history(cur, horse_id, course_json)

    finally:
        conn.close()
        logger.info("Database connection closed")

def parse_args():
    parser = argparse.ArgumentParser(description="Ingest horse_race_history from PMU JSON for a given date.")
    parser.add_argument("--date", required=True, help="PMU date code (e.g., 05112025)")
    return parser.parse_args()

if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    ingest_horse_race_history_for_date(args.date)
