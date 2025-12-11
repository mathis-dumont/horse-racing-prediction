"""
Ingest PMU participants JSON (JSON 2) for a WHOLE day.
Scope: Horse -> Race Participant.

Logic:
    - Queries DB to find all races for the given date.
    - Iterates over each race to fetch participants JSON.
    - Inserts horses and links them to the race.
    - Uses ON CONFLICT DO NOTHING.

Usage:
    python scripts/ingest_participants_day.py --date 05112025
"""

import argparse
import datetime as dt
import logging
import os
import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

PARTICIPANTS_URL_TEMPLATE = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}/R{meeting}/C{race}/participants"
)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def get_db_connection():
    return psycopg2.connect(os.getenv("DB_URL"))

def get_races_for_date(cur, sql_date):
    """Retrieve all (race_id, meeting_number, race_number) for a SQL date."""
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

def fetch_participants_json(date_code, meeting_num, race_num):
    url = PARTICIPANTS_URL_TEMPLATE.format(date=date_code, meeting=meeting_num, race=race_num)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            logging.warning("404 for %s (Race might be cancelled)", url)
            return []
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data.get("participants", [])
        return data if isinstance(data, list) else []
    except Exception as e:
        logging.error("Failed to fetch %s: %s", url, e)
        return []

def safe_get(obj, path, default=None):
    keys = path.split(".")
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def insert_horse(cur, p):
    """Insert horse if not exists, return horse_id."""
    name = p.get("nom")
    if not name: return None
    
    age = p.get("age")
    birth_year = (dt.date.today().year - int(age)) if age else None
    
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
    
    cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (name,))
    res = cur.fetchone()
    return res[0] if res else None

def insert_participant(cur, race_id, horse_id, p):
    """Insert race_participant if not exists."""
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

def ingest_participants_for_date(date_code):
    logger = logging.getLogger(__name__)
    sql_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
    logger.info("Starting PARTICIPANTS ingestion for %s (%s)", date_code, sql_date)

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                races = get_races_for_date(cur, sql_date)
                logger.info("Found %d races to process", len(races))

                for r in races:
                    race_id, meeting_num, race_num = r
                    
                    participants = fetch_participants_json(date_code, meeting_num, race_num)
                    if not participants:
                        continue
                        
                    for p in participants:
                        horse_id = insert_horse(cur, p)
                        insert_participant(cur, race_id, horse_id, p)
                    
                    # Optional: Commit per race or let the big transaction handle it
                    # logging.info("Processed R%s C%s", meeting_num, race_num)
    finally:
        conn.close()

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="PMU date code (e.g. 05112025)")
    args = parser.parse_args()
    ingest_participants_for_date(args.date)