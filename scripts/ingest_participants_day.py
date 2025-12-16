"""
Ingest PMU participants (JSON 2) for a WHOLE day.
Scope: Horse -> Race Participant.
Status: STABLE & ROBUST version.
- No global cache for dynamic data (prevents Foreign Key errors during rollbacks).
- Retry logic for DB Deadlocks.
- FIXED: Connection Pool Exhaustion by reusing cursors for lookups.
"""

import argparse
import datetime as dt
import logging
import os
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
from psycopg2 import pool, errors
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from enum import Enum
import threading

load_dotenv()

# --- Configuration ---
PARTICIPANTS_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/participants"
)

# --- MAPPINGS ---
# Domain-specific mappings to normalize API status codes to database constraints.
INCIDENT_MAP = {
    "DISQUALIFIE_POUR_ALLURE_IRREGULIERE": "DAI",
    "DISQUALIFIE_POTEAU_GALOP": "DPG",
    "NON_PARTANT": "NP",
    "DISTANCE": "DIST",
    "ARRETE": "ARR",
    "TOMBE": "T",
    "RESTE_AU_POTEAU": "RP",
    "DISQUALIFIE": "DAI",
    "RETROGRADE": "RET"
}

SHOE_MAP = {
    "DEFERRE_ANTERIEURS_POSTERIEURS": "D4",
    "PROTEGE_ANTERIEURS_DEFERRRE_POSTERIEURS": "PADP",
    "DEFERRE_POSTERIEURS": "DP",
    "DEFERRE_ANTERIEURS": "DA",
    "PROTEGE_ANTERIEURS": "PA",
    "PROTEGE_ANTERIEURS_POSTERIEURS": "P4",
    "DEFERRE_ANTERIEURS_PROTEGE_POSTERIEURS": "DAPP",
    "REFERRE_ANTERIEURS_POSTERIEURS": "R4",
    "PROTEGE_POSTERIEURS": "PP"
}

MAX_WORKERS = 10
FAILURES_DIR = "failures/participants"
DB_POOL = None

# --- MANUAL CACHES ---
# Thread-safe manual caching strategies for static lookup data.
# Replaces @lru_cache to allow passing non-hashable 'cursor' objects 
# and to ensure atomic updates across threads.
SHOEING_CACHE = {}
INCIDENT_CACHE = {}
# Mutex lock to synchronize writes to the cache and prevent race conditions on lookup inserts.
CACHE_LOCK = threading.Lock()

class IngestStatus(Enum):
    SUCCESS = "SUCCESS"
    SKIPPED_NO_CONTENT = "SKIPPED_NO_CONTENT"
    FAILED = "FAILED"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def init_db_pool():
    """
    Initializes a ThreadedConnectionPool.
    Sizing strategy: 1 connection per worker + small buffer.
    Ensures strict 1:1 mapping between threads and active DB sessions.
    """
    global DB_POOL
    db_url = os.getenv("DB_URL")
    if not db_url: raise ValueError("DB_URL not set")
    # Buffer set to +2 to handle transient overhead.
    DB_POOL = psycopg2.pool.ThreadedConnectionPool(1, MAX_WORKERS + 2, db_url)
    logging.info("DB Pool Initialized")

def close_db_pool():
    global DB_POOL
    if DB_POOL:
        DB_POOL.closeall()
        logging.info("DB Pool Closed")

def get_pooled_connection():
    return DB_POOL.getconn()

def release_pooled_connection(conn):
    if DB_POOL and conn: DB_POOL.putconn(conn)

def save_failed_json(data, date_code, meeting, race):
    """
    Fallback mechanism: serializes raw API data to disk upon critical DB failures
    to allow for manual debugging or later reprocessing.
    """
    try:
        os.makedirs(FAILURES_DIR, exist_ok=True)
        filename = f"{FAILURES_DIR}/{date_code}_R{meeting}_C{race}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.warning(f"Fallback: JSON saved to {filename}")
    except Exception as e:
        logging.error(f"Critical: Failed to save fallback JSON: {e}")

def get_http_session():
    """
    Configures a requests Session with an HTTPAdapter.
    Implements automatic retries with backoff for transient network errors (5xx, 429).
    """
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504, 429])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def fetch_participants_json(session, date_code, meeting_num, race_num):
    url = PARTICIPANTS_URL_TEMPLATE.format(date=date_code, meeting=meeting_num, race=race_num)
    headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept": "application/json" }
    try:
        resp = session.get(url, headers=headers, timeout=10)
        if resp.status_code in [404, 204]: return [], resp.status_code
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict): return data.get("participants", []), 200
        return (data, 200) if isinstance(data, list) else ([], 200)
    except Exception as e:
        logging.warning(f"Failed to fetch R{meeting_num}C{race_num}: {e}")
        return None, 500

def safe_get(obj, path, default=None):
    keys = path.split(".")
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur: return default
        cur = cur[k]
    return cur

def truncate(text, length):
    if text and isinstance(text, str) and len(text) > length: return text[:length]
    return text

def to_euros(cents):
    if cents is None: return None
    try:
        return float(cents) / 100.0
    except (ValueError, TypeError):
        return None

# --- HELPERS DB ---

def get_or_create_horse(cur, p):
    """
    Idempotent upsert logic for Horse entities.
    Attempts INSERT first; handles uniqueness via ON CONFLICT DO NOTHING.
    Falls back to SELECT if the record already existed.
    """
    name = p.get("nom")
    if not name: return None
    
    age = p.get("age")
    birth_year = (dt.date.today().year - int(age)) if age else None
    raw_sex = p.get("sexe")
    clean_sex = raw_sex[0].upper() if raw_sex else None
    
    cur.execute(
        "INSERT INTO horse (horse_name, sex, birth_year) VALUES (%s, %s, %s) "
        "ON CONFLICT (horse_name) DO NOTHING RETURNING horse_id;",
        (name, clean_sex, birth_year)
    )
    row = cur.fetchone()
    if row: return row[0]
    
    cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (name,))
    res = cur.fetchone()
    return res[0] if res else None

def get_or_create_actor(cur, name):
    clean_name = truncate(name, 100)
    if not clean_name: return None
    
    cur.execute(
        "INSERT INTO racing_actor (actor_name) VALUES (%s) "
        "ON CONFLICT (actor_name) DO NOTHING RETURNING actor_id;",
        (clean_name,)
    )
    row = cur.fetchone()
    if row: return row[0]
    
    cur.execute("SELECT actor_id FROM racing_actor WHERE actor_name = %s", (clean_name,))
    res = cur.fetchone()
    return res[0] if res else None

# --- LOCAL CACHE & CURSOR REUSE (POOL EXHAUSTION FIX) ---

def get_or_create_shoeing(cur, code):
    """
    Optimized lookup using Double-Checked Locking.
    1. Checks global dictionary cache (Fast Path).
    2. Acquires lock to prevent redundant DB hits by concurrent threads.
    3. Reuses the active cursor (passed arg) to execute SQL, avoiding pool starvation.
    """
    if not code: return None
    
    # Fast path: Read check
    if code in SHOEING_CACHE:
        return SHOEING_CACHE[code]
    
    # Critical Section: Prevent multiple threads from inserting the same lookup
    with CACHE_LOCK:
        # Double-check after acquiring lock
        if code in SHOEING_CACHE:
            return SHOEING_CACHE[code]

        # Database Execution (Reusing existing cursor)
        cur.execute(
            "INSERT INTO lookup_shoeing (code) VALUES (%s) "
            "ON CONFLICT (code) DO NOTHING RETURNING shoeing_id;", (code,)
        )
        row = cur.fetchone()
        
        if row:
            s_id = row[0]
        else:
            cur.execute("SELECT shoeing_id FROM lookup_shoeing WHERE code = %s", (code,))
            res = cur.fetchone()
            s_id = res[0] if res else None

        if s_id:
            SHOEING_CACHE[code] = s_id
        
        return s_id

def get_or_create_incident(cur, code):
    """
    Identical optimization pattern to shoeing lookup:
    Combines memory caching, thread locking, and cursor reuse.
    """
    if not code: return None
    
    if code in INCIDENT_CACHE:
        return INCIDENT_CACHE[code]
    
    with CACHE_LOCK:
        if code in INCIDENT_CACHE:
            return INCIDENT_CACHE[code]

        cur.execute(
            "INSERT INTO lookup_incident (code) VALUES (%s) "
            "ON CONFLICT (code) DO NOTHING RETURNING incident_id;", (code,)
        )
        row = cur.fetchone()
        if row:
            i_id = row[0]
        else:
            cur.execute("SELECT incident_id FROM lookup_incident WHERE code = %s", (code,))
            res = cur.fetchone()
            i_id = res[0] if res else None
        
        if i_id:
            INCIDENT_CACHE[code] = i_id
        
        return i_id

def insert_participant(cur, race_id, p):
    """
    Main ingestion logic for a single participant.
    Aggregates Foreign Keys using helper functions and performs the final insertion.
    Handles data cleaning (Euro conversion, enum mapping) prior to SQL execution.
    """
    p_num = p.get("numPmu")
    
    # Mappings
    raw_inc = p.get("incident")
    clean_inc = INCIDENT_MAP.get(raw_inc, raw_inc[:20] if raw_inc else None)
    
    raw_shoe = p.get("deferre")
    clean_shoe = SHOE_MAP.get(raw_shoe, raw_shoe[:10] if raw_shoe else None)

    # Foreign Key Retrieval
    horse_id = get_or_create_horse(cur, p)
    if not horse_id: return
    
    trainer_id = get_or_create_actor(cur, p.get("entraineur"))
    driver_id = get_or_create_actor(cur, p.get("driver"))
    
    # Optimization: Passing 'cur' to avoid fetching new connections from the pool
    incident_id = get_or_create_incident(cur, clean_inc)
    shoeing_id = get_or_create_shoeing(cur, clean_shoe)

    # Data Conversion
    raw_sex = p.get("sexe")
    clean_sex = raw_sex[0].upper() if raw_sex else None
    
    raw_red_km = p.get("reductionKilometrique")
    try:
        clean_red_km = float(raw_red_km) if raw_red_km is not None else None
    except:
        clean_red_km = None
    
    career_winnings = to_euros(safe_get(p, "gainsParticipant.gainsCarriere"))

    cur.execute(
        """
        INSERT INTO race_participant (
            race_id, horse_id, pmu_number, age, sex,
            trainer_id, driver_jockey_id, shoeing_id, incident_id,
            career_races_count, career_winnings, reference_odds, live_odds,
            raw_performance_string, trainer_advice, finish_rank,
            time_achieved_s, reduction_km
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (race_id, pmu_number) DO NOTHING;
        """,
        (
            race_id, horse_id, p_num, p.get("age"), clean_sex,
            trainer_id, driver_id, shoeing_id, incident_id,
            p.get("nombreCourses"), career_winnings,
            safe_get(p, "dernierRapportReference.rapport"), safe_get(p, "dernierRapportDirect.rapport"),
            p.get("musique"), p.get("avisEntraineur"), p.get("ordreArrivee"),
            p.get("tempsObtenu"), clean_red_km
        )
    )

def process_single_race_participants(date_code, race_id, meeting_num, race_num):
    """
    Worker function executed by ThreadPoolExecutor.
    Manages the lifecycle of a single race ingestion:
    1. Fetches JSON data.
    2. Acquires a DB connection.
    3. Executes inserts within an atomic transaction.
    4. Implements explicit retry logic for PostgreSQL Deadlocks.
    """
    time.sleep(random.uniform(0.1, 0.3))
    session = get_http_session()
    participants, status_code = fetch_participants_json(session, date_code, meeting_num, race_num)
    
    if status_code in [204, 404]: return 0, IngestStatus.SKIPPED_NO_CONTENT
    if participants is None: return 0, IngestStatus.FAILED

    conn = None
    # --- RETRY LOGIC (DB Deadlock Handling) ---
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_pooled_connection()
            with conn: # Start atomic transaction block
                with conn.cursor() as cur:
                    for p in participants:
                        insert_participant(cur, race_id, p)
            return len(participants), IngestStatus.SUCCESS
            
        except psycopg2.errors.DeadlockDetected:
            # Explicit Rollback for Deadlocks, followed by retry with jitter
            if conn: conn.rollback()
            sleep_time = random.uniform(0.5, 1.5)
            time.sleep(sleep_time)
            continue
            
        except Exception as e:
            # Handle non-retryable errors (Network, SQL Syntax, Data Integrity)
            logging.error(f"DB Error R{meeting_num}C{race_num}: {e}")
            if conn: conn.rollback()
            save_failed_json(participants, date_code, meeting_num, race_num)
            return 0, IngestStatus.FAILED
            
        finally:
            if conn: release_pooled_connection(conn)
            conn = None

    return 0, IngestStatus.FAILED

def get_races_for_date(sql_date):
    conn = get_pooled_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.race_id, rm.meeting_number, r.race_number
                FROM race r
                JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
                JOIN daily_program dp ON rm.program_id = dp.program_id
                WHERE dp.program_date = %s
                AND r.discipline IN ('ATTELE', 'MONTE')
                ORDER BY rm.meeting_number, r.race_number;
                """,
                (sql_date,)
            )
            return cur.fetchall()
    finally:
        release_pooled_connection(conn)

def ingest_participants_for_date(date_code):
    """
    Orchestrator function.
    Sets up the thread pool and maps race ingestion tasks to workers.
    Aggregates success/failure statistics upon completion.
    """
    logger = logging.getLogger("PartIngest")
    sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    init_db_pool()
    try:
        logger.info(f"Starting PARALLEL PARTICIPANTS ingestion for {date_code}")
        races = get_races_for_date(sql_date)
        logger.info(f"Processing {len(races)} races.")

        total_inserted = 0
        total_skipped = 0
        total_failed = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_race = {
                executor.submit(process_single_race_participants, date_code, r_id, m, r): (m, r)
                for r_id, m, r in races
            }

            for future in as_completed(future_to_race):
                m, r = future_to_race[future]
                try:
                    count, status = future.result()
                    if status == IngestStatus.SUCCESS: total_inserted += count
                    elif status == IngestStatus.SKIPPED_NO_CONTENT: total_skipped += 1
                    else: total_failed += 1
                except Exception as e:
                    logger.error(f"Exception for R{m}C{r}: {e}")
                    total_failed += 1
        logger.info(f"Ingestion Completed. Records: {total_inserted} | Skipped: {total_skipped} | Failed: {total_failed}")
    finally:
        close_db_pool()

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_participants_for_date(args.date)