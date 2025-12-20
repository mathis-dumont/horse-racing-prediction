import argparse
import sys
import logging
from datetime import datetime, timedelta
from typing import List

from src.ingestion.program import ProgramIngestor
from src.ingestion.participants import ParticipantsIngestor
from src.ingestion.performances import PerformancesIngestor
from src.ingestion.rapports import RapportsIngestor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | ORCHESTRATOR | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Orchestrator")

def generate_date_range(start_str: str, end_str: str) -> List[str]:
    """Generates a list of date strings (DDMMYYYY) between start and end inclusive."""
    try:
        start = datetime.strptime(start_str, "%d%m%Y")
        end = datetime.strptime(end_str, "%d%m%Y")
    except ValueError:
        logger.error("Invalid date format. Please use DDMMYYYY (e.g., 05112025).")
        sys.exit(1)

    if start > end:
        logger.error("Start date cannot be after end date.")
        sys.exit(1)

    date_list = []
    current = start
    while current <= end:
        date_list.append(current.strftime("%d%m%Y"))
        current += timedelta(days=1)
    
    return date_list

def process_date(date_code: str, ingest_type: str):
    """Executes the ingestion pipeline for a specific single date."""
    logger.info(f"=== Starting Ingestion for Date: {date_code} ===")
    
    ingestors = []
    
    if ingest_type in ["program", "all"]:
        ingestors.append(ProgramIngestor(date_code))
        
    if ingest_type in ["participants", "all"]:
        ingestors.append(ParticipantsIngestor(date_code))
        
    if ingest_type in ["performances", "all"]:
        ingestors.append(PerformancesIngestor(date_code))
        
    if ingest_type in ["rapports", "all"]:
        ingestors.append(RapportsIngestor(date_code))

    for ingestor in ingestors:
        try:
            ingestor.ingest()
        except Exception as e:
            logger.error(f"Ingestion failed for {ingestor.__class__.__name__} on {date_code}: {e}")

def main():
    parser = argparse.ArgumentParser(description="PMU Ingestion Orchestrator (ETL CLI)")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="Single date code (e.g., 05112025)")
    group.add_argument("--range", nargs=2, metavar=('START', 'END'), help="Date range (e.g., 01012025 05012025)")
    
    parser.add_argument(
        "--type", 
        required=True, 
        choices=["program", "participants", "performances", "rapports", "all"],
        help="Type of data to ingest"
    )
    
    args = parser.parse_args()
    
    dates_to_process = []
    
    if args.date:
        dates_to_process = [args.date]
    elif args.range:
        start_date, end_date = args.range
        dates_to_process = generate_date_range(start_date, end_date)
    
    total_days = len(dates_to_process)
    logger.info(f"Job started. Processing {total_days} day(s). Mode: {args.type}")

    for i, date_code in enumerate(dates_to_process, 1):
        logger.info(f"Progress: [{i}/{total_days}] Processing {date_code}")
        process_date(date_code, args.type)
        
    logger.info("All jobs completed.")

if __name__ == "__main__":
    main()