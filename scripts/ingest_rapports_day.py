"""
Ingest PMU betting reports (JSON 4) for a WHOLE day.
Scope: Race Bet -> Bet Report.
Improvements:
- Connection Pooling (ThreadedConnectionPool).
- JSON Fallback on DB Failure.
- Robust Retry Logic.
- DATA OPTIMIZATION: Maps bet types & Converts Cents to Euros.
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
from psycopg2 import pool
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from enum import Enum

load_dotenv()

RAPPORTS_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{date}/R{meeting}/C{race}/rapports-definitifs"
)

# --- OPTIMIZED MAPPINGS ---
# Maps verbose API bet codes to compact database identifiers.
# Reduces storage footprint and normalizes inconsistent API naming.
BET_TYPE_MAP = {
    "SIMPLE_GAGNANT": "SG",
    "SIMPLE_PLACE": "SP",
    "COUPLE_GAGNANT": "CG",
    "COUPLE_PLACE": "CP",
    "COUPLE_ORDRE": "CO",
    "TRIO": "TRIO",
    "TRIO_ORDRE": "TRIOO",
    "DEUX_SUR_QUATRE": "2S4",
    "MULTI": "MULTI",
    "MINI_MULTI": "MM",
    "TIERCE": "TIERCE",
    "QUARTE_PLUS": "QUARTE",
    "QUINTE_PLUS": "QUINTE",
    "PICK5": "PICK5",
    "SUPER_QUATRE": "SUP4"
}

MAX_WORKERS = 10
FAILURES_DIR = "failures/rapports"

DB_POOL = None

class IngestStatus(Enum):
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

# --- Pooling ---
def init_db_pool():
    """
    Initializes a ThreadedConnectionPool.
    Ensures thread safety for DB operations within the ThreadPoolExecutor.
    """
    global DB_POOL
    db_url = os.getenv("DB_URL")
    if not db_url: raise ValueError("DB_URL missing")
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

# --- Fallback ---
def save_failed_json(data, date_code, meeting, race):
    """
    Dumps raw API responses to disk when database transactions fail.
    Prevents data loss and allows for manual replay/debugging.
    """
    try:
        os.makedirs(FAILURES_DIR, exist_ok=True)
        filename = f"{FAILURES_DIR}/{date_code}_R{meeting}_C{race}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.warning(f"Fallback: Saved failed JSON to {filename}")
    except Exception as e:
        logger.error(f"Critical: Failed to save fallback JSON: {e}")

# --- Helper Conversion ---
def to_euros(cents):
    """
    Converts API currency values (integers in cents) to standard Euros (float).
    Handles None types gracefully.
    """
    if cents is None: return None
    try:
        return float(cents) / 100.0
    except (ValueError, TypeError):
        return None

# --- Logic ---
def get_http_session():
    """
    Configures HTTP session with retry policies for resilience against
    transient network errors (429, 5xx).
    """
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session

def fetch_rapports_json(session, date, meeting, race):
    url = RAPPORTS_URL_TEMPLATE.format(date=date, meeting=meeting, race=race)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        resp = session.get(url, headers=headers, timeout=10)
        # Handle "No Content" or "Not Found" as valid logical states (race not run/cancelled)
        if resp.status_code in [404, 204]: return [], resp.status_code
        resp.raise_for_status()
        
        data = resp.json()
        if isinstance(data, list): return data, 200
        return data.get("rapportsDefinitifs", []), 200
    except Exception as e:
        logging.warning(f"Failed fetching reports R{meeting}C{race}: {e}")
        return [], 500

def insert_race_bet(cur, race_id, bet):
    """
    Inserts the Bet definition (metadata) and returns its primary key.
    Applies currency conversion on the base stake.
    """
    # Mapping Bet Type
    raw_type = bet.get("typePari")
    clean_type = BET_TYPE_MAP.get(raw_type, raw_type[:10] if raw_type else None)
    
    # CONVERSION: Base Stake to Euros (e.g., 200 cents -> 2.00 €)
    stake_euros = to_euros(bet.get("miseBase"))

    cur.execute(
        """
        INSERT INTO race_bet (race_id, bet_type, bet_family, base_stake, is_refunded)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (race_id, bet_type) DO NOTHING
        RETURNING bet_id;
        """,
        (
            race_id, 
            clean_type, 
            bet.get("famillePari"),
            stake_euros, 
            bet.get("rembourse")
        )
    )
    row = cur.fetchone()
    if row: return row[0]
    
    # Handle race condition where insert was skipped due to conflict
    cur.execute("SELECT bet_id FROM race_bet WHERE race_id = %s AND bet_type = %s", (race_id, clean_type))
    res = cur.fetchone()
    return res[0] if res else None

def insert_bet_report(cur, bet_id, r):
    if not bet_id: return
    
    # CONVERSION: Dividends to Euros
    # Note: winners_count is a quantity, not a monetary value; no conversion applied.
    div_euros = to_euros(r.get("dividende"))
    div_1e_euros = to_euros(r.get("dividendePourUnEuro"))

    cur.execute(
        """
        INSERT INTO bet_report (bet_id, combination, dividend, dividend_per_1e, winners_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (bet_id, combination) DO NOTHING;
        """,
        (
            bet_id, 
            r.get("combinaison"), 
            div_euros, 
            div_1e_euros, 
            r.get("nombreGagnants")
        )
    )

def process_single_race_reports(date_code, race_id, meeting_num, race_num):
    """
    Worker function processing all bets for a specific race.
    Executes within a single transaction scope (`with conn`).
    """
    time.sleep(random.uniform(0.1, 0.3)) # Jitter to reduce API burst load
    session = get_http_session()
    
    bets, status_code = fetch_rapports_json(session, date_code, meeting_num, race_num)
    
    if status_code in [204, 404]: return 0, IngestStatus.SKIPPED
    if not bets and status_code == 200: return 0, IngestStatus.SUCCESS
    if status_code >= 500: return 0, IngestStatus.FAILED

    conn = None
    count_bets = 0
    try:
        conn = get_pooled_connection()
        with conn: # Atomic Transaction Start
            with conn.cursor() as cur:
                for bet in bets:
                    bet_id = insert_race_bet(cur, race_id, bet)
                    count_bets += 1
                    for r in bet.get("rapports", []):
                        insert_bet_report(cur, bet_id, r)
        return count_bets, IngestStatus.SUCCESS
    except Exception as e:
        logging.error(f"DB Error Bets R{meeting_num}C{race_num}: {e}")
        if conn: conn.rollback()
        save_failed_json(bets, date_code, meeting_num, race_num)
        return 0, IngestStatus.FAILED
    finally:
        if conn: release_pooled_connection(conn)

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

def ingest_rapports_for_date(date_code):
    logger = logging.getLogger("BetsIngest")
    sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    
    init_db_pool() 
    
    try:
        logger.info(f"Starting PARALLEL RAPPORTS ingestion for {date_code}")
        races = get_races_for_date(sql_date)
        logger.info(f"Processing {len(races)} races.")

        total_bets, skipped_count, failed_count = 0, 0, 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_race = {
                executor.submit(process_single_race_reports, date_code, r_id, m, r): (m, r)
                for r_id, m, r in races
            }
            for future in as_completed(future_to_race):
                try:
                    count, status = future.result()
                    if status == IngestStatus.SUCCESS: total_bets += count
                    elif status == IngestStatus.SKIPPED: skipped_count += 1
                    else: failed_count += 1
                except Exception as e:
                    logger.error(f"Thread Error: {e}")
                    failed_count += 1

        logger.info(
            f"Ingestion Completed. "
            f"Bets: {total_bets} | Skipped: {skipped_count} | Failed: {failed_count}"
        )
    finally:
        close_db_pool() 

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_rapports_for_date(args.date)