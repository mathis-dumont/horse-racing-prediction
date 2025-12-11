"""
Ingest all data for a specific day (Programme, Participants, Performances, Rapports).
This script orchestrates the execution of the individual ingestion scripts in the correct order.

Order of execution:
1. Programme (JSON 1)     -> Creates DailyProgram, Meetings, Races.
2. Participants (JSON 2)  -> Creates Horses, RaceParticipants.
3. Performances (JSON 3)  -> Creates HorseRaceHistory.
4. Rapports (JSON 4)      -> Creates RaceBets, BetReports.

Usage:
    python scripts/ingest_full_day.py --date 05112025
"""

import argparse
import logging
import time
import sys
import os

# Path Setup
# Ensure we can import sibling scripts whether running from root or scripts/ dir
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from ingest_programme_day import ingest_programme_for_date
    from ingest_participants_day import ingest_participants_for_date
    from ingest_performances_day import ingest_performances_for_date
    from ingest_rapports_day import ingest_rapports_for_date
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import ingestion modules. Details: {e}")
    sys.exit(1)

def setup_logging():
    """Configure logging for the full orchestration script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def process_full_day(date_code: str):
    """
    Run the full ingestion pipeline for the given date.
    """
    logger = logging.getLogger("FullIngest")
    start_time = time.time()
    
    logger.info("===================================================")
    logger.info("STARTING FULL INGESTION FOR DATE: %s", date_code)
    logger.info("===================================================")

    # STEP 1: PROGRAMME (JSON 1)
    # Critical: Creates the race structure (Foreign Keys for everything else).

    try:
        logger.info(">>> STEP 1/4: Ingesting Programme...")
        ingest_programme_for_date(date_code)
        logger.info(">>> STEP 1/4: Success.")
    except Exception as e:
        logger.error("!!! STEP 1 FAILED: Programme ingestion aborted. Stopping pipeline.")
        logger.error(e)
        sys.exit(1)

    # STEP 2: PARTICIPANTS (JSON 2)
    # Populates Horse and RaceParticipant tables.

    try:
        logger.info(">>> STEP 2/4: Ingesting Participants...")
        ingest_participants_for_date(date_code)
        logger.info(">>> STEP 2/4: Success.")
    except Exception as e:
        logger.error("!!! STEP 2 FAILED: Participants ingestion aborted.")
        logger.error(e)
        # We can optionally continue or stop here. Usually better to stop.
        sys.exit(1)

    # STEP 3: PERFORMANCES (JSON 3)
    # Longest step: fetches history for every horse in every race.

    try:
        logger.info(">>> STEP 3/4: Ingesting Performances (History)...")
        ingest_performances_for_date(date_code)
        logger.info(">>> STEP 3/4: Success.")
    except Exception as e:
        logger.error("!!! STEP 3 FAILED: Performances ingestion aborted.")
        logger.error(e)
        # Not critical for the race result itself, but critical for ML features.
        
    # STEP 4: RAPPORTS (JSON 4)
    # Final betting results.

    try:
        logger.info(">>> STEP 4/4: Ingesting Rapports (Bets)...")
        ingest_rapports_for_date(date_code)
        logger.info(">>> STEP 4/4: Success.")
    except Exception as e:
        logger.error("!!! STEP 4 FAILED: Rapports ingestion aborted.")
        logger.error(e)

    # SUMMARY

    elapsed_time = time.time() - start_time
    logger.info("===================================================")
    logger.info("FULL INGESTION COMPLETED FOR DATE: %s", date_code)
    logger.info("Total execution time: %.2f seconds", elapsed_time)
    logger.info("===================================================")

if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="Orchestrator: Ingest Programme, Participants, Performances, and Rapports for a full day."
    )
    parser.add_argument(
        "--date", 
        required=True, 
        help="PMU date code (e.g., 05112025)"
    )
    
    args = parser.parse_args()
    process_full_day(args.date)