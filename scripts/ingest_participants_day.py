"""
Ingest PMU participants JSON (JSON 2)
for a given date / meeting / race
into PostgreSQL (Supabase) tables :

Tables:
- horse
- race_participant

Usage:
    python ingest_participants.py --date 05112025 --meeting 1 --race 1
"""

import argparse
import datetime as dt
import json
import logging
import os

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

PARTICIPANTS_URL_TEMPLATE = ("https://online.turfinfo.api.pmu.fr/rest/client/61/"
    "programme/{date}/R{meeting}/C{race}/participants")

def safe_get(obj, path, default=None):
    keys = path.split(".")
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return default
        if k not in cur:
            return default
        cur = cur[k]
    return cur

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



def fetch_participants_json(date: str, meeting: str, race: str) -> dict:
    """
    Fetch the programme JSON for a given PMU date code (e.g. '05112025').

    Returns the parsed JSON as a Python dict.
    """
    url = PARTICIPANTS_URL_TEMPLATE.format(
        date=date,
        meeting = meeting,
        race = race)
    logging.info("Fetching participants JSON from %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data


# def convert_participants_timestamp_to_date(ms_timestamp: int) -> dt.date:
#     """
#     Convert PMU programme timestamp in milliseconds to a Python date.

#     The 'programme.date' field is a timestamp in milliseconds since epoch.
#     """
#     # Using UTC since we only care about the calendar day.
#     return dt.datetime.utcfromtimestamp(ms_timestamp / 1000).date()


def upsert_horse(cur, p):
    horse_name = p.get("nom")
    age = p.get("age")
    sex = p.get("sexe")

    # Approximate birth year
    birth_year = None
    if age is not None:
        birth_year = dt.date.today().year - int(age)

    cur.execute(
        """
        INSERT INTO horse (
            horse_name,
            sex,
            birth_year
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (horse_name)
        DO UPDATE SET
            sex = EXCLUDED.sex,
            birth_year = EXCLUDED.birth_year
        RETURNING horse_id;
        """,
        (horse_name, sex, birth_year),
    )
    return cur.fetchone()[0]

def upsert_race_participant(cur, race_id, horse_id, p):
    cur.execute(
        """
        INSERT INTO race_participant (
            race_id,
            horse_id,
            pmu_number,
            age,
            sex,
            trainer_name,
            driver_jockey_name,
            shoeing_status,
            career_races_count,
            career_winnings,
            reference_odds,
            live_odds,
            raw_performance_string,
            trainer_advice,
            finish_rank,
            incident,
            time_achieved_s,
            reduction_km,
            post_race_comment
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (race_id, pmu_number)
        DO UPDATE SET
            horse_id = EXCLUDED.horse_id,
            age = EXCLUDED.age,
            sex = EXCLUDED.sex,
            trainer_name = EXCLUDED.trainer_name,
            driver_jockey_name = EXCLUDED.driver_jockey_name,
            shoeing_status = EXCLUDED.shoeing_status,
            career_races_count = EXCLUDED.career_races_count,
            career_winnings = EXCLUDED.career_winnings,
            reference_odds = EXCLUDED.reference_odds,
            live_odds = EXCLUDED.live_odds,
            raw_performance_string = EXCLUDED.raw_performance_string,
            trainer_advice = EXCLUDED.trainer_advice,
            finish_rank = EXCLUDED.finish_rank,
            incident = EXCLUDED.incident,
            time_achieved_s = EXCLUDED.time_achieved_s,
            reduction_km = EXCLUDED.reduction_km,
            post_race_comment = EXCLUDED.post_race_comment
        RETURNING participant_id;
        """,
        (
            race_id,
            horse_id,
            p.get("numPmu"),
            p.get("age"),
            p.get("sexe"),
            p.get("entraineur"),
            p.get("driver"),
            p.get("deferre"),
            p.get("nombreCourses"),
            safe_get(p, "gainsParticipant.gainsCarriere"),
            safe_get(p, "dernierRapportReference.rapport"),
            safe_get(p, "dernierRapportDirect.rapport"),
            p.get("musique"),
            p.get("avisEntraineur"),
            p.get("ordreArrivee"),
            p.get("incident"),
            p.get("tempsObtenu"),
            p.get("reductionKilometrique"),
            safe_get(p, "commentaireApresCourse.texte"),
        ),
    )

    return cur.fetchone()[0]


def ingest_participants_for_date(date, meeting, race):
    logger = logging.getLogger(__name__)
    logger.info(
        "Starting participants ingestion for date=%s R%sC%s",
        date, meeting, race
    )

    raw = fetch_participants_json(date, meeting, race)


    if isinstance(raw, dict):
        participants = raw.get("participants", [])
    else:
        participants = raw

    if not isinstance(participants, list):
        raise RuntimeError(f"Unexpected JSON format from API: {type(participants)}")

    if not participants:
        logger.warning("No participants returned by API")
        return


    if not participants:
        logger.warning("No participants returned by API")
        return

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

                # To recover the race ID in the race table
                # Convert 05112025 -> 2025-11-04
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

                count = 0
                for p in participants:
                    horse_id = upsert_horse(cur, p)
                    upsert_race_participant(cur, race_id, horse_id, p)
                    count += 1

                logger.info("Inserted/updated %d participants", count)

    finally:
        conn.close()
        logger.info("DB connection closed")


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest PMU participants")
    parser.add_argument("--date", required=True, help="PMU date code")
    parser.add_argument("--meeting", required=True, type=int)
    parser.add_argument("--race", required=True, type=int)
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    ingest_participants_for_date(args.date, args.meeting, args.race)
