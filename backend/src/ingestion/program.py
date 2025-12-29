import datetime as dt
import logging
import requests
from src.core.config import PROGRAMME_URL_TEMPLATE, HEADERS, STATUS_MAP, TRACK_MAP
from src.ingestion.base import BaseIngestor

class ProgramIngestor(BaseIngestor):
    """
    Ingests the daily race program, including meetings (reunions) and races (courses).
    """

    def fetch_programme_json(self) -> dict:
        """Fetches the full program JSON for the specific date."""
        url = PROGRAMME_URL_TEMPLATE.format(date_code=self.date_code)
        self.logger.info("Fetching programme JSON from %s", url)
        session = self._get_http_session()
        try:
            response = session.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error("CRITICAL: Failed to fetch programme: %s", e)
            raise e

    def _insert_daily_program(self, cursor, program_date: dt.date) -> int:
        """Inserts the daily program record and returns its ID."""
        cursor.execute(
            """
            INSERT INTO daily_program (program_date) VALUES (%s)
            ON CONFLICT (program_date) DO NOTHING RETURNING program_id;
            """,
            (program_date,)
        )
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("SELECT program_id FROM daily_program WHERE program_date = %s", (program_date,))
        return cursor.fetchone()[0]

    def _insert_race_meeting(self, cursor, program_id: int, meeting_data: dict) -> int:
        """Inserts a race meeting (Reunion) and returns its ID."""
        num_officiel = meeting_data.get("numOfficiel")
        meeting_type = self._safe_truncate("meeting_type", meeting_data.get("nature"), 50)
        racetrack_code = self._safe_truncate("racetrack_code", (meeting_data.get("hippodrome") or {}).get("code"), 10)
        temp = (meeting_data.get("meteo") or {}).get("temperature")
        wind = (meeting_data.get("meteo") or {}).get("directionVent")

        cursor.execute(
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
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute(
            "SELECT meeting_id FROM race_meeting WHERE program_id = %s AND meeting_number = %s",
            (program_id, num_officiel)
        )
        return cursor.fetchone()[0]

    def _insert_race(self, cursor, meeting_id: int, race_data: dict):
        """Inserts a single race record."""
        race_number = race_data.get("numOrdre")
        raw_status = race_data.get("statut")
        race_status = STATUS_MAP.get(raw_status, raw_status[:10] if raw_status else None)
        raw_track = race_data.get("typePiste")
        track_type = TRACK_MAP.get(raw_track, raw_track[:10] if raw_track else None)

        discipline = self._safe_truncate("discipline", race_data.get("discipline"), 20)
        race_status_category = self._safe_truncate("race_status_category", race_data.get("categorieStatut"), 50)
        race_category = race_data.get("categorieParticularite")
        distance_m = race_data.get("distance")
        
        penetrometre = race_data.get("penetrometre") or {}
        raw_val = penetrometre.get("valeurMesure")
        terrain_label = penetrometre.get("intitule")
        penetrometer_value = None
        if raw_val is not None:
            try:
                # Handle comma decimal separator often found in French data
                penetrometer_value = float(str(raw_val).replace(",", "."))
            except (ValueError, TypeError):
                pass

        declared_runners = race_data.get("nombreDeclaresPartants")
        conditions = race_data.get("conditions")
        duration_raw = race_data.get("dureeCourse")
        # Convert milliseconds to seconds
        race_duration_s = int(duration_raw) // 1000 if duration_raw else None

        cursor.execute(
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
        """Main entry point for program ingestion."""
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
            if not ts:
                self.logger.error(
                    "Skipping date %s due to missing 'date' timestamp in programme payload.",
                    self.date_code,
                )
                return
            try:
                program_date = dt.datetime.fromtimestamp(ts / 1000, tz=dt.timezone.utc).date()
            except (TypeError, ValueError, OSError, OverflowError):
                self.logger.error(
                    "Skipping date %s due to invalid 'date' timestamp in programme payload: %r",
                    self.date_code,
                    ts,
                )
                return

        conn = self.db_manager.get_connection()
        try:
            with conn:
                with conn.cursor() as cursor:
                    program_id = self._insert_daily_program(cursor, program_date)
                    meetings = programme.get("reunions", [])
                    self.logger.info("Found %d meetings.", len(meetings))
                    
                    count_races = 0
                    for meeting in meetings:
                        meeting_id = self._insert_race_meeting(cursor, program_id, meeting)
                        races = meeting.get("courses", [])
                        for race in races:
                            discipline = race.get("discipline", "").upper()
                            if discipline in ["ATTELE", "MONTE"]:
                                self._insert_race(cursor, meeting_id, race)
                                count_races += 1
                    self.logger.info("Ingested %d trot races for date %s", count_races, program_date)
        finally:
            self.db_manager.release_connection(conn)