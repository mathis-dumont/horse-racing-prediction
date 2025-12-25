import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.environ["DB_URL"])

os.makedirs("data", exist_ok=True)

# bornes
bounds = pd.read_sql(
    """
    SELECT MIN(program_date) AS min_date, MAX(program_date) AS max_date
    FROM learning_dataset_v2
    """,
    engine,
)

min_date = pd.to_datetime(bounds.loc[0, "min_date"]).date()
max_date = pd.to_datetime(bounds.loc[0, "max_date"]).date()
print("Date range:", min_date, "→", max_date)

out_path = "data/learning_dataset_v2.csv"

# si le fichier existe, on reprend après la dernière date exportée
start_date = min_date
if os.path.exists(out_path):
    prev = pd.read_csv(out_path, usecols=["program_date"])
    prev["program_date"] = pd.to_datetime(prev["program_date"]).dt.date
    start_date = max(prev["program_date"])  # dernière date déjà exportée
    print("Resume from:", start_date)

dates = pd.date_range(start_date, max_date, freq="D")

first_write = not os.path.exists(out_path)

for d in dates:
    day = d.date()
    print("Export day:", day)

    query = f"""
        SELECT *
        FROM learning_dataset_v2
        WHERE program_date = '{day}'
    """

    df = pd.read_sql(query, engine)
    print("  rows:", len(df))

    if len(df) == 0:
        continue

    df.to_csv(out_path, index=False, mode="a", header=first_write)
    first_write = False

print("✅ Done:", out_path)
