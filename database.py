import os
import psycopg2
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

def connect_db():
    if not DATABASE_URL:
       logger.error("DATABASE_URL is not set.")
       return None
    try:
        connection = psycopg2.connect(DATABASE_URL)
        logger.info("Connected to PostgreSQL database")
        return connection
    except psycopg2.Error as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def init_db():
    conn = connect_db()
    if conn is None:
        logger.error("Failed to connect to the database.")
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                date_published TIMESTAMP NOT NULL,
                is_published BOOLEAN NOT NULL DEFAULT FALSE,
                slug TEXT UNIQUE NOT NULL
            )
        """)
        conn.commit()
        logger.info("Database initialized or already exists.")
        return True
    except psycopg2.Error as e:
        logger.error(f"Error initializing database: {e}")
        return False
    finally:
        if conn:
            conn.close()