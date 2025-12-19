import datetime as dt
import logging
import requests
from src.core.config import PROGRAMME_URL_TEMPLATE, HEADERS, STATUS_MAP, TRACK_MAP
from src.ingestion.base import BaseIngestor

class ProgramIngestor(BaseIngestor):
    def fetch_programme_json(self) -> dict:
        url = PROGRAMME_URL_TEMPLATE.format(date_code=self.date_code)
        self.logger.info("Fetching programme JSON from %s", url)
        session = self._get_http_session()
        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            self.logger.error("CRITICAL: Failed to fetch programme: %s", e)
            raise e

    def _insert_daily_program(self, cur, program_date: dt.date) -> int:
        cur.execute(
            """
            INSERT INTO daily_program (program_date) VALUES (%s)
            ON CONFLICT (program_date) DO NOTHING RETURNING program_id;
            """,
            (program_date,)
        )
        row = cur.fetchone()
        if row: return row[0]
        cur.execute("SELECT program_id FROM daily_program WHERE program_date = %s", (program_date,))
        return cur.fetchone()[0]

    def _insert_race_meeting(self, cur, program_id: int, reunion: dict) -> int:
        num_officiel = reunion.get("numOfficiel")
        meeting_type = self._safe_truncate("meeting_type", reunion.get("nature"), 50)
        racetrack_code = self._safe_truncate("racetrack_code", (reunion.get("hippodrome") or {}).get("code"), 10)
        temp = (reunion.get("meteo") or {}).get("temperature")
        wind = (reunion.get("meteo") or {}).get("directionVent")

        cur.execute(
            """
            INSERT INTO race_meeting (
                program_id, meeting_number, meeting_type, 
                racetrack_code, weather_temperature, weather_wind
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (program_id, meeting_number) DO NOTHING
            RETURNING meeting_id;
            """,
            (program_id, num_officiel, meeting_type, racetrack_code, temp, wind),
        )
        row = cur.fetchone()
        if row: return row[0]
        cur.execute(
            "SELECT meeting_id FROM race_meeting WHERE program_id = %s AND meeting_number = %s",
            (program_id, num_officiel)
        )
        return cur.fetchone()[0]

    def _insert_race(self, cur, meeting_id: int, course: dict):
        race_number = course.get("numOrdre")
        raw_status = course.get("statut")
        race_status = STATUS_MAP.get(raw_status, raw_status[:10] if raw_status else None)
        raw_track = course.get("typePiste")
        track_type = TRACK_MAP.get(raw_track, raw_track[:10] if raw_track else None)

        discipline = self._safe_truncate("discipline", course.get("discipline"), 20)
        race_status_category = self._safe_truncate("race_status_category", course.get("categorieStatut"), 50)
        race_category = course.get("categorieParticularite")
        distance_m = course.get("distance")
        
        penetrometre = course.get("penetrometre") or {}
        raw_val = penetrometre.get("valeurMesure")
        terrain_label = penetrometre.get("intitule")
        penetrometer_value = None
        if raw_val is not None:
            try:
                penetrometer_value = float(str(raw_val).replace(",", "."))
            except (ValueError, TypeError):
                pass

        declared_runners = course.get("nombreDeclaresPartants")
        conditions = course.get("conditions")
        duration_raw = course.get("dureeCourse")
        race_duration_s = int(duration_raw) // 1000 if duration_raw else None

        cur.execute(
            """
            INSERT INTO race (
                meeting_id, race_number, discipline, race_category,
                distance_m, track_type, terrain_label, penetrometer,
                declared_runners_count, conditions_text, race_status,
                race_duration_s, race_status_category
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (meeting_id, race_number) DO NOTHING;
            """,
            (
                meeting_id, race_number, discipline, race_category,
                distance_m, track_type, terrain_label, penetrometer_value,
                declared_runners, conditions, race_status,
                race_duration_s, race_status_category
            ),
        )

    def ingest(self):
        self.logger.info("Starting PROGRAMME ingestion for date=%s", self.date_code)
        try:
            data = self.fetch_programme_json()
        except Exception:
            self.logger.error("Skipping date %s due to API failure.", self.date_code)
            return

        programme = data.get("programme") or {}
        try:
            program_date = dt.datetime.strptime(self.date_code, "%d%m%Y").date()
        except ValueError:
            ts = programme.get("date")
            program_date = dt.datetime.fromtimestamp(ts / 1000).date()

        conn = self.db_manager.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    program_id = self._insert_daily_program(cur, program_date)
                    reunions = programme.get("reunions", [])
                    self.logger.info("Found %d meetings.", len(reunions))
                    
                    count_races = 0
                    for reunion in reunions:
                        meeting_id = self._insert_race_meeting(cur, program_id, reunion)
                        courses = reunion.get("courses", [])
                        for course in courses:
                            discipline = course.get("discipline", "").upper()
                            if discipline in ["ATTELE", "MONTE"]:
                                self._insert_race(cur, meeting_id, course)
                                count_races += 1
                    self.logger.info("Ingested %d trot races for date %s", count_races, program_date)
        finally:
            self.db_manager.release_connection(conn)