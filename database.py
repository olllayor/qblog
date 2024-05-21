import os
import psycopg2
import logging
from dotenv import load_dotenv
logger = logging.getLogger(__name__)

# Replace with your actual database credentials

# Load environment variables from .env file
load_dotenv()

# Get the database URL from the environment variable
DATABASE_URL = os.getenv('POSTGRES_DB_URL')
def connect_db():
    try:
        connection = psycopg2.connect(DATABASE_URL, sslmode='require')
        print()
        # print("Connected to database")
        logger.info("Connected to database")
        return connection
    except psycopg2.Error as e:
        # print(f"Error connecting to database: {e}")
        logger.error(f"Error connecting to database: {e}")
        return None
    
connect_db()