import argparse
import sys
from src.ingestion.program import ProgramIngestor
from src.ingestion.participants import ParticipantsIngestor
from src.ingestion.performances import PerformancesIngestor
from src.ingestion.rapports import RapportsIngestor

def main():
    parser = argparse.ArgumentParser(description="PMU Ingestion Orchestrator")
    parser.add_argument("--date", required=True, help="Date code (e.g. 05112025)")
    parser.add_argument(
        "--type", 
        required=True, 
        choices=["program", "participants", "performances", "rapports", "all"],
        help="Type of ingestion to run"
    )
    
    args = parser.parse_args()
    
    ingestors = []
    
    if args.type == "program" or args.type == "all":
        ingestors.append(ProgramIngestor(args.date))
        
    if args.type == "participants" or args.type == "all":
        ingestors.append(ParticipantsIngestor(args.date))
        
    if args.type == "performances" or args.type == "all":
        ingestors.append(PerformancesIngestor(args.date))
        
    if args.type == "rapports" or args.type == "all":
        ingestors.append(RapportsIngestor(args.date))

    for ingestor in ingestors:
        try:
            ingestor.ingest()
        except Exception as e:
            print(f"Ingestion failed for {ingestor.__class__.__name__}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()