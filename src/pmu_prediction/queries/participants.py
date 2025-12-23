def get_participants_for_race_id(conn, race_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            rp.pmu_number,
            h.horse_name,
            rp.reference_odds
        FROM race_participant rp
        JOIN horse h ON rp.horse_id = h.horse_id
        WHERE rp.race_id = %s
        ORDER BY rp.pmu_number;
        """,
        (race_id,)
    )

    rows = cur.fetchall()

    return [
        {
            "pmu_number": pmu,
            "horse": name,
            "odds": odds
        }
        for pmu, name, odds in rows
    ]

