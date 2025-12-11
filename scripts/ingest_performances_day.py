"""
Ingest PMU detailed performances (JSON 3) for a WHOLE day.
Scope: Horse -> Horse Race History.

Logic:
    - Queries DB to find all races for the given date.
    - Iterates over each race to fetch detailed performances.
    - Ensures horse exists (creates if not).
    - Inserts history records into horse_race_history.
    - Uses ON CONFLICT DO NOTHING.

Usage:
    python scripts/ingest_performances_day.py --date 05112025
"""

import argparse
import datetime as dt
import logging
import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

PERF_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/performances-detaillees/pretty"
)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def get_db_connection():
    return psycopg2.connect(os.getenv("DB_URL"))

def get_races_for_date(cur, sql_date):
    """Retrieve (meeting_number, race_number) for a SQL date."""
    cur.execute(
        """
        SELECT rm.meeting_number, r.race_number
        FROM race r
        JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
        JOIN daily_program dp ON rm.program_id = dp.program_id
        WHERE dp.program_date = %s
        ORDER BY rm.meeting_number, r.race_number;
        """,
        (sql_date,)
    )
    return cur.fetchall()

def fetch_perf_json(date_code, meeting, race):
    url = PERF_URL_TEMPLATE.format(date=date_code, meeting=meeting, race=race)
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error("Failed to fetch performances for %s: %s", url, e)
        return {}

def get_or_create_horse(cur, horse_name):
    """Get horse_id, creating it if necessary."""
    if not horse_name:
        return None
    
    cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (horse_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    
    cur.execute(
        "INSERT INTO horse (horse_name) VALUES (%s) ON CONFLICT (horse_name) DO NOTHING RETURNING horse_id",
        (horse_name,)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    
    # Retry fetch if race condition occurred
    cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (horse_name,))
    row = cur.fetchone()
    return row[0] if row else None

def insert_history(cur, horse_id, c):
    """Insert a single history line."""
    if not horse_id: return

    # Parse date
    race_date = None
    if c.get("date"):
        race_date = dt.datetime.utcfromtimestamp(c["date"] / 1000).date()
    
    # Parse participant info inside the history
    # The JSON structure implies 'participants' list inside a 'courseCourue'
    # We look for 'itsHim': true to find the subject horse
    subject = next((p for p in c.get("participants", []) if p.get("itsHim")), None)
    
    finish_place = None
    finish_status = None
    jockey_weight = None
    draw = None
    red_km = None
    dist_travel = None
    
    if subject:
        # Check structure: subject['place'] is usually a dict { 'place': X, 'statusArrivee': ... }
        place_obj = subject.get("place")
        if isinstance(place_obj, dict):
            finish_place = place_obj.get("place")
            finish_status = place_obj.get("statusArrivee")
        
        jockey_weight = subject.get("poidsJockey")
        draw = subject.get("corde")
        red_km = subject.get("reductionKilometrique")
        dist_travel = subject.get("distanceParcourue")

    cur.execute(
        """
        INSERT INTO horse_race_history (
            horse_id, race_date, discipline, distance_m,
            prize_money, first_place_time_s,
            finish_place, finish_status, jockey_weight,
            draw_number, reduction_km, distance_traveled_m
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (horse_id, race_date, discipline, distance_m) DO NOTHING;
        """,
        (
            horse_id, race_date, c.get("discipline"), c.get("distance"),
            c.get("allocation"), c.get("tempsDuPremier"),
            finish_place, finish_status, jockey_weight,
            draw, red_km, dist_travel
        )
    )

def ingest_performances_for_date(date_code):
    logger = logging.getLogger(__name__)
    sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    logger.info("Starting PERFORMANCES ingestion for %s", date_code)

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                races = get_races_for_date(cur, sql_date)
                logger.info("Found %d races to scan for history", len(races))

                for meeting_num, race_num in races:
                    data = fetch_perf_json(date_code, meeting_num, race_num)
                    
                    # Some endpoints return list directly, some dict with 'participants'
                    participants = []
                    if isinstance(data, dict):
                        participants = data.get("participants", [])
                    elif isinstance(data, list):
                        participants = data

                    for p in participants:
                        horse_name = p.get("nomCheval") or p.get("nom")
                        horse_id = get_or_create_horse(cur, horse_name)
                        
                        history_list = p.get("coursesCourues", [])
                        for h in history_list:
                            insert_history(cur, horse_id, h)
                            
    finally:
        conn.close()

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_performances_for_date(args.date)