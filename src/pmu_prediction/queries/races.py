from collections import defaultdict

def get_races_for_date(conn, program_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            rm.meeting_number,
            rm.racetrack_code,
            r.race_number,
            r.discipline,
            r.distance_m,
            r.declared_runners_count
        FROM race r
        JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
        JOIN daily_program dp ON rm.program_id = dp.program_id
        WHERE dp.program_date = %s
        ORDER BY rm.meeting_number, r.race_number;
        """,
        (program_date,)
    )

    rows = cur.fetchall()

    meetings = defaultdict(lambda: {
        "meeting_number": None,
        "track": None,
        "races": []
    })

    TRACK_NAME_MAP = {
        "SON": "Salon-de-Provence",
        "ARG": "Argentan",
        "CAG": "Cagnes-sur-Mer",
        "HWM": "Hambourg",
    }

    for meeting_num, track_code, race_num, discipline, distance, runners in rows:
        track_name = TRACK_NAME_MAP.get(track_code, track_code)

        meeting = meetings[meeting_num]
        meeting["meeting_number"] = meeting_num
        meeting["track"] = track_name

        meeting["races"].append({
            "id": f"R{meeting_num}C{race_num}",
            "race_number": race_num,
            "type": discipline,
            "distance": distance,
            "runners": runners
        })

    return list(meetings.values())


def get_race_id(conn, meeting_number, race_number, program_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.race_id
        FROM race r
        JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
        JOIN daily_program dp ON rm.program_id = dp.program_id
        WHERE rm.meeting_number = %s
          AND r.race_number = %s
          AND dp.program_date = %s;
        """,
        (meeting_number, race_number, program_date)
    )
    row = cur.fetchone()
    return row[0] if row else None
