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

# -----------------------------------------------------------------------------
# Path Setup to import sibling scripts
# -----------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(_file_))
sys.path.append(current_dir)

try:
    from ingest_full_day import process_full_day
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import ingest_full_day. Details: {e}")
    sys.exit(1)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def date_range_generator(start_date_str: str, end_date_str: str):
    """Yields date strings (DDMMYYYY) from start to end (inclusive)."""
    start = dt.datetime.strptime(start_date_str, "%d%m%Y").date()
    end = dt.datetime.strptime(end_date_str, "%d%m%Y").date()

    if start > end:
        raise ValueError("Start date must be before or equal to end date.")

    delta = (end - start).days
    for i in range(delta + 1):
        day = start + dt.timedelta(days=i)
        yield day.strftime("%d%m%Y")


def ingest_range(start_date: str, end_date: str):
    logger = logging.getLogger("RangeIngest")
    logger.info("Starting Batch Ingestion from %s to %s", start_date, end_date)

    dates = list(date_range_generator(start_date, end_date))
    total_days = len(dates)
    
    logger.info("Total days to process: %d", total_days)

    success_count = 0
    failure_count = 0

    for i, date_code in enumerate(dates, 1):
        logger.info("---------------------------------------------------")
        logger.info("Processing Day %d/%d : %s", i, total_days, date_code)
        logger.info("---------------------------------------------------")

        try:
            process_full_day(date_code)
            success_count += 1
            
            # Optional: Polite pause between days to respect API limits
            # time.sleep(1) 

        except Exception as e:
            logger.error("!!! CRITICAL FAILURE on date %s. Skipping to next day.", date_code)
            logger.error(e)
            failure_count += 1
            # We continue the loop to not block the whole batch

    logger.info("===================================================")
    logger.info("BATCH COMPLETED.")
    logger.info("Success: %d | Failures: %d", success_count, failure_count)
    logger.info("===================================================")


if _name_ == "_main_":
    setup_logging()
    
    parser = argparse.ArgumentParser(description="Ingest PMU data for a date range.")
    parser.add_argument("--start", required=True, help="Start date (DDMMYYYY)")
    parser.add_argument("--end", required=True, help="End date (DDMMYYYY)")
    
    args = parser.parse_args()
    
    try:
        ingest_range(args.start, args.end)
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)