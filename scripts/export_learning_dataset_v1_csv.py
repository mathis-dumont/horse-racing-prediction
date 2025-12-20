import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.environ["DB_URL"])

os.makedirs("data", exist_ok=True)

print("Downloading view learning_dataset_v1...")
df = pd.read_sql("SELECT * FROM learning_dataset_v1;", engine)
print("shape:", df.shape)

df.to_csv("data/learning_dataset_v1.csv", index=False)
print("✅ Saved: data/learning_dataset_v1.csv")
