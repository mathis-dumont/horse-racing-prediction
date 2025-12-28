"""
Database repositories.
"""
import datetime as dt
import logging
from typing import List, Dict, Any
import psycopg2.extras
from src.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class RaceRepository:
    """
    Access layer for Race Data.
    """

    def __init__(self) -> None:
        self.db_manager = DatabaseManager()

    def get_races_by_date(self, date_code: str) -> List[Dict[str, Any]]:
        try:
            target_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
        except ValueError:
            return []

        query = """
            SELECT r.race_id, rm.meeting_number, r.race_number, r.discipline, r.distance_m, rm.racetrack_code
            FROM race r
            JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
            JOIN daily_program dp ON rm.program_id = dp.program_id
            WHERE dp.program_date = %s
            ORDER BY rm.meeting_number, r.race_number;
        """
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (target_date,))
                return cur.fetchall()
        finally:
            self.db_manager.release_connection(conn)

    def get_participants_by_race(self, race_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT rp.pmu_number, h.horse_name, d.actor_name AS driver_name, t.actor_name AS trainer_name, rp.live_odds AS odds
            FROM race_participant rp
            JOIN horse h ON rp.horse_id = h.horse_id
            LEFT JOIN racing_actor d ON rp.driver_jockey_id = d.actor_id
            LEFT JOIN racing_actor t ON rp.trainer_id = t.actor_id
            WHERE rp.race_id = %s
            ORDER BY rp.pmu_number;
        """
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (race_id,))
                return cur.fetchall()
        finally:
            self.db_manager.release_connection(conn)

    def get_race_data_for_ml(self, race_id: int) -> List[Dict[str, Any]]:
        """
        Extrait TOUTES les données nécessaires au Pipeline ML.
        Inclut une sous-requête pour les stats historiques manquantes (hist_avg_speed, etc.)
        """
        query = """
            -- 1. Calcul des stats historiques pour les chevaux de CETTE course uniquement
            WITH horse_stats AS (
                SELECT 
                    horse_id,
                    COUNT(*) as hist_races,
                    AVG(finish_place) as hist_avg_rank,
                    AVG(reduction_km) as hist_avg_speed,
                    SUM(prize_money) as hist_earnings
                FROM horse_race_history
                WHERE horse_id IN (SELECT horse_id FROM race_participant WHERE race_id = %s)
                GROUP BY horse_id
            )
            
            SELECT 
                -- Identifiants
                rp.race_id, rp.pmu_number, h.horse_name,
                
                -- Features Course
                dp.program_date, r.distance_m, r.declared_runners_count,
                rm.racetrack_code, r.discipline, r.track_type,
                rm.weather_wind, rm.weather_temperature, r.terrain_label,
                
                -- Features Cheval (Directes)
                rp.age, rp.career_winnings, rp.career_races_count, h.birth_year,
                rp.reference_odds, rp.live_odds,
                
                -- Features Cheval (Calculées via CTE)
                COALESCE(hs.hist_avg_speed, 1.20) as hist_avg_speed, -- Valeur par défaut 1.20
                COALESCE(hs.hist_earnings, 0) as hist_earnings,
                COALESCE(hs.hist_races, 0) as hist_races,
                
                -- Features Categorical
                ls.code AS shoeing_status,
                h.sex,
                d.actor_name AS jockey_name,
                t.actor_name AS trainer_name

            FROM race_participant rp
            JOIN race r ON rp.race_id = r.race_id
            JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
            JOIN daily_program dp ON rm.program_id = dp.program_id
            JOIN horse h ON rp.horse_id = h.horse_id
            
            -- Jointure Stats Historiques
            LEFT JOIN horse_stats hs ON rp.horse_id = hs.horse_id
            
            -- Jointures Labels
            LEFT JOIN lookup_shoeing ls ON rp.shoeing_id = ls.shoeing_id
            LEFT JOIN racing_actor d ON rp.driver_jockey_id = d.actor_id
            LEFT JOIN racing_actor t ON rp.trainer_id = t.actor_id
            
            WHERE rp.race_id = %s
            ORDER BY rp.pmu_number;
        """
        
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # On passe race_id deux fois : une fois pour la sous-requête, une fois pour la principale
                cur.execute(query, (race_id, race_id))
                return cur.fetchall()
        except Exception as exc:
            logger.error(f"Database error in get_race_data_for_ml: {exc}")
            return []
        finally:
            self.db_manager.release_connection(conn)

    def get_daily_data_for_ml(self, date_code: str) -> List[Dict[str, Any]]:
        """
        VERSION OPTIMISÉE : Récupère TOUTES les données de la journée en une seule requête.
        """
        try:
            target_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
        except ValueError:
            return []

        query = """
            -- 1. Calcul des stats historiques pour TOUS les chevaux de la journée
            WITH horse_stats AS (
                SELECT 
                    horse_id,
                    COUNT(*) as hist_races,
                    AVG(finish_place) as hist_avg_rank,
                    AVG(reduction_km) as hist_avg_speed,
                    SUM(prize_money) as hist_earnings
                FROM horse_race_history
                WHERE horse_id IN (
                    SELECT rp.horse_id 
                    FROM race_participant rp
                    JOIN race r ON rp.race_id = r.race_id
                    JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
                    JOIN daily_program dp ON rm.program_id = dp.program_id
                    WHERE dp.program_date = %s
                )
                GROUP BY horse_id
            )
            
            SELECT 
                -- Identifiants pour le regroupement Python
                rp.race_id, r.race_number,
                rp.pmu_number, h.horse_name,
                
                -- Features Course
                dp.program_date, r.distance_m, r.declared_runners_count,
                rm.racetrack_code, r.discipline, r.track_type,
                rm.weather_wind, rm.weather_temperature, r.terrain_label,
                
                -- Features Cheval (Directes)
                rp.age, rp.career_winnings, rp.career_races_count, h.birth_year,
                rp.reference_odds, rp.live_odds,
                
                -- Features Cheval (Calculées via CTE)
                COALESCE(hs.hist_avg_speed, 1.20) as hist_avg_speed,
                COALESCE(hs.hist_earnings, 0) as hist_earnings,
                COALESCE(hs.hist_races, 0) as hist_races,
                
                -- Features Categorical
                ls.code AS shoeing_status,
                h.sex,
                d.actor_name AS jockey_name,
                t.actor_name AS trainer_name

            FROM race_participant rp
            JOIN race r ON rp.race_id = r.race_id
            JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
            JOIN daily_program dp ON rm.program_id = dp.program_id
            JOIN horse h ON rp.horse_id = h.horse_id
            
            LEFT JOIN horse_stats hs ON rp.horse_id = hs.horse_id
            LEFT JOIN lookup_shoeing ls ON rp.shoeing_id = ls.shoeing_id
            LEFT JOIN racing_actor d ON rp.driver_jockey_id = d.actor_id
            LEFT JOIN racing_actor t ON rp.trainer_id = t.actor_id
            
            WHERE dp.program_date = %s
            ORDER BY rp.race_id, rp.pmu_number;
        """
        
        conn = self.db_manager.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # On passe la date deux fois (une pour la CTE, une pour la requête principale)
                cur.execute(query, (target_date, target_date))
                return cur.fetchall()
        except Exception as exc:
            logger.error(f"Database error in get_daily_data_for_ml: {exc}")
            return []
        finally:
            self.db_manager.release_connection(conn)