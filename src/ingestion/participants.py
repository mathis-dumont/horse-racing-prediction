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
    def __init__(self, date_code):
        super().__init__(date_code)
        self.horse_cache = {}
        self.actor_cache = {}
        self.shoeing_cache = {}
        self.incident_cache = {}
        self.cache_lock = threading.Lock()

    def _preload_caches(self):
        self.logger.info("PRE-WARMING: Loading Entity Caches (Horses/Actors)...")
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                self.logger.info("Loading Horses into RAM...")
                cur.execute("SELECT horse_name, horse_id FROM horse")
                for name, h_id in cur.fetchall():
                    self.horse_cache[name] = h_id
                
                self.logger.info("Loading Actors into RAM...")
                cur.execute("SELECT actor_name, actor_id FROM racing_actor")
                for name, a_id in cur.fetchall():
                    self.actor_cache[name] = a_id
                    
                cur.execute("SELECT code, shoeing_id FROM lookup_shoeing")
                for code, s_id in cur.fetchall():
                    self.shoeing_cache[code] = s_id
                    
                cur.execute("SELECT code, incident_id FROM lookup_incident")
                for code, i_id in cur.fetchall():
                    self.incident_cache[code] = i_id
            self.logger.info(f"CACHE READY: {len(self.horse_cache)} Horses, {len(self.actor_cache)} Actors loaded.")
        except Exception as e:
            self.logger.error(f"Cache Pre-warm failed: {e}")
        finally:
            self.db_manager.release_connection(conn)

    def _fetch_participants_json(self, session, meeting_num, race_num):
        url = PARTICIPANTS_URL_TEMPLATE.format(date=self.date_code, meeting=meeting_num, race=race_num)
        try:
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code in [404, 204]: return [], resp.status_code
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict): return data.get("participants", []), 200
            return (data, 200) if isinstance(data, list) else ([], 200)
        except Exception as e:
            self.logger.warning(f"Failed to fetch R{meeting_num}C{race_num}: {e}")
            return None, 500

    def _get_or_create_horse(self, p):
        name = p.get("nom")
        if not name: return None
        if name in self.horse_cache: return self.horse_cache[name]

        age = p.get("age")
        birth_year = (dt.datetime.now(tz=dt.timezone.utc).year - int(age)) if age else None
        raw_sex = p.get("sexe")
        clean_sex = raw_sex[0].upper() if raw_sex else None
        
        h_id = None
        tmp_conn = self.db_manager.get_connection()
        try:
            with tmp_conn:
                with tmp_conn.cursor() as tmp_cur:
                    tmp_cur.execute(
                        "INSERT INTO horse (horse_name, sex, birth_year) VALUES (%s, %s, %s) "
                        "ON CONFLICT (horse_name) DO NOTHING RETURNING horse_id;",
                        (name, clean_sex, birth_year)
                    )
                    row = tmp_cur.fetchone()
                    if row:
                        h_id = row[0]
                    else:
                        tmp_cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (name,))
                        res = tmp_cur.fetchone()
                        h_id = res[0] if res else None
        finally:
            self.db_manager.release_connection(tmp_conn)
        
        if h_id:
            with self.cache_lock:
                self.horse_cache[name] = h_id
        return h_id

    def _get_or_create_actor(self, name):
        clean_name = self._safe_truncate("actor_name", name, 100)
        if not clean_name: return None
        if clean_name in self.actor_cache: return self.actor_cache[clean_name]
        
        a_id = None
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
                        a_id = row[0]
                    else:
                        tmp_cur.execute("SELECT actor_id FROM racing_actor WHERE actor_name = %s", (clean_name,))
                        res = tmp_cur.fetchone()
                        a_id = res[0] if res else None
        finally:
            self.db_manager.release_connection(tmp_conn)
            
        if a_id:
            with self.cache_lock:
                self.actor_cache[clean_name] = a_id
        return a_id

    def _get_or_create_shoeing(self, code):
        if not code: return None
        if code in self.shoeing_cache: return self.shoeing_cache[code]
        s_id = None
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
                        s_id = row[0]
                    else:
                        tmp_cur.execute("SELECT shoeing_id FROM lookup_shoeing WHERE code=%s", (code,))
                        res = tmp_cur.fetchone()
                        s_id = res[0] if res else None
        finally:
            self.db_manager.release_connection(tmp_conn)
        if s_id:
            with self.cache_lock:
                self.shoeing_cache[code] = s_id
        return s_id

    def _get_or_create_incident(self, code):
        if not code: return None
        if code in self.incident_cache: return self.incident_cache[code]
        i_id = None
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
                        i_id = row[0]
                    else:
                        tmp_cur.execute("SELECT incident_id FROM lookup_incident WHERE code=%s", (code,))
                        res = tmp_cur.fetchone()
                        i_id = res[0] if res else None
        finally:
            self.db_manager.release_connection(tmp_conn)
        if i_id:
            with self.cache_lock:
                self.incident_cache[code] = i_id
        return i_id

    def _insert_participant(self, cur, race_id, p):
        p_num = p.get("numPmu")
        raw_inc = p.get("incident")
        clean_inc = INCIDENT_MAP.get(raw_inc, raw_inc[:20] if raw_inc else None)
        raw_shoe = p.get("deferre")
        clean_shoe = SHOE_MAP.get(raw_shoe, raw_shoe[:10] if raw_shoe else None)

        horse_id = self._get_or_create_horse(p)
        if not horse_id: return
        trainer_id = self._get_or_create_actor(p.get("entraineur"))
        driver_id = self._get_or_create_actor(p.get("driver"))
        incident_id = self._get_or_create_incident(clean_inc)
        shoeing_id = self._get_or_create_shoeing(clean_shoe)

        raw_sex = p.get("sexe")
        clean_sex = raw_sex[0].upper() if raw_sex else None
        
        raw_red_km = p.get("reductionKilometrique")
        try:
            clean_red_km = float(raw_red_km) if raw_red_km is not None else None
        except:
            clean_red_km = None
        
        career_winnings = self._to_euros((p.get("gainsParticipant") or {}).get("gainsCarriere"))
        
        ref_odds = (p.get("dernierRapportReference") or {}).get("rapport")
        live_odds = (p.get("dernierRapportDirect") or {}).get("rapport")

        cur.execute(
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
                race_id, horse_id, p_num, p.get("age"), clean_sex,
                trainer_id, driver_id, shoeing_id, incident_id,
                p.get("nombreCourses"), career_winnings,
                ref_odds, live_odds,
                p.get("musique"), p.get("avisEntraineur"), p.get("ordreArrivee"),
                p.get("tempsObtenu"), clean_red_km
            )
        )

    def _process_single_race(self, race_id, meeting_num, race_num):
        time.sleep(random.uniform(0.1, 0.3))
        session = self._get_http_session()
        participants, status_code = self._fetch_participants_json(session, meeting_num, race_num)
        
        if status_code in [204, 404]: return 0, IngestStatus.SKIPPED
        if participants is None: return 0, IngestStatus.FAILED

        conn = None
        max_retries = 3
        for _ in range(max_retries):
            try:
                conn = self.db_manager.get_connection()
                with conn:
                    with conn.cursor() as cur:
                        for p in participants:
                            self._insert_participant(cur, race_id, p)
                return len(participants), IngestStatus.SUCCESS
            except psycopg2.errors.DeadlockDetected:
                if conn: conn.rollback()
                time.sleep(random.uniform(0.5, 1.5))
                continue
            except Exception as e:
                self.logger.error(f"DB Error R{meeting_num}C{race_num}: {e}")
                if conn: conn.rollback()
                self._save_failed_json(participants, "participants", meeting_num, race_num)
                return 0, IngestStatus.FAILED
            finally:
                self.db_manager.release_connection(conn)
                conn = None
        return 0, IngestStatus.FAILED

    def _get_races(self):
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
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
                return cur.fetchall()
        finally:
            self.db_manager.release_connection(conn)

    def ingest(self):
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
                    if status == IngestStatus.SUCCESS: total_inserted += count
                    elif status == IngestStatus.SKIPPED_NO_CONTENT: total_skipped += 1
                    else: total_failed += 1
                except Exception as e:
                    self.logger.error(f"Exception: {e}")
                    total_failed += 1
        
        self.logger.info(f"Ingestion Completed. Records: {total_inserted} | Skipped: {total_skipped} | Failed: {total_failed}")
        self.db_manager.close_pool()