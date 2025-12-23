import os
import psycopg2
from dotenv import load_dotenv

# Charge le fichier .env
load_dotenv()

def get_connection():
    """
    Connect to the PostgreSQL database using the DB_URL from environment variables.
    """
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL not set in environment variables.")

    return psycopg2.connect(db_url)

