import datetime as dt
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.config import RAPPORTS_URL_TEMPLATE, HEADERS, BET_TYPE_MAP, MAX_WORKERS
from src.ingestion.base import BaseIngestor, IngestStatus

class RapportsIngestor(BaseIngestor):
    def _fetch_rapports_json(self, session, meeting, race):
        url = RAPPORTS_URL_TEMPLATE.format(date=self.date_code, meeting=meeting, race=race)
        try:
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code in [404, 204]: return [], resp.status_code
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list): return data, 200
            return data.get("rapportsDefinitifs", []), 200
        except Exception as e:
            self.logger.warning(f"Failed fetching reports R{meeting}C{race}: {e}")
            return [], 500

    def _insert_race_bet(self, cur, race_id, bet):
        raw_type = bet.get("typePari")
        clean_type = BET_TYPE_MAP.get(raw_type)
        if clean_type is None:
            if raw_type:
                if len(raw_type) > 10:
                    truncated = raw_type[:10]
                    self.logger.warning(
                        "Bet type '%s' not found in BET_TYPE_MAP; truncating to '%s'.",
                        raw_type,
                        truncated,
                    )
                    clean_type = truncated
                else:
                    clean_type = raw_type[:10]
            else:
                clean_type = None
        stake_euros = self._to_euros(bet.get("miseBase"))

        cur.execute(
            """
            INSERT INTO race_bet (race_id, bet_type, bet_family, base_stake, is_refunded)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (race_id, bet_type) DO NOTHING
            RETURNING bet_id;
            """,
            (
                race_id, 
                clean_type, 
                bet.get("famillePari"),
                stake_euros, 
                bet.get("rembourse")
            )
        )
        row = cur.fetchone()
        if row: return row[0]
        cur.execute("SELECT bet_id FROM race_bet WHERE race_id = %s AND bet_type = %s", (race_id, clean_type))
        res = cur.fetchone()
        return res[0] if res else None

    def _insert_bet_report(self, cur, bet_id, r):
        if not bet_id: return
        div_euros = self._to_euros(r.get("dividende"))
        div_1e_euros = self._to_euros(r.get("dividendePourUnEuro"))

        cur.execute(
            """
            INSERT INTO bet_report (bet_id, combination, dividend, dividend_per_1e, winners_count)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (bet_id, combination) DO NOTHING;
            """,
            (
                bet_id, 
                r.get("combinaison"), 
                div_euros, 
                div_1e_euros, 
                r.get("nombreGagnants")
            )
        )

    def _process_single_race(self, race_id, meeting_num, race_num):
        time.sleep(random.uniform(0.1, 0.3))
        session = self._get_http_session()
        bets, status_code = self._fetch_rapports_json(session, meeting_num, race_num)
        
        if status_code in [204, 404]: return 0, IngestStatus.SKIPPED
        if not bets and status_code == 200: return 0, IngestStatus.SUCCESS
        if status_code >= 500: return 0, IngestStatus.FAILED

        conn = None
        count_bets = 0
        try:
            conn = self.db_manager.get_connection()
            with conn:
                with conn.cursor() as cur:
                    for bet in bets:
                        bet_id = self._insert_race_bet(cur, race_id, bet)
                        count_bets += 1
                        for r in bet.get("rapports", []):
                            self._insert_bet_report(cur, bet_id, r)
            return count_bets, IngestStatus.SUCCESS
        except Exception as e:
            self.logger.error(f"DB Error Bets R{meeting_num}C{race_num}: {e}")
            if conn: conn.rollback()
            self._save_failed_json(bets, "rapports", meeting_num, race_num)
            return 0, IngestStatus.FAILED
        finally:
            self.db_manager.release_connection(conn)

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
        self.logger.info(f"Starting PARALLEL RAPPORTS ingestion for {self.date_code}")
        races = self._get_races()
        self.logger.info(f"Processing {len(races)} races.")

        total_bets, skipped, failed = 0, 0, 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_race = {
                executor.submit(self._process_single_race, r_id, m, r): (m, r)
                for r_id, m, r in races
            }
            for future in as_completed(future_to_race):
                try:
                    count, status = future.result()
                    if status == IngestStatus.SUCCESS: total_bets += count
                    elif status == IngestStatus.SKIPPED: skipped += 1
                    else: failed += 1
                except Exception as e:
                    self.logger.error(f"Thread Error: {e}")
                    failed += 1

        self.logger.info(f"Ingestion Completed. Bets: {total_bets} | Skipped: {skipped} | Failed: {failed}")
        self.db_manager.close_pool()