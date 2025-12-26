import datetime as dt
import logging
import time
import random
import threading
import psycopg2.extras
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.config import PERF_URL_TEMPLATE, HEADERS, MAX_WORKERS
from src.ingestion.base import BaseIngestor, IngestStatus

class PerformancesIngestor(BaseIngestor):
    def __init__(self, date_code):
        super().__init__(date_code)
        self.horse_cache = {}
        self.cache_lock = threading.Lock()

    def _preload_horse_cache(self):
        conn = self.db_manager.get_connection()
        try:
            self.logger.info("PRE-WARMING: Loading Horse Cache...")
            start_t = time.time()
            with conn.cursor() as cur:
                cur.execute("SELECT horse_name, horse_id FROM horse")
                rows = cur.fetchall()
                with self.cache_lock:
                    for name, h_id in rows:
                        self.horse_cache[name] = h_id
            elapsed = time.time() - start_t
            self.logger.info(f"CACHE LOADED: {len(self.horse_cache)} horses in {elapsed:.2f}s.")
        except Exception as e:
            self.logger.error(f"Failed to preload cache: {e}")
        finally:
            self.db_manager.release_connection(conn)

    def _fetch_perf_json(self, session, meeting, race):
        url = PERF_URL_TEMPLATE.format(date=self.date_code, meeting=meeting, race=race)
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            if resp.status_code in [404, 204]: return {}, resp.status_code
            resp.raise_for_status()
            return resp.json(), 200
        except Exception as e:
            self.logger.warning("Network error R%sC%s: %s", meeting, race, e)
            return {}, 500

    def _get_horse_id_thread_safe(self, horse_name):
        if not horse_name: return None
        if horse_name in self.horse_cache: return self.horse_cache[horse_name]
        
        h_id = None
        tmp_conn = self.db_manager.get_connection()
        try:
            with tmp_conn:
                with tmp_conn.cursor() as tmp_cur:
                    tmp_cur.execute(
                        "INSERT INTO horse (horse_name) VALUES (%s) "
                        "ON CONFLICT (horse_name) DO NOTHING RETURNING horse_id", 
                        (horse_name,)
                    )
                    row = tmp_cur.fetchone()
                    if row:
                        h_id = row[0]
                    else:
                        tmp_cur.execute("SELECT horse_id FROM horse WHERE horse_name = %s", (horse_name,))
                        row = tmp_cur.fetchone()
                        if row: h_id = row[0]
        except Exception as e:
            self.logger.error(f"Error creating horse {horse_name}: {e}")
        finally:
            self.db_manager.release_connection(tmp_conn)
            
        if h_id:
            with self.cache_lock:
                self.horse_cache[horse_name] = h_id
            return h_id
        return None

    def _prepare_history_data(self, horse_id, history_item):
        if not horse_id: return None
        discipline = history_item.get("discipline", "").upper()
        if discipline not in ["ATTELE", "MONTE"]: return None
        
        race_date = None
        if history_item.get("date"):
            race_date = dt.datetime.fromtimestamp(history_item["date"] / 1000, tz=dt.timezone.utc).date()
        
        subject = next((p for p in history_item.get("participants", []) if p.get("itsHim")), None)
        finish_place, finish_status, jockey_weight, draw, red_km, dist_travel = None, None, None, None, None, None
        
        if subject:
            place_obj = subject.get("place")
            if isinstance(place_obj, dict):
                finish_place = place_obj.get("place")
                finish_status = place_obj.get("statusArrivee")
            jockey_weight = subject.get("poidsJockey")
            draw = subject.get("corde")
            red_km = subject.get("reductionKilometrique")
            dist_travel = subject.get("distanceParcourue")

        return (
            horse_id, race_date, history_item.get("discipline"), history_item.get("distance"),
            history_item.get("allocation"), history_item.get("tempsDuPremier"),
            finish_place, finish_status, jockey_weight, draw, red_km, dist_travel
        )

    def _process_single_race(self, meeting_num, race_num):
        time.sleep(random.uniform(0.1, 0.3))
        session = self._get_http_session()
        data, status_code = self._fetch_perf_json(session, meeting_num, race_num)
        
        if status_code in [204, 404]: return 0, IngestStatus.SKIPPED
        if status_code >= 500: return 0, IngestStatus.FAILED

        participants = []
        if isinstance(data, dict): participants = data.get("participants", [])
        elif isinstance(data, list): participants = data
        
        if not participants: return 0, IngestStatus.SKIPPED

        conn = None
        inserted_count = 0
        try:
            conn = self.db_manager.get_connection()
            with conn:
                with conn.cursor() as cur:
                    batch_values = []
                    for p in participants:
                        horse_name = p.get("nomCheval") or p.get("nom")
                        horse_id = self._get_horse_id_thread_safe(horse_name)
                        if not horse_id: continue
                        
                        for h in p.get("coursesCourues", []):
                            row_data = self._prepare_history_data(horse_id, h)
                            if row_data: batch_values.append(row_data)

                    if batch_values:
                        query = """
                            INSERT INTO horse_race_history (
                                horse_id, race_date, discipline, distance_m,
                                prize_money, first_place_time_s,
                                finish_place, finish_status, jockey_weight,
                                draw_number, reduction_km, distance_traveled_m
                            ) VALUES %s
                            ON CONFLICT (horse_id, race_date, discipline, distance_m) DO NOTHING
                        """
                        psycopg2.extras.execute_values(cur, query, batch_values)
                        inserted_count = len(batch_values)
            return inserted_count, IngestStatus.SUCCESS
        except Exception as e:
            self.logger.error("DB Error R%sC%s: %s", meeting_num, race_num, e)
            if conn: conn.rollback()
            self._save_failed_json(data, "performances", meeting_num, race_num)
            return 0, IngestStatus.FAILED
        finally:
            self.db_manager.release_connection(conn)

    def _get_races(self):
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT rm.meeting_number, r.race_number
                    FROM race r
                    JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
                    JOIN daily_program dp ON rm.program_id = dp.program_id
                    WHERE dp.program_date = %s
                    ORDER BY rm.meeting_number, r.race_number;
                """
                cur.execute(query, (dt.datetime.strptime(self.date_code, "%d%m%Y").date(),))
                return cur.fetchall()
        finally:
            self.db_manager.release_connection(conn)

    def ingest(self):
        self.db_manager.initialize_pool()
        self._preload_horse_cache()
        
        self.logger.info("Starting PARALLEL PERFORMANCE Ingestion for: %s", self.date_code)
        races = self._get_races()
        self.logger.info("Found %d races to process.", len(races))

        total_records, skipped, failed = 0, 0, 0
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_race = {
                executor.submit(self._process_single_race, m, r): (m, r)
                for m, r in races
            }

            for i, future in enumerate(as_completed(future_to_race), 1):
                try:
                    count, status = future.result()
                    if status == IngestStatus.SUCCESS: total_records += count
                    elif status == IngestStatus.SKIPPED: skipped += 1
                    elif status == IngestStatus.FAILED: failed += 1
                    
                    if i % 10 == 0:
                        self.logger.info("Progress: %d/%d. Skipped: %d.", i, len(races), skipped)
                except Exception as e:
                    self.logger.error("Thread Error: %s", e)
                    failed += 1

        self.logger.info("Ingestion Completed. Records: %d | Skipped: %d | Failed: %d", total_records, skipped, failed)
        self.logger.info("Time: %.2f seconds", time.time() - start_time)
        self.db_manager.close_pool()