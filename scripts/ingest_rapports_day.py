"""
Ingest PMU rapports définitifs (JSON 4)
for a given date / meeting / race
into PostgreSQL tables:

- race_bet
- bet_report

Usage:
    python ingest_rapports_day.py --date 05112025 --meeting 1 --race 1
"""

import argparse
import datetime as dt
import logging
import os

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

RAPPORTS_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/1/"
    "programme/{date}/R{meeting}/C{race}/rapports-definitifs"
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


def safe_get(obj, path, default=None):

    keys = path.split(".")
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def fetch_rapports_json(date: str, meeting: int, race: int):
    """
    Fetch JSON 4 (rapports-definitifs) for a given date / meeting / race.

    Returns the parsed JSON as a Python list of bets.
    """
    url = RAPPORTS_URL_TEMPLATE.format(
        date=date,
        meeting=meeting,
        race=race,
    )
    logging.info("Fetching rapports JSON from %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Normalement, l'API renvoie directement une liste.
    if isinstance(data, list):
        bets = data
    elif isinstance(data, dict):
        bets = data.get("rapportsDefinitifs", [])
    else:
        bets = []

    return bets


def insert_race_bet(cur, race_id: int, bet: dict) -> int:

    bet_type = bet.get("typePari")
    bet_family = bet.get("famillePari")
    base_stake = bet.get("miseBase")
    is_refunded = bet.get("rembourse")

    logging.info(
        "Inserting race_bet for race_id=%s, bet_type=%s",
        race_id,
        bet_type,
    )

    cur.execute(
        """
        INSERT INTO race_bet (
            race_id,
            bet_type,
            bet_family,
            base_stake,
            is_refunded
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING bet_id;
        """,
        (race_id, bet_type, bet_family, base_stake, is_refunded),
    )

    bet_id = cur.fetchone()[0]
    return bet_id


def insert_bet_report(cur, bet_id: int, report: dict) -> int:
    
    combination = report.get("combinaison")
    dividend = report.get("dividende")
    dividend_per_1e = report.get("dividendePourUnEuro")
    winners_count = report.get("nombreGagnants")

    logging.info(
        "Inserting bet_report for bet_id=%s, combination=%s",
        bet_id,
        combination,
    )

    cur.execute(
        """
        INSERT INTO bet_report (
            bet_id,
            combination,
            dividend,
            dividend_per_1e,
            winners_count
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING report_id;
        """,
        (
            bet_id,
            combination,
            dividend,
            dividend_per_1e,
            winners_count,
        ),
    )

    report_id = cur.fetchone()[0]
    return report_id


def ingest_rapports(date: str, meeting: int, race: int) -> None:
   
    logger = logging.getLogger(__name__)
    logger.info(
        "Starting rapports ingestion for date=%s R%sC%s",
        date,
        meeting,
        race,
    )

    bets = fetch_rapports_json(date, meeting, race)

    if not bets:
        logger.warning("No bets (rapports-definitifs) returned by API")
        return

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

                # On récupère l’ID de la course dans la table "race"
                sql_date = dt.datetime.strptime(date, "%d%m%Y").date()

                cur.execute(
                    """
                    SELECT r.race_id
                    FROM race r
                    JOIN race_meeting rm ON rm.meeting_id = r.meeting_id
                    JOIN daily_program dp ON dp.program_id = rm.program_id
                    WHERE dp.program_date = %s
                      AND rm.meeting_number = %s
                      AND r.race_number = %s;
                    """,
                    (sql_date, meeting, race),
                )

                res = cur.fetchone()
                if not res:
                    raise RuntimeError(
                        f"race_id not found for date={sql_date}, meeting={meeting}, race={race}"
                    )

                race_id = res["race_id"]
                logger.info("Found race_id=%s", race_id)

                bet_count = 0
                report_count = 0

                for bet in bets:
                    bet_id = insert_race_bet(cur, race_id, bet)
                    bet_count += 1

                    rapports = bet.get("rapports", []) or []
                    for r in rapports:
                        insert_bet_report(cur, bet_id, r)
                        report_count += 1

                logger.info(
                    "Inserted %d bets and %d reports for race_id=%s",
                    bet_count,
                    report_count,
                    race_id,
                )

    finally:
        conn.close()
        logger.info("DB connection closed")


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest PMU rapports-definitifs (JSON 4)")
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    parser.add_argument("--meeting", required=True, type=int, help="Meeting number (e.g. 1 for R1)")
    parser.add_argument("--race", required=True, type=int, help="Race number (e.g. 1 for C1)")
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    ingest_rapports(args.date, args.meeting, args.race)
