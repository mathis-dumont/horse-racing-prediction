import datetime as dt
import logging
import time
import random
import threading
import psycopg2
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.config import PARTICIPANTS_URL_TEMPLATE, HEADERS, INCIDENT_MAP, SHOE_MAP, MAX_WORKERS
from src.ingestion.base import BaseIngestor, IngestStatus

class ParticipantsIngestor(BaseIngestor):
    """
    Ingests race participants (horses, drivers, trainers) and related metadata
    (shoeing, incidents, odds).
    """

    def __init__(self, date_code):
        super().__init__(date_code)
        # Caches to reduce DB load for high-frequency lookups
        self.horse_cache = {}
        self.actor_cache = {}
        self.shoeing_cache = {}
        self.incident_cache = {}
        self.cache_lock = threading.Lock()

    def _preload_caches(self):
        """
        Loads existing horses, actors, shoeing codes, and incidents from the database 
        into memory to minimize redundant SELECT queries during ingestion.
        """
        self.logger.info("PRE-WARMING: Loading Entity Caches (Horses/Actors)...")
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                self.logger.info("Loading Horses into RAM...")
                cursor.execute("SELECT horse_name, horse_id FROM horse")
                for name, horse_id in cursor.fetchall():
                    self.horse_cache[name] = horse_id
                
                self.logger.info("Loading Actors into RAM...")
                cursor.execute("SELECT actor_name, actor_id FROM racing_actor")
                for name, actor_id in cursor.fetchall():
                    self.actor_cache[name] = actor_id
                    
                cursor.execute("SELECT code, shoeing_id FROM lookup_shoeing")
                for code, shoeing_id in cursor.fetchall():
                    self.shoeing_cache[code] = shoeing_id
                    
                cursor.execute("SELECT code, incident_id FROM lookup_incident")
                for code, incident_id in cursor.fetchall():
                    self.incident_cache[code] = incident_id
            
            self.logger.info(f"CACHE READY: {len(self.horse_cache)} Horses, {len(self.actor_cache)} Actors loaded.")
        except Exception as e:
            self.logger.error(f"Cache Pre-warm failed: {e}")
        finally:
            self.db_manager.release_connection(conn)

    def _fetch_participants_json(self, session, meeting_num, race_num):
        """Fetches the participants JSON data from the external API."""
        url = PARTICIPANTS_URL_TEMPLATE.format(date=self.date_code, meeting=meeting_num, race=race_num)
        try:
            response = session.get(url, headers=HEADERS, timeout=10)
            if response.status_code in [404, 204]:
                return [], response.status_code
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, dict):
                return data.get("participants", []), 200
            
            # Handling edge case where API returns a list directly
            return (data, 200) if isinstance(data, list) else ([], 200)
        except Exception as e:
            self.logger.warning(f"Failed to fetch R{meeting_num}C{race_num}: {e}")
            return None, 500

    def _get_or_create_horse(self, participant_data):
        """
        Retrieves a horse ID from cache/DB or creates a new record if it doesn't exist.
        """
        name = participant_data.get("nom")
        if not name:
            return None
        
        if name in self.horse_cache:
            return self.horse_cache[name]

        age = participant_data.get("age")
        # Determine birth year based on current year and age
        # TODO: Verify if this logic holds for races processed historically (vs current date).
        birth_year = (dt.datetime.now(tz=dt.timezone.utc).year - int(age)) if age else None
        
        raw_sex = participant_data.get("sexe")
        clean_sex = raw_sex[0].upper() if raw_sex else None
        
        horse_id = None
        tmp_conn = self.db_manager.get_connection()
        try:
            with tmp_conn:
                with tmp_conn.cursor() as tmp_cur:
                    # Try to insert; if conflict, do nothing
                    tmp_cur.execute(
                        "INSERT INTO horse (horse_name, sex, birth_year) VALUES (%s, %s, %s) "
                        "ON CONFLICT (horse_name) DO NOTHING RETURNING horse_id;",
                        (name, clean_sex, birth_year)
                    )
                    row = tmp_cur.fetchone()
                    if row:
                        horse_id = row[0]
                    else:
                        # Fallback: Record exists, fetch ID
                        tmp_cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (name,))
                        res = tmp_cur.fetchone()
                        horse_id = res[0] if res else None
        finally:
            self.db_manager.release_connection(tmp_conn)
        
        if horse_id:
            with self.cache_lock:
                self.horse_cache[name] = horse_id
        return horse_id

    def _get_or_create_actor(self, name):
        """
        Retrieves an actor (trainer/driver) ID from cache/DB or creates a new record.
        """
        clean_name = self._safe_truncate("actor_name", name, 100)
        if not clean_name:
            return None
        
        if clean_name in self.actor_cache:
            return self.actor_cache[clean_name]
        
        actor_id = None
        tmp_conn = self.db_manager.get_connection()
        try:
            with tmp_conn:
                with tmp_conn.cursor() as tmp_cur:
                    tmp_cur.execute(
                        "INSERT INTO racing_actor (actor_name) VALUES (%s) "
                        "ON CONFLICT (actor_name) DO NOTHING RETURNING actor_id;",
                        (clean_name,)
                    )
                    row = tmp_cur.fetchone()
                    if row:
                        actor_id = row[0]
                    else:
                        tmp_cur.execute("SELECT actor_id FROM racing_actor WHERE actor_name = %s", (clean_name,))
                        res = tmp_cur.fetchone()
                        actor_id = res[0] if res else None
        finally:
            self.db_manager.release_connection(tmp_conn)
            
        if actor_id:
            with self.cache_lock:
                self.actor_cache[clean_name] = actor_id
        return actor_id

    def _get_or_create_shoeing(self, code):
        """Retrieves or creates a shoeing configuration ID."""
        if not code:
            return None
        if code in self.shoeing_cache:
            return self.shoeing_cache[code]
        
        shoeing_id = None
        tmp_conn = self.db_manager.get_connection()
        try:
            with tmp_conn:
                with tmp_conn.cursor() as tmp_cur:
                    tmp_cur.execute(
                        "INSERT INTO lookup_shoeing (code) VALUES (%s) "
                        "ON CONFLICT (code) DO NOTHING RETURNING shoeing_id;", (code,)
                    )
                    row = tmp_cur.fetchone()
                    if row:
                        shoeing_id = row[0]
                    else:
                        tmp_cur.execute("SELECT shoeing_id FROM lookup_shoeing WHERE code=%s", (code,))
                        res = tmp_cur.fetchone()
                        shoeing_id = res[0] if res else None
        finally:
            self.db_manager.release_connection(tmp_conn)
            
        if shoeing_id:
            with self.cache_lock:
                self.shoeing_cache[code] = shoeing_id
        return shoeing_id

    def _get_or_create_incident(self, code):
        """Retrieves or creates an incident type ID."""
        if not code:
            return None
        if code in self.incident_cache:
            return self.incident_cache[code]
        
        incident_id = None
        tmp_conn = self.db_manager.get_connection()
        try:
            with tmp_conn:
                with tmp_conn.cursor() as tmp_cur:
                    tmp_cur.execute(
                        "INSERT INTO lookup_incident (code) VALUES (%s) "
                        "ON CONFLICT (code) DO NOTHING RETURNING incident_id;", (code,)
                    )
                    row = tmp_cur.fetchone()
                    if row:
                        incident_id = row[0]
                    else:
                        tmp_cur.execute("SELECT incident_id FROM lookup_incident WHERE code=%s", (code,))
                        res = tmp_cur.fetchone()
                        incident_id = res[0] if res else None
        finally:
            self.db_manager.release_connection(tmp_conn)
        
        if incident_id:
            with self.cache_lock:
                self.incident_cache[code] = incident_id
        return incident_id

    def _insert_participant(self, cursor, race_id, participant_data):
        """Parses participant JSON data and inserts into race_participant table."""
        p_num = participant_data.get("numPmu")
        
        raw_incident = participant_data.get("incident")
        clean_incident = INCIDENT_MAP.get(raw_incident, raw_incident[:20] if raw_incident else None)
        
        raw_shoe = participant_data.get("deferre")
        clean_shoe = SHOE_MAP.get(raw_shoe, raw_shoe[:10] if raw_shoe else None)

        horse_id = self._get_or_create_horse(participant_data)
        if not horse_id:
            return
            
        trainer_id = self._get_or_create_actor(participant_data.get("entraineur"))
        driver_id = self._get_or_create_actor(participant_data.get("driver"))
        incident_id = self._get_or_create_incident(clean_incident)
        shoeing_id = self._get_or_create_shoeing(clean_shoe)

        raw_sex = participant_data.get("sexe")
        clean_sex = raw_sex[0].upper() if raw_sex else None
        
        raw_red_km = participant_data.get("reductionKilometrique")
        try:
            clean_red_km = float(raw_red_km) if raw_red_km is not None else None
        except:
            clean_red_km = None
        
        career_winnings = self._to_euros((participant_data.get("gainsParticipant") or {}).get("gainsCarriere"))
        
        ref_odds = (participant_data.get("dernierRapportReference") or {}).get("rapport")
        live_odds = (participant_data.get("dernierRapportDirect") or {}).get("rapport")

        cursor.execute(
            """
            INSERT INTO race_participant (
                race_id, horse_id, pmu_number, age, sex,
                trainer_id, driver_jockey_id, shoeing_id, incident_id,
                career_races_count, career_winnings, reference_odds, live_odds,
                raw_performance_string, trainer_advice, finish_rank,
                time_achieved_s, reduction_km
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (race_id, pmu_number) DO NOTHING;
            """,
            (
                race_id, horse_id, p_num, participant_data.get("age"), clean_sex,
                trainer_id, driver_id, shoeing_id, incident_id,
                participant_data.get("nombreCourses"), career_winnings,
                ref_odds, live_odds,
                participant_data.get("musique"), participant_data.get("avisEntraineur"), participant_data.get("ordreArrivee"),
                participant_data.get("tempsObtenu"), clean_red_km
            )
        )

    def _process_single_race(self, race_id, meeting_num, race_num):
        """Worker method to process participants for a single race."""
        # Random sleep to prevent API throttling
        time.sleep(random.uniform(0.1, 0.3))
        session = self._get_http_session()
        participants, status_code = self._fetch_participants_json(session, meeting_num, race_num)
        
        if status_code in [204, 404]:
            return 0, IngestStatus.SKIPPED
        if participants is None:
            return 0, IngestStatus.FAILED

        conn = None
        max_retries = 3
        for _ in range(max_retries):
            try:
                conn = self.db_manager.get_connection()
                with conn:
                    with conn.cursor() as cursor:
                        for p_data in participants:
                            self._insert_participant(cursor, race_id, p_data)
                return len(participants), IngestStatus.SUCCESS
            except psycopg2.errors.DeadlockDetected:
                if conn:
                    conn.rollback()
                time.sleep(random.uniform(0.5, 1.5))
                continue
            except Exception as e:
                self.logger.error(f"DB Error R{meeting_num}C{race_num}: {e}")
                if conn:
                    conn.rollback()
                self._save_failed_json(participants, "participants", meeting_num, race_num)
                return 0, IngestStatus.FAILED
            finally:
                self.db_manager.release_connection(conn)
                conn = None
        return 0, IngestStatus.FAILED

    def _get_races(self):
        """Retrieves the list of races to ingest for the date_code."""
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT r.race_id, rm.meeting_number, r.race_number
                    FROM race r
                    JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
                    JOIN daily_program dp ON rm.program_id = dp.program_id
                    WHERE dp.program_date = %s
                    AND r.discipline IN ('ATTELE', 'MONTE')
                    ORDER BY rm.meeting_number, r.race_number;
                    """,
                    (dt.datetime.strptime(self.date_code, "%d%m%Y").date(),)
                )
                return cursor.fetchall()
        finally:
            self.db_manager.release_connection(conn)

    def ingest(self):
        """Main entry point for parallel participants ingestion."""
        self.db_manager.initialize_pool()
        self._preload_caches()
        
        self.logger.info(f"Starting PARALLEL PARTICIPANTS ingestion for {self.date_code}")
        races = self._get_races()
        self.logger.info(f"Processing {len(races)} races.")

        total_inserted, total_skipped, total_failed = 0, 0, 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_race = {
                executor.submit(self._process_single_race, r_id, m, r): (m, r)
                for r_id, m, r in races
            }

            for future in as_completed(future_to_race):
                try:
                    count, status = future.result()
                    if status == IngestStatus.SUCCESS:
                        total_inserted += count
                    elif status == IngestStatus.SKIPPED_NO_CONTENT:
                        total_skipped += 1
                    else:
                        total_failed += 1
                except Exception as e:
                    self.logger.error(f"Exception: {e}")
                    total_failed += 1
        
        self.logger.info(f"Ingestion Completed. Records: {total_inserted} | Skipped: {total_skipped} | Failed: {total_failed}")
        self.db_manager.close_pool()