from typing import Dict, List
import logging
import requests
 
PROGRAMME_DAY_URL = (
    "https://online.turfinfo.api.pmu.fr/rest/client/61/programme/{date}"
)
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

print(get_meetings_and_races('05112025'))
