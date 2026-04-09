import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "cho_marketwatch_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def get_connection():
    return psycopg2.connect(
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"],
        database=DATABASE_CONFIG["database"],
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
    )
