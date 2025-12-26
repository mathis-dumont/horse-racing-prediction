"""
Data loader module responsible for extracting training data from the database.
"""
import logging
import pandas as pd
from src.core.database import DatabaseManager

class DataLoader:
    """
    Handles complex SQL queries to build the training dataset.
    """

    def __init__(self) -> None:
        """Initialize with a logger and database connection."""
        self.logger = logging.getLogger("ML.Loader")
        self.db_manager = DatabaseManager()

    def get_training_data(self) -> pd.DataFrame:
        """
        Fetches raw data, calculates historical statistics, and merges them 
        into a final DataFrame for training.

        Returns:
            pd.DataFrame: The complete dataset ready for the pipeline.
        """
        self.logger.info("Extracting data from SQL...")
        connection = self.db_manager.get_connection()
        
        try:
            # 1. Main Data Retrieval (Participants & Race Context)
            query_main = """
            SELECT
                rp.participant_id, rp.race_id, rp.horse_id, rp.finish_rank,
                CASE WHEN rp.finish_rank = 1 THEN 1 ELSE 0 END AS is_winner,
                dp.program_date, rm.racetrack_code, rm.weather_temperature, rm.weather_wind,
                r.race_number, r.discipline, r.distance_m, r.track_type, r.terrain_label, r.declared_runners_count,
                h.birth_year, h.sex,
                rp.pmu_number, rp.age, rp.career_winnings, rp.career_races_count, rp.trainer_advice,
                rp.reference_odds, rp.live_odds,
                ls.code AS shoeing_status,
                j.actor_name AS jockey_name,
                t.actor_name AS trainer_name
            FROM race_participant rp
            JOIN race r ON rp.race_id = r.race_id
            JOIN race_meeting rm ON r.meeting_id = rm.meeting_id
            JOIN daily_program dp ON rm.program_id = dp.program_id
            JOIN horse h ON rp.horse_id = h.horse_id
            LEFT JOIN lookup_shoeing ls ON rp.shoeing_id = ls.shoeing_id
            LEFT JOIN racing_actor j ON rp.driver_jockey_id = j.actor_id
            LEFT JOIN racing_actor t ON rp.trainer_id = t.actor_id
            WHERE rp.finish_rank IS NOT NULL
            """
            main_df = pd.read_sql(query_main, connection)
            main_df['program_date'] = pd.to_datetime(main_df['program_date'])

            # 2. Historical Data Retrieval
            query_history = """
            SELECT horse_id, finish_place, reduction_km, prize_money 
            FROM horse_race_history
            """
            history_df = pd.read_sql(query_history, connection)

            # 3. Calculate Historical Statistics (Aggregations)
            self.logger.info("Calculating historical aggregates...")
            horse_stats = history_df.groupby('horse_id').agg({
                'finish_place': ['count', 'mean'],
                'reduction_km': ['mean', 'min'],
                'prize_money': 'sum'
            }).reset_index()
            
            # Flatten MultiIndex columns
            horse_stats.columns = [
                'horse_id', 'hist_races', 'hist_avg_rank', 
                'hist_avg_speed', 'hist_best_speed', 'hist_earnings'
            ]
            
            # Impute missing speed with a safe default
            horse_stats['hist_avg_speed'] = horse_stats['hist_avg_speed'].fillna(1.20)

            # 4. Merge DataSets
            self.logger.info("Merging Main Data with History...")
            final_df = pd.merge(main_df, horse_stats, on='horse_id', how='left')
            
            # Basic filling for stats (other NaN handling occurs in pipeline)
            final_df['hist_races'] = final_df['hist_races'].fillna(0)
            final_df['hist_earnings'] = final_df['hist_earnings'].fillna(0)

            return final_df
            
        except Exception as exc:
            self.logger.error(f"Failed to load training data: {exc}")
            return pd.DataFrame()
            
        finally:
            self.db_manager.release_connection(connection)