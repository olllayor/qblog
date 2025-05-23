import os
import psycopg2
import logging
from urllib.parse import urlparse
from flask import g # Added import

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

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if 'db' not in g:
        g.db = connect_db()
    return g.db

def close_db(e=None):
    """Closes the database connection."""
    db = g.pop('db', None)

    if db is not None:
        db.close()
        logger.info("Database connection closed.")

def init_db():
    conn = get_db() # Use get_db instead of connect_db
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT,
                technologies TEXT, -- Comma-separated or JSON
                github_link TEXT,
                live_demo_link TEXT,
                date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("Database initialized or already exists.")
        return True
    except psycopg2.Error as e:
        logger.error(f"Error initializing database: {e}")
        return False
    finally:
        # Connection is now managed by app context, no close here
        pass