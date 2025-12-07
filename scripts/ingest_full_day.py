"""
Master ingestion script for a full PMU day.
Fetches all meetings and races, then runs all ingestion steps.

Usage:
    python ingest_full_day.py --date 05112025
"""

import argparse
import logging
import requests
from typing import Dict, List

# Import all ingestion functions
from ingest_programme_day import ingest_programme_for_date
from ingest_participants_day import ingest_participants_for_date
from ingest_rapports_day import ingest_rapports_for_date
from ingest_performances_day import ingest_horse_race_history_for_date

PROGRAMME_DAY_URL = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}"
)


# --------------------------------------------
# LOGGING
# --------------------------------------------------------

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# ---------------------------------------------------------
# Fetch meeting and race list
# ---------------------------------------------------------

def get_meetings_and_races(date: str) -> Dict[int, List[int]]:
    """
    Fetch PMU programme of the day and return:
       { meeting_id: [race_id1, race_id2, ...] }
    """

    url = PROGRAMME_DAY_URL.format(date=date)
    logging.info("Fetching programme of the day: %s", url)

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    meetings = {}

    # Correct node in your JSON:
    # data["programme"]["reunions"]
    programme = data.get("programme", {})
    reunions = programme.get("reunions", [])

    for r in reunions:
        meeting_id = (
            r.get("numOfficiel")
            or r.get("numExterne")
            or r.get("numReunion")
        )

        if meeting_id is None:
            continue

        courses = r.get("courses", [])

        race_ids = [
            c.get("numOrdre")
            for c in courses
            if c.get("numOrdre") is not None
        ]

        meetings[meeting_id] = race_ids

    return meetings


# ---------------------------------------------------------
# FULL INGESTION LOGIC
# ---------------------------------------------------------

def ingest_full_day(date: str):
    logger = logging.getLogger("ingest_full_day")
    logger.info("Starting FULL ingestion for date %s", date)

    # Get program of the day
    # --- Ingestion Step 1: Programme (JSON 1)
    try:
        ingest_programme_for_date(date)
    except Exception as e:
        logger.error("Failed to ingest programme for %s: %s", date, e)
        return
    # Get full day structure
    meetings = get_meetings_and_races(date)
    logger.info("Found %d meetings for the day", len(meetings))

    # Iterate over meetings & races
    for meeting_id, races in meetings.items():
        logger.info("Processing meeting %s with %d races", meeting_id, len(races))

        for race_id in races:
            logger.info("Processing Race R%sC%s", meeting_id, race_id)

            try:
                # --- Ingestion Step 2: Participants (JSON 2)
                ingest_participants_for_date(date, meeting_id, race_id)

                # --- Ingestion Step 3: Rapports (JSON 5)
                ingest_rapports_for_date(date, meeting_id, race_id)

                # --- Ingestion Step 4: Horse history (JSON 3)
                ingest_horse_race_history_for_date(date, meeting_id, race_id)

                logger.info("  ✔ Completed R%sC%s", meeting_id, race_id)

            except Exception as e:
                logger.error(
                    "  Error during ingestion for R%sC%s: %s",
                    meeting_id, race_id, str(e)
                )
                # Continue with next race
                continue

    logger.info("FULL DAY INGESTION COMPLETED for date %s", date)




def parse_args():
    parser = argparse.ArgumentParser(description="Run full-day ingestion for a PMU date.")
    parser.add_argument("--date", required=True, help="PMU date code (e.g., 05112025)")
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    ingest_full_day(args.date)