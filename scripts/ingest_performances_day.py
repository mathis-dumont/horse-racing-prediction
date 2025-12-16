"""
Ingest PMU detailed performances (JSON 3) for a WHOLE day.

Scope: Horse -> Horse Race History.
Improvements:
- Connection Pooling (ThreadedConnectionPool).
- JSON Fallback on DB Failure.
- Robust Retry Logic.
"""

import argparse
import datetime as dt
import logging
import os
import sys
import json
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
PERF_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/performances-detaillees/pretty"
)
MAX_WORKERS = 10
FAILURES_DIR = "failures/performances"

# Globals
DB_POOL = None
# In-memory cache for Horse IDs to minimize DB lookups.
# Key: Horse Name, Value: Database ID.
HORSE_CACHE: Dict[str, int] = {}
# Mutex lock to ensure thread safety when writing to HORSE_CACHE.
CACHE_LOCK = threading.Lock()
logger = logging.getLogger(__name__)

class IngestStatus(Enum):
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"

def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

# --- Pooling ---
def init_db_pool():
    """
    Initializes the PostgreSQL ThreadedConnectionPool.
    Allocates enough connections to cover all worker threads plus a safety buffer.
    """
    global DB_POOL
    db_url = os.getenv("DB_URL")
    if not db_url: raise ValueError("DB_URL missing")
    DB_POOL = psycopg2.pool.ThreadedConnectionPool(1, MAX_WORKERS + 2, db_url)
    logger.info("DB Pool Initialized")

def close_db_pool():
    global DB_POOL
    if DB_POOL:
        DB_POOL.closeall()
        logger.info("DB Pool Closed")

def get_pooled_connection():
    return DB_POOL.getconn()

def release_pooled_connection(conn):
    if DB_POOL and conn: DB_POOL.putconn(conn)

# --- Fallback ---
def save_failed_json(data, date_code, meeting, race):
    """
    Persists raw JSON data to disk upon ingestion failure.
    Enables post-mortem debugging or manual re-ingestion without data loss.
    """
    try:
        os.makedirs(FAILURES_DIR, exist_ok=True)
        filename = f"{FAILURES_DIR}/{date_code}_R{meeting}_C{race}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.warning(f"Fallback: Saved failed JSON to {filename}")
    except Exception as e:
        logger.error(f"Critical: Failed to save fallback JSON: {e}")

# --- Logic ---
def get_http_session():
    """
    Creates a requests Session with an exponential backoff retry strategy.
    Handles transient server errors (5xx) and rate limiting (429).
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=3, backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    return session

def fetch_perf_json(session, date_code, meeting, race):
    url = PERF_URL_TEMPLATE.format(date=date_code, meeting=meeting, race=race)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        resp = session.get(url, headers=headers, timeout=20)
        if resp.status_code in [404, 204]: return {}, resp.status_code
        resp.raise_for_status()
        return resp.json(), 200
    except Exception as e:
        logger.warning("Network error R%sC%s: %s", meeting, race, e)
        return {}, 500

def get_horse_id_thread_safe(cur, horse_name):
    """
    Thread-safe retrieval of Horse IDs using a 'Read-Through' cache strategy.
    1. Checks local memory (HORSE_CACHE) under lock.
    2. Checks DB if cache miss.
    3. Inserts into DB if missing, then updates cache.
    """
    if not horse_name: return None
    with CACHE_LOCK:
        if horse_name in HORSE_CACHE: return HORSE_CACHE[horse_name]
    
    cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (horse_name,))
    row = cur.fetchone()
    if row:
        with CACHE_LOCK: HORSE_CACHE[horse_name] = row[0]
        return row[0]
    
    try:
        cur.execute("INSERT INTO horse (horse_name) VALUES (%s) ON CONFLICT (horse_name) DO NOTHING RETURNING horse_id", (horse_name,))
        row = cur.fetchone()
        if row:
            with CACHE_LOCK: HORSE_CACHE[horse_name] = row[0]
            return row[0]
        # Race condition fallback
        cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (horse_name,))
        row = cur.fetchone()
        if row:
            with CACHE_LOCK: HORSE_CACHE[horse_name] = row[0]
            return row[0]
    except Exception:
        pass
    return None

def prepare_history_data(horse_id, history_item):
    """
    Parses and sanitizes a single performance history record.
    Returns a tuple suitable for bulk insertion or None if invalid.
    """
    if not horse_id: return None
    discipline = history_item.get("discipline", "").upper()
    if discipline not in ["ATTELE", "MONTE"]: return None
    
    race_date = None
    if history_item.get("date"):
        race_date = dt.datetime.utcfromtimestamp(history_item["date"] / 1000).date()
    
    subject = next((p for p in history_item.get("participants", []) if p.get("itsHim")), None)
    finish_place, finish_status, jockey_weight, draw, red_km, dist_travel = None, None, None, None, None, None
    
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
        horse_id, race_date, history_item.get("discipline"), history_item.get("distance"),
        history_item.get("allocation"), history_item.get("tempsDuPremier"),
        finish_place, finish_status, jockey_weight, draw, red_km, dist_travel
    )

def process_single_race(date_code, meeting_num, race_num):
    """
    Worker function: Handles the ETL process for one race.
    Fetches JSON, resolves foreign keys (Horse IDs), and performs a bulk insert
    via `execute_values` for performance optimization.
    """
    time.sleep(random.uniform(0.1, 0.3))
    
    session = get_http_session()
    data, status_code = fetch_perf_json(session, date_code, meeting_num, race_num)
    
    if status_code in [204, 404]:
        return 0, IngestStatus.SKIPPED
    if status_code >= 500:
        return 0, IngestStatus.FAILED

    participants = []
    if isinstance(data, dict): participants = data.get("participants", [])
    elif isinstance(data, list): participants = data
    
    if not participants: return 0, IngestStatus.SKIPPED

    conn = None
    inserted_count = 0
    try:
        conn = get_pooled_connection()
        with conn:
            with conn.cursor() as cur:
                batch_values = []
                for p in participants:
                    horse_name = p.get("nomCheval") or p.get("nom")
                    horse_id = get_horse_id_thread_safe(cur, horse_name)
                    if not horse_id: continue
                    
                    for h in p.get("coursesCourues", []):
                        row_data = prepare_history_data(horse_id, h)
                        if row_data: batch_values.append(row_data)

                if batch_values:
                    # Execute bulk insert to reduce network round-trips
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
        return inserted_count, IngestStatus.SUCCESS
        
    except Exception as e:
        logger.error("DB Error R%sC%s: %s", meeting_num, race_num, e)
        if conn: conn.rollback()
        save_failed_json(data, date_code, meeting_num, race_num)
        return 0, IngestStatus.FAILED
    finally:
        if conn: release_pooled_connection(conn)

def get_races_for_date(sql_date):
    conn = get_pooled_connection()
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
        release_pooled_connection(conn)

def ingest_performances_for_date(date_code):
    """
    Main Orchestrator:
    1. Initializes DB Connection Pool.
    2. Retrieves race list.
    3. Dispatches tasks to a ThreadPoolExecutor.
    4. Aggregates and logs final statistics.
    """
    try:
        sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    except ValueError:
        logger.critical("Invalid date format: %s", date_code)
        sys.exit(1)

    init_db_pool() # START POOL

    try:
        logger.info("==================================================")
        logger.info("Starting PARALLEL PERFORMANCE Ingestion for: %s", date_code)
        logger.info("==================================================")

        races = get_races_for_date(sql_date)
        logger.info("Found %d races to process.", len(races))

        total_records, skipped_races, failed_races = 0, 0, 0
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_race = {
                executor.submit(process_single_race, date_code, m, r): (m, r)
                for m, r in races
            }

            for i, future in enumerate(as_completed(future_to_race), 1):
                meeting, race = future_to_race[future]
                try:
                    count, status = future.result()
                    if status == IngestStatus.SUCCESS: total_records += count
                    elif status == IngestStatus.SKIPPED: skipped_races += 1
                    elif status == IngestStatus.FAILED: failed_races += 1
                    
                    if i % 10 == 0:
                        logger.info("Progress: %d/%d. Skipped: %d.", i, len(races), skipped_races)

                except Exception as e:
                    logger.error("Thread Error R%sC%s: %s", meeting, race, e)
                    failed_races += 1

        logger.info("==================================================")
        logger.info("Ingestion Completed.")
        logger.info("Records: %d | Skipped: %d | Failed: %d", total_records, skipped_races, failed_races)
        logger.info("Total execution time: %.2f seconds", time.time() - start_time)
        logger.info("==================================================")
    
    finally:
        close_db_pool() # CLOSE POOL

if __name__ == "__main__":
    setup_logging(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    ingest_performances_for_date(args.date)