import os
import logging
import pandas as pd
from sqlalchemy import create_engine, Engine
from src.core.config import DB_URL 

class DataLoader:
    """
    Robust Data Manager using SQLAlchemy.
    Responsible for loading raw data (Participants + History) and performing the initial merge.
    """

    def __init__(self) -> None:
        """
        Initializes the database connection using environment variables.
        """

        self.logger = logging.getLogger("ML.Loader")
        
        if not DB_URL:
            raise ValueError("DB_URL is missing in the .env file")
            
        self.engine: Engine = create_engine(DB_URL)

    def get_training_data(self) -> pd.DataFrame:
        """
        Extracts and merges participant data with aggregated historical statistics.
        
        Returns:
            pd.DataFrame: The merged dataset sorted by program date.
        """
        self.logger.info("Loading SQL data...")
        
        try:
            with self.engine.connect() as connection:
                # 1. Main Dataset (Optimized Query)
                # Note: SQL Column aliases are preserved to ensure downstream compatibility.
                query_main = """
                SELECT
                    rp.participant_id, rp.race_id, rp.horse_id,
                    rp.finish_rank,
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

                # 2. History Dataset & Aggregation
                self.logger.info("Calculating historical statistics...")
                query_history = """
                SELECT horse_id, finish_place, reduction_km, prize_money 
                FROM horse_race_history
                """
                history_df = pd.read_sql(query_history, connection)
                
                # Optimized statistics calculation
                horse_stats = history_df.groupby('horse_id').agg({
                    'finish_place': ['count', 'mean'],
                    'reduction_km': ['mean', 'min'],
                    'prize_money': 'sum'
                }).reset_index()
                
                # Flatten MultiIndex columns and rename
                horse_stats.columns = [
                    'horse_id', 'hist_races', 'hist_avg_rank', 
                    'hist_avg_speed', 'hist_best_speed', 'hist_earnings'
                ]
                
                # Default value for speed (1.20 = slow/standard context)
                horse_stats['hist_avg_speed'] = horse_stats['hist_avg_speed'].fillna(1.20)

                # 3. Merge
                self.logger.info("Merging datasets...")
                final_df = pd.merge(main_df, horse_stats, on='horse_id', how='left')
                
                # Basic handling of NULLs post-merge (for "new" horses not in history)
                final_df['hist_races'] = final_df['hist_races'].fillna(0)
                final_df['hist_earnings'] = final_df['hist_earnings'].fillna(0)
                
                return final_df.sort_values('program_date')

        except Exception as error:
            self.logger.error(f"Critical error while loading data: {error}")
            raise error