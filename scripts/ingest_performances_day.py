"""
Ingest PMU detailed performances (JSON 3) for a WHOLE day.

Scope: Horse -> Horse Race History.
Mode: PARALLEL EXECUTION + BATCH INSERT PER RACE.
      - Uses ThreadPoolExecutor for concurrency.
      - Implements Thread-Safe Caching for Horse IDs.
      - Batch inserts history records per race to minimize round-trips.
"""

import argparse
import datetime as dt
import logging
import os
import sys
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any

import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
PERF_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/performances-detaillees/pretty"
)
MAX_WORKERS = 12        # Adjust based on DB connection limits

# --- Thread-Safe Globals ---
# Shared cache for Horse IDs to reduce DB SELECTs
HORSE_CACHE: Dict[str, int] = {}
# Lock to ensure thread-safe access/write to the cache
CACHE_LOCK = threading.Lock()

# Configure module-level logger
logger = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO) -> None:
    """Configures the logging format and level."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Reduce noise from connection libraries if needed
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_db_connection():
    """Establishes a new connection to the PostgreSQL database."""
    db_url = os.getenv("DB_URL")
    if not db_url:
        logger.critical("DB_URL environment variable is not set.")
        sys.exit(1)
    return psycopg2.connect(db_url)

def fetch_perf_json(date_code: str, meeting: int, race: int) -> Dict[str, Any]:
    """
    Fetches detailed performance history with browser-like headers.
    Handles 404 (Not Found) and 204 (No Content) gracefully.
    """
    url = PERF_URL_TEMPLATE.format(date=date_code, meeting=meeting, race=race)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.pmu.fr/",
        "Connection": "keep-alive"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        
        # 1. Resource does not exist
        if resp.status_code == 404:
            return {}
            
        # 2. No Content (HTTP 204) - Likely a foreign race without detailed history
        if resp.status_code == 204:
            logger.info("Skipping R%sC%s: HTTP 204 (No Content) - Likely foreign race.", meeting, race)
            return {}
            
        resp.raise_for_status()
        
        # 3. Extra safety: Empty body with 200 OK
        if not resp.content:
            return {}

        return resp.json()
        
    except requests.exceptions.JSONDecodeError:
        logger.warning("Invalid JSON content for R%sC%s (Status: %s)", meeting, race, resp.status_code)
        return {}
        
    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching R%sC%s: %s", meeting, race, e)
        return {}

def get_horse_id_thread_safe(cur: Any, horse_name: str) -> Optional[int]:
    """
    Retrieves the horse ID from the shared cache or database in a thread-safe manner.
    
    Args:
        cur: Database cursor (unique to the thread).
        horse_name: Name of the horse.
        
    Returns:
        The horse_id (int) or None.
    """
    if not horse_name:
        return None
    
    # 1. Check Shared Cache (with Lock)
    with CACHE_LOCK:
        if horse_name in HORSE_CACHE:
            return HORSE_CACHE[horse_name]
    
    # 2. Check Database (if not in cache)
    cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (horse_name,))
    row = cur.fetchone()
    
    if row:
        horse_id = row[0]
        # Update Cache
        with CACHE_LOCK:
            HORSE_CACHE[horse_name] = horse_id
        return horse_id
    
    # 3. Insert new Horse (if not found in DB)
    try:
        cur.execute(
            """
            INSERT INTO horse (horse_name) 
            VALUES (%s) 
            ON CONFLICT (horse_name) DO NOTHING 
            RETURNING horse_id
            """,
            (horse_name,)
        )
        row = cur.fetchone()
        
        if row:
            horse_id = row[0]
            with CACHE_LOCK:
                HORSE_CACHE[horse_name] = horse_id
            return horse_id
        
        # Fallback for concurrency race condition
        cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (horse_name,))
        row = cur.fetchone()
        if row:
            horse_id = row[0]
            with CACHE_LOCK:
                HORSE_CACHE[horse_name] = horse_id
            return horse_id
            
    except Exception as e:
        logger.error("Failed to get/create horse '%s': %s", horse_name, e)
        
    return None


def prepare_history_data(horse_id: int, history_item: Dict[str, Any]) -> Optional[Tuple]:
    """
    Transforms a 'courseCourue' JSON object into a tuple ready for SQL insertion.
    Pure data transformation, no I/O.
    """
    if not horse_id:
        return None

    race_date = None
    if history_item.get("date"):
        race_date = dt.datetime.utcfromtimestamp(history_item["date"] / 1000).date()
    
    # Identify the specific horse within the history participants list
    subject = next((p for p in history_item.get("participants", []) if p.get("itsHim")), None)
    
    finish_place = None
    finish_status = None
    jockey_weight = None
    draw = None
    red_km = None
    dist_travel = None
    
    if subject:
        place_obj = subject.get("place")
        if isinstance(place_obj, dict):
            finish_place = place_obj.get("place")
            finish_status = place_obj.get("statusArrivee")
            
        jockey_weight = subject.get("poidsJockey")
        draw = subject.get("corde")
        red_km = subject.get("reductionKilometrique")
        dist_travel = subject.get("distanceParcourue")

    return (
        horse_id, 
        race_date, 
        history_item.get("discipline"), 
        history_item.get("distance"),
        history_item.get("allocation"), 
        history_item.get("tempsDuPremier"),
        finish_place, 
        finish_status, 
        jockey_weight,
        draw, 
        red_km, 
        dist_travel
    )


def process_single_race(date_code: str, meeting_num: int, race_num: int) -> int:
    """
    Worker function: Handles the full workflow for a SINGLE race.
    
    1. Fetches JSON (Thread-safe).
    2. Transforms data.
    3. Opens a DB connection.
    4. Inserts data in batch.
    5. Closes connection.
    """
    # Throttling to respect API rate limits
    time.sleep(random.uniform(0.1, 0.3))

    # 1. Fetch Data
    data = fetch_perf_json(date_code, meeting_num, race_num)
    
    participants = []
    if isinstance(data, dict):
        participants = data.get("participants", [])
    elif isinstance(data, list):
        participants = data
    
    if not participants:
        return 0

    batch_values = []
    conn = get_db_connection()
    inserted_count = 0

    try:
        with conn:
            with conn.cursor() as cur:
                # 2. Data Preparation
                for p in participants:
                    horse_name = p.get("nomCheval") or p.get("nom")
                    # Use thread-safe helper
                    horse_id = get_horse_id_thread_safe(cur, horse_name)
                    
                    if not horse_id:
                        continue
                    
                    history_list = p.get("coursesCourues", [])
                    for h in history_list:
                        row_data = prepare_history_data(horse_id, h)
                        if row_data:
                            batch_values.append(row_data)

                # 3. Batch Insert
                if batch_values:
                    query = """
                        INSERT INTO horse_race_history (
                            horse_id, race_date, discipline, distance_m,
                            prize_money, first_place_time_s,
                            finish_place, finish_status, jockey_weight,
                            draw_number, reduction_km, distance_traveled_m
                        ) VALUES %s
                        ON CONFLICT (horse_id, race_date, discipline, distance_m) DO NOTHING
                    """
                    psycopg2.extras.execute_values(cur, query, batch_values)
                    inserted_count = len(batch_values)
                    
    except Exception as e:
        logger.error("DB Error processing R%sC%s: %s", meeting_num, race_num, e)
    finally:
        conn.close()
    
    return inserted_count


def get_races_for_date(sql_date: dt.date) -> List[Tuple[int, int]]:
    """Retrieves the list of races to process."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT rm.meeting_number, r.race_number
                FROM race r
                JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
                JOIN daily_program dp ON rm.program_id = dp.program_id
                WHERE dp.program_date = %s
                ORDER BY rm.meeting_number, r.race_number;
            """
            cur.execute(query, (sql_date,))
            return cur.fetchall()
    finally:
        conn.close()


def ingest_performances_for_date(date_code: str):
    """
    Main orchestration function using ThreadPoolExecutor.
    """
    try:
        sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    except ValueError:
        logger.critical("Invalid date format: %s. Expected DDMMYYYY.", date_code)
        sys.exit(1)

    logger.info("==================================================")
    logger.info("Starting PARALLEL PERFORMANCE Ingestion for: %s", date_code)
    logger.info("Max Workers: %d", MAX_WORKERS)
    logger.info("==================================================")

    # 1. Get Race List
    races = get_races_for_date(sql_date)
    logger.info("Found %d races to process.", len(races))

    if not races:
        logger.warning("No races found. Did you run ingest_programme_day.py?")
        return

    total_records = 0
    start_time = time.time()

    # 2. Parallel Processing
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_race = {
            executor.submit(process_single_race, date_code, m, r): (m, r)
            for m, r in races
        }

        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_race), 1):
            meeting, race = future_to_race[future]
            try:
                count = future.result()
                total_records += count
                
                # Optional: Verbose logging for debugging
                # logger.debug("R%sC%s: %d records.", meeting, race, count)
                
                if i % 10 == 0 or i == len(races):
                    elapsed = time.time() - start_time
                    logger.info(
                        "Progress: %d/%d races done. Records: %d. (%.2fs)", 
                        i, len(races), total_records, elapsed
                    )

            except Exception as e:
                logger.error("Exception in thread for R%sC%s: %s", meeting, race, e)

    logger.info("==================================================")
    logger.info("Ingestion Completed.")
    logger.info("Total history items inserted: %d", total_records)
    logger.info("Total execution time: %.2f seconds", time.time() - start_time)
    logger.info("==================================================")


if __name__ == "__main__":
    setup_logging(logging.INFO)
    
    parser = argparse.ArgumentParser(description="Ingest Horse Performance History (JSON 3) - Parallel.")
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    
    args = parser.parse_args()
    ingest_performances_for_date(args.date)