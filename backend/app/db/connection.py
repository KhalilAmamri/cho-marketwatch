from contextlib import contextmanager
import psycopg2

from app.core.config import settings


@contextmanager
def get_connection():
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    try:
        yield conn
    finally:
        conn.close()
