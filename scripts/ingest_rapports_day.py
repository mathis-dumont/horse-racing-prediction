"""
Ingest PMU betting reports (JSON 4) for a WHOLE day.
Scope: Race Bet -> Bet Report.
Mode: Parallel Execution with Throttling & HTTP 204 handling.
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
RAPPORTS_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{date}/R{meeting}/C{race}/rapports-definitifs"
)
MAX_WORKERS = 12 
REQUEST_DELAY = 0.050

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Silence urllib3 to avoid flooding logs
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def get_db_connection():
    return psycopg2.connect(os.getenv("DB_URL"))

def fetch_rapports_json(date, meeting, race):
    """
    Fetches betting reports with browser-like headers.
    Handles 204 No Content gracefully.
    """
    url = RAPPORTS_URL_TEMPLATE.format(date=date, meeting=meeting, race=race)
    
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
            
        # Handle 204 No Content (Common for foreign races or races without bets)
        if resp.status_code == 204:
            return []
            
        resp.raise_for_status()
        
        try:
            data = resp.json()
        except requests.exceptions.JSONDecodeError:
            logging.warning(f"Empty JSON content for {url} (Status: {resp.status_code})")
            return []

        if isinstance(data, list): return data
        return data.get("rapportsDefinitifs", []) if isinstance(data, dict) else []
        
    except Exception as e:
        logging.error(f"Network error fetching reports {url}: {e}")
        return []

def insert_race_bet(cur, race_id, bet):
    cur.execute(
        """
        INSERT INTO race_bet (race_id, bet_type, bet_family, base_stake, is_refunded)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (race_id, bet_type) DO NOTHING
        RETURNING bet_id;
        """,
        (
            race_id, bet.get("typePari"), bet.get("famillePari"),
            bet.get("miseBase"), bet.get("rembourse")
        )
    )
    row = cur.fetchone()
    if row: return row[0]
    
    cur.execute(
        "SELECT bet_id FROM race_bet WHERE race_id = %s AND bet_type = %s",
        (race_id, bet.get("typePari"))
    )
    res = cur.fetchone()
    return res[0] if res else None

def insert_bet_report(cur, bet_id, r):
    if not bet_id: return
    cur.execute(
        """
        INSERT INTO bet_report (bet_id, combination, dividend, dividend_per_1e, winners_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (bet_id, combination) DO NOTHING;
        """,
        (
            bet_id, r.get("combinaison"), r.get("dividende"),
            r.get("dividendePourUnEuro"), r.get("nombreGagnants")
        )
    )

def process_single_race_reports(date_code, race_id, meeting_num, race_num):
    time.sleep(REQUEST_DELAY)
    bets = fetch_rapports_json(date_code, meeting_num, race_num)
    if not bets: return 0

    conn = get_db_connection()
    count_bets = 0
    try:
        with conn:
            with conn.cursor() as cur:
                for bet in bets:
                    bet_id = insert_race_bet(cur, race_id, bet)
                    count_bets += 1
                    reports = bet.get("rapports", [])
                    for r in reports:
                        insert_bet_report(cur, bet_id, r)
    except Exception as e:
        logging.error(f"DB Error Bets R{meeting_num}C{race_num}: {e}")
    finally:
        conn.close()
    return count_bets

def get_races_for_date(sql_date):
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

def ingest_rapports_for_date(date_code):
    logger = logging.getLogger("BetsIngest")
    sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    logger.info(f"Starting PARALLEL RAPPORTS ingestion for {date_code}")
    races = get_races_for_date(sql_date)
    logger.info(f"Processing {len(races)} races.")

    total_bets_processed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_race = {
            executor.submit(process_single_race_reports, date_code, r_id, m, r): (m, r)
            for r_id, m, r in races
        }
        for future in as_completed(future_to_race):
            try:
                count = future.result()
                total_bets_processed += count
            except Exception as e:
                logger.error(f"Thread Error: {e}")

    logger.info(f"Ingestion Completed. Total bets processed: {total_bets_processed}")

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_rapports_for_date(args.date)