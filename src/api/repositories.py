import datetime as dt
from typing import List, Dict, Any
import psycopg2.extras
from src.core.database import DatabaseManager

class RaceRepository:
    def __init__(self):
        self.db = DatabaseManager()

    def get_races_by_date(self, date_code: str) -> List[Dict[str, Any]]:
        try:
            target_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
        except ValueError:
            return []

        query = """
            SELECT 
                r.race_id,
                rm.meeting_number,
                r.race_number,
                r.discipline,
                r.distance_m,
                rm.racetrack_code
            FROM race r
            JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
            JOIN daily_program dp ON rm.program_id = dp.program_id
            WHERE dp.program_date = %s
            ORDER BY rm.meeting_number, r.race_number;
        """

        conn = self.db.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (target_date,))
                return cur.fetchall()
        finally:
            self.db.release_connection(conn)

    def get_participants_by_race(self, race_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                rp.pmu_number,
                h.horse_name,
                d.actor_name AS driver_name,
                t.actor_name AS trainer_name,
                rp.live_odds AS odds
            FROM race_participant rp
            JOIN horse h ON rp.horse_id = h.horse_id
            LEFT JOIN racing_actor d ON rp.driver_jockey_id = d.actor_id
            LEFT JOIN racing_actor t ON rp.trainer_id = t.actor_id
            WHERE rp.race_id = %s
            ORDER BY rp.pmu_number;
        """

        conn = self.db.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (race_id,))
                return cur.fetchall()
        finally:
            self.db.release_connection(conn)