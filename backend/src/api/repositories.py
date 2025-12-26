"""
Database repositories for handling data access logic.
"""
import datetime as dt
import logging
from typing import List, Dict, Any, Optional

import psycopg2.extras

from src.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class RaceRepository:
    """
    Repository for accessing race and participant data from PostgreSQL.
    """

    def __init__(self) -> None:
        """Initialize the repository with a database manager."""
        self.db_manager = DatabaseManager()

    def get_races_by_date(self, date_code: str) -> List[Dict[str, Any]]:
        """
        Retrieves a list of races for a specific date.

        Args:
            date_code (str): Date string in 'DDMMYYYY' format.

        Returns:
            List[Dict[str, Any]]: A list of race summaries.
        """
        try:
            target_date = dt.datetime.strptime(date_code, "%d%m%Y").date()
        except ValueError:
            logger.warning(f"Invalid date format received: {date_code}")
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

        connection = self.db_manager.get_connection()
        try:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (target_date,))
                return cursor.fetchall()
        except Exception as exc:
            logger.error(f"Database error in get_races_by_date: {exc}")
            return []
        finally:
            self.db_manager.release_connection(connection)

    def get_participants_by_race(self, race_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves basic participant details for a specific race.

        Args:
            race_id (int): The unique identifier of the race.

        Returns:
            List[Dict[str, Any]]: A list of participants.
        """
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

        connection = self.db_manager.get_connection()
        try:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (race_id,))
                return cursor.fetchall()
        except Exception as exc:
            logger.error(f"Database error in get_participants_by_race: {exc}")
            return []
        finally:
            self.db_manager.release_connection(connection)

    def get_race_data_for_ml(self, race_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves comprehensive data required for the XGBoost inference pipeline.
        
        This includes context features (weather, track) and participant features 
        (history, stats).

        Args:
            race_id (int): The unique identifier of the race.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing raw features 
            for the machine learning model.
        """
        query = """
            SELECT 
                -- Identifiants
                rp.race_id,  -- TRES IMPORTANT
                rp.pmu_number,
                h.horse_name,
                
                -- Features Course (Context)
                dp.program_date,
                r.distance_m,
                r.declared_runners_count,
                rm.racetrack_code,
                r.discipline,
                r.track_type,
                rm.weather_wind,
                r.terrain_label,
                
                -- Features Cheval (Numeric)
                rp.age,
                rp.career_winnings,
                rp.career_races_count,
                h.birth_year,
                rp.reference_odds,
                
                -- Features Cheval (Categorical)
                ls.code AS shoeing_status,
                h.sex,
                d.actor_name AS jockey_name,
                t.actor_name AS trainer_name

            FROM race_participant rp
            JOIN race r ON rp.race_id = r.race_id
            JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
            JOIN daily_program dp ON rm.program_id = dp.program_id
            JOIN horse h ON rp.horse_id = h.horse_id
            LEFT JOIN lookup_shoeing ls ON rp.shoeing_id = ls.shoeing_id
            LEFT JOIN racing_actor d ON rp.driver_jockey_id = d.actor_id
            LEFT JOIN racing_actor t ON rp.trainer_id = t.actor_id
            
            WHERE rp.race_id = %s
            ORDER BY rp.pmu_number;
        """
        
        connection = self.db_manager.get_connection()
        try:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (race_id,))
                return cursor.fetchall()
        except Exception as exc:
            logger.error(f"Database error in get_race_data_for_ml: {exc}")
            return []
        finally:
            self.db_manager.release_connection(connection)