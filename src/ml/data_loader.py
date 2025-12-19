import pandas as pd
import os
from src.core.database import DatabaseManager

class DataLoader:
    def __init__(self):
        self.db_manager = DatabaseManager()

    def fetch_data_from_db(self, limit=None):
        conn = self.db_manager.get_connection()
        try:
            query = "SELECT * FROM v_raw_training_data"
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql(query, conn)
            return df
        finally:
            self.db_manager.release_connection(conn)

    def save_to_parquet(self, df, filename="data/raw_dataset.parquet"):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        df.to_parquet(filename, engine="pyarrow", compression="snappy", index=False)

    def load_local_dataset(self, filename="data/raw_dataset.parquet"):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Dataset not found at {filename}")
        return pd.read_parquet(filename, engine="pyarrow")