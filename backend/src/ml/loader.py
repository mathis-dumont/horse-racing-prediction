import os
import logging
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

class DataLoader:
    """
    Gestionnaire de données robuste utilisant SQLAlchemy.
    Charge les données brutes (Participants + Historique) et effectue la fusion initiale.
    """

    def __init__(self) -> None:
        load_dotenv() # Charge les variables du .env
        self.logger = logging.getLogger("ML.Loader")
        
        db_url = os.getenv("DB_URL")
        if not db_url:
            raise ValueError("DB_URL manquant dans le fichier .env")
            
        self.engine = create_engine(db_url)

    def get_training_data(self) -> pd.DataFrame:
        """
        Extrait et fusionne les données participants et l'historique agrégé.
        """
        self.logger.info("Chargement des données SQL...")
        
        try:
            with self.engine.connect() as connection:
                # 1. Main Dataset (La nouvelle requête optimisée)
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
                self.logger.info("Calcul des statistiques historiques...")
                query_history = """
                SELECT horse_id, finish_place, reduction_km, prize_money 
                FROM horse_race_history
                """
                hist_df = pd.read_sql(query_history, connection)
                
                # Calcul optimisé des stats
                horse_stats = hist_df.groupby('horse_id').agg({
                    'finish_place': ['count', 'mean'],
                    'reduction_km': ['mean', 'min'],
                    'prize_money': 'sum'
                }).reset_index()
                
                horse_stats.columns = [
                    'horse_id', 'hist_races', 'hist_avg_rank', 
                    'hist_avg_speed', 'hist_best_speed', 'hist_earnings'
                ]
                
                # Valeur par défaut pour la vitesse (1.20 = lent/standard)
                horse_stats['hist_avg_speed'] = horse_stats['hist_avg_speed'].fillna(1.20)

                # 3. Fusion
                self.logger.info("Fusion des datasets...")
                final_df = pd.merge(main_df, horse_stats, on='horse_id', how='left')
                
                # Gestion basique des NULLs post-jointure (les "nouveaux" chevaux)
                final_df['hist_races'] = final_df['hist_races'].fillna(0)
                final_df['hist_earnings'] = final_df['hist_earnings'].fillna(0)
                
                return final_df.sort_values('program_date')

        except Exception as exc:
            self.logger.error(f"Erreur critique lors du chargement des données: {exc}")
            raise exc