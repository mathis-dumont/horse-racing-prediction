"""
Ingest a full PMU date range by calling ingest_full_day for each date.
Usage:
    python ingest_range.py --start 01102024 --end 31102024
"""

import argparse
import logging
import random
import time
from datetime import datetime, timedelta

from ingest_full_day import ingest_full_day


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | ingest_range | %(message)s",
    )


def daterange(start_date, end_date):
    """Generator that yields each date between start_date and end_date included."""
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def ingest_range(start: str, end: str):
    """
    Ingest all PMU data between start and end (DDMMYYYY format).
    Adds delays to avoid hitting API rate limits.
    """

    logger = logging.getLogger("ingest_range")

    # Parse dates in DDMMYYYY format
    start_date = datetime.strptime(start, "%d%m%Y")
    end_date = datetime.strptime(end, "%d%m%Y")

    total_days = (end_date - start_date).days + 1
    logger.info(f"Starting ingestion from {start} to {end} ({total_days} days).")

    for d in daterange(start_date, end_date):
        date_str = d.strftime("%d%m%Y")  # ingest_full_day attend JJMMAAAA

        logger.info(f"=== Ingesting day {date_str} ===")

        try:
            ingest_full_day(date_str)

        except Exception as e:
            logger.error(f"Error while ingesting {date_str}: {e}")

        # Sleep to avoid spamming PMU servers.
        delay = random.uniform(10, 20)  # between 10 and 20 seconds
        logger.info(f"Sleeping {delay:.1f}s before next day...")
        time.sleep(delay)

    logger.info("Ingestion finished for full date range.")


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest PMU data for a date range (DDMMYYYY).")
    parser.add_argument("--start", required=True, help="Start date (DDMMYYYY)")
    parser.add_argument("--end", required=True, help="End date (DDMMYYYY)")
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    ingest_range(args.start, args.end)
