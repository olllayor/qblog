import sqlite3
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = 'blog.db'  # Path to your SQLite database file

def connect_db():
    try:
        connection = sqlite3.connect(DATABASE_URL)
        logger.info("Connected to SQLite database")
        return connection
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def init_db():
    conn = connect_db()
    if conn is None:
        logger.error("Failed to connect to the database.")
        return False

    try:
        cur = conn.cursor() #Get the cursor object
        cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")
        return False
    finally:
       if conn: #Ensure that the connection is closed, whether or not an error occurred
         conn.close()

# Create the table if not exists
init_db()