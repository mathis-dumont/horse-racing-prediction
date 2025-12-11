"""
Ingest PMU reports (JSON 4) for a WHOLE day.
Scope: Race Bet -> Bet Report.

Logic:
    - Queries DB for all races of the date.
    - Fetches reports (rapports-definitifs).
    - Inserts betting metadata (race_bet) and results (bet_report).
    - Uses ON CONFLICT DO NOTHING (requires the constraints added in SQL/02).

Usage:
    python scripts/ingest_rapports_day.py --date 05112025
"""

import argparse
import datetime as dt
import logging
import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

RAPPORTS_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/1/programme/{date}/R{meeting}/C{race}/rapports-definitifs"
)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def get_db_connection():
    return psycopg2.connect(os.getenv("DB_URL"))

def get_races_for_date(cur, sql_date):
    """Retrieve (race_id, meeting_number, race_number) for a SQL date."""
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

def fetch_rapports_json(date, meeting, race):
    url = RAPPORTS_URL_TEMPLATE.format(date=date, meeting=meeting, race=race)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list): return data
        return data.get("rapportsDefinitifs", []) if isinstance(data, dict) else []
    except Exception as e:
        logging.error("Failed to fetch reports for %s: %s", url, e)
        return []

def insert_race_bet(cur, race_id, bet):
    """Insert race_bet if not exists, return bet_id."""
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
    if row:
        return row[0]
    
    # Retrieve existing ID
    cur.execute(
        "SELECT bet_id FROM race_bet WHERE race_id = %s AND bet_type = %s",
        (race_id, bet.get("typePari"))
    )
    res = cur.fetchone()
    return res[0] if res else None

def insert_bet_report(cur, bet_id, r):
    """Insert bet_report if not exists."""
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

def ingest_rapports_for_date(date_code):
    logger = logging.getLogger(__name__)
    sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    logger.info("Starting RAPPORTS ingestion for %s", date_code)

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                races = get_races_for_date(cur, sql_date)
                logger.info("Found %d races to process", len(races))
                
                for race_id, meeting_num, race_num in races:
                    bets = fetch_rapports_json(date_code, meeting_num, race_num)
                    
                    for bet in bets:
                        bet_id = insert_race_bet(cur, race_id, bet)
                        
                        reports = bet.get("rapports", [])
                        for r in reports:
                            insert_bet_report(cur, bet_id, r)
    finally:
        conn.close()

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_rapports_for_date(args.date)