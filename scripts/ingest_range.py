"""
Ingest data for a range of dates.
Wrapper around ingest_full_day.py to process multiple days sequentially.

Usage:
    python scripts/ingest_range.py --start 01112025 --end 05112025
"""

import argparse
import datetime as dt
import logging
import sys
import os
import time
import random

# -----------------------------------------------------------------------------
# Path Setup to import sibling scripts
# -----------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    # On importe la fonction principale du script journalier
    from ingest_full_day import process_full_day
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import ingest_full_day. Details: {e}")
    sys.exit(1)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def date_range_generator(start_date_str: str, end_date_str: str):
    """Yields date strings (DDMMYYYY) from start to end (inclusive)."""
    try:
        start = dt.datetime.strptime(start_date_str, "%d%m%Y").date()
        end = dt.datetime.strptime(end_date_str, "%d%m%Y").date()
    except ValueError:
        raise ValueError("Dates must be in format DDMMYYYY")

    if start > end:
        raise ValueError("Start date must be before or equal to end date.")

    delta = (end - start).days
    for i in range(delta + 1):
        day = start + dt.timedelta(days=i)
        yield day.strftime("%d%m%Y")


def ingest_range(start_date: str, end_date: str):
    logger = logging.getLogger("RangeIngest")
    logger.info("===================================================")
    logger.info("Starting BATCH Ingestion from %s to %s", start_date, end_date)
    logger.info("===================================================")

    try:
        dates = list(date_range_generator(start_date, end_date))
    except ValueError as e:
        logger.error(f"Date Error: {e}")
        sys.exit(1)

    total_days = len(dates)
    logger.info("Total days to process: %d", total_days)

    success_count = 0
    failure_count = 0
    global_start_time = time.time()

    for i, date_code in enumerate(dates, 1):
        logger.info(f"\n>>> PROCESSING DAY {i}/{total_days} : {date_code}")
        
        day_start = time.time()
        
        try:
            # Exécution de l'ingestion complète pour une journée
            process_full_day(date_code)
            
            success_count += 1
            
            # Délai de sécurité entre les jours (Anti-ban & Politeness)
            # On ne dort pas après le dernier jour
            if i < total_days:
                sleep_time = random.uniform(1.0, 3.0)
                logger.info(f"Day completed. Sleeping {sleep_time:.2f}s before next day...")
                time.sleep(sleep_time)

        except SystemExit as e:
            # ingest_full_day fait un sys.exit(1) en cas d'erreur critique.
            # On attrape cette exception pour ne pas tuer la boucle du range.
            if e.code != 0:
                logger.error(f"!!! CRITICAL FAILURE on date {date_code}. (Exit Code: {e.code})")
                failure_count += 1
            else:
                success_count += 1
        except Exception as e:
            logger.error(f"!!! UNHANDLED EXCEPTION on date {date_code}: {e}")
            failure_count += 1
        
        logger.info(f"Day {date_code} finished in {time.time() - day_start:.2f}s")

    total_duration = time.time() - global_start_time
    
    logger.info("\n===================================================")
    logger.info("BATCH COMPLETED.")
    logger.info(f"Range: {start_date} -> {end_date}")
    logger.info(f"Total Duration: {total_duration:.2f}s")
    logger.info(f"Stats: {success_count} Success | {failure_count} Failures")
    logger.info("===================================================")


if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(description="Ingest PMU data for a date range (Batch Mode).")
    parser.add_argument("--start", required=True, help="Start date (DDMMYYYY), e.g., 01112025")
    parser.add_argument("--end", required=True, help="End date (DDMMYYYY), e.g., 30112025")

    args = parser.parse_args()

    ingest_range(args.start, args.end)