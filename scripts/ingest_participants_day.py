"""
Ingest PMU participants (JSON 2) for a WHOLE day.
Scope: Horse -> Race Participant.
Mode: Parallel Execution (Multithreading) with Throttling.

Fetches participant lists for all races and populates 'horse' and 'race_participant' tables.
"""

import argparse
import datetime as dt
import logging
import os
import time
import requests
import psycopg2
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

# --- Configuration ---
PARTICIPANTS_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/participants"
)
MAX_WORKERS = 12
REQUEST_DELAY = 0.050  # 50ms

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def get_db_connection():
    return psycopg2.connect(os.getenv("DB_URL"))

def fetch_participants_json(date_code, meeting_num, race_num):
    """
    Fetches participants list with browser-like headers.
    """
    url = PARTICIPANTS_URL_TEMPLATE.format(date=date_code, meeting=meeting_num, race=race_num)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.pmu.fr/",
        "Connection": "keep-alive"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        
        data = resp.json()
        if isinstance(data, dict):
            return data.get("participants", [])
        return data if isinstance(data, list) else []
        
    except Exception as e:
        logging.error(f"Network error fetching {url}: {e}")
        return []

def safe_get(obj, path, default=None):
    """Utility to traverse nested dictionaries safely."""
    keys = path.split(".")
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def get_or_create_horse(cur, p):
    """Insert horse if not exists, return horse_id."""
    name = p.get("nom")
    if not name: return None
    
    age = p.get("age")
    birth_year = (dt.date.today().year - int(age)) if age else None
    
    # Attempt Insert
    cur.execute(
        """
        INSERT INTO horse (horse_name, sex, birth_year)
        VALUES (%s, %s, %s)
        ON CONFLICT (horse_name) DO NOTHING
        RETURNING horse_id;
        """,
        (name, p.get("sexe"), birth_year)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    
    # Fallback Select
    cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (name,))
    res = cur.fetchone()
    return res[0] if res else None

def insert_participant(cur, race_id, horse_id, p):
    """Insert race_participant record."""
    if not horse_id: return

    cur.execute(
        """
        INSERT INTO race_participant (
            race_id, horse_id, pmu_number, age, sex,
            trainer_name, driver_jockey_name, shoeing_status,
            career_races_count, career_winnings, reference_odds, live_odds,
            raw_performance_string, trainer_advice, finish_rank,
            incident, time_achieved_s, reduction_km, post_race_comment
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (race_id, pmu_number) DO NOTHING;
        """,
        (
            race_id, horse_id, p.get("numPmu"), p.get("age"), p.get("sexe"),
            p.get("entraineur"), p.get("driver"), p.get("deferre"),
            p.get("nombreCourses"), safe_get(p, "gainsParticipant.gainsCarriere"),
            safe_get(p, "dernierRapportReference.rapport"), safe_get(p, "dernierRapportDirect.rapport"),
            p.get("musique"), p.get("avisEntraineur"), p.get("ordreArrivee"),
            p.get("incident"), p.get("tempsObtenu"), p.get("reductionKilometrique"),
            safe_get(p, "commentaireApresCourse.texte")
        )
    )

def process_single_race_participants(date_code, race_id, meeting_num, race_num):
    """Worker: Handle one race's participants."""
    time.sleep(REQUEST_DELAY) # Throttling

    participants = fetch_participants_json(date_code, meeting_num, race_num)
    if not participants:
        return 0

    conn = get_db_connection()
    count = 0
    try:
        with conn:
            with conn.cursor() as cur:
                for p in participants:
                    horse_id = get_or_create_horse(cur, p)
                    insert_participant(cur, race_id, horse_id, p)
                    count += 1
    except Exception as e:
        logging.error(f"DB Error R{meeting_num}C{race_num}: {e}")
    finally:
        conn.close()
    return count

def get_races_for_date(sql_date):
    """Get all race IDs and codes for the date."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.race_id, rm.meeting_number, r.race_number
                FROM race r
                JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
                JOIN daily_program dp ON rm.program_id = dp.program_id
                WHERE dp.program_date = %s
                ORDER BY rm.meeting_number, r.race_number;
                """,
                (sql_date,)
            )
            return cur.fetchall()
    finally:
        conn.close()

def ingest_participants_for_date(date_code):
    logger = logging.getLogger("PartIngest")
    sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    logger.info(f"Starting PARALLEL PARTICIPANTS ingestion for {date_code}")

    races = get_races_for_date(sql_date)
    logger.info(f"Processing {len(races)} races.")

    total_inserted = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_race = {
            executor.submit(process_single_race_participants, date_code, r_id, m, r): (m, r)
            for r_id, m, r in races
        }

        for future in as_completed(future_to_race):
            m, r = future_to_race[future]
            try:
                count = future.result()
                total_inserted += count
            except Exception as e:
                logger.error(f"Exception for R{m}C{r}: {e}")

    logger.info(f"Ingestion Completed. Total participants processed: {total_inserted}")

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_participants_for_date(args.date)