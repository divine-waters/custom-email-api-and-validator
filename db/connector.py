# db/connector.py

import pyodbc
import os
from dotenv import load_dotenv
from contextlib import contextmanager
from utils.logger import get_logger

logger = get_logger("db_connector")
load_dotenv()

# Load database connection details from environment variables
# Use 'localhost' or 'localhost\INSTANCE_NAME' as appropriate
DB_SERVER = os.getenv("DB_SERVER")
# Find this name using SSMS or sqlcmd as described above
DB_DATABASE = os.getenv("DB_DATABASE")
# DB_USERNAME = os.getenv("DB_USERNAME") # REMOVED - Not needed for Windows Auth
# DB_PASSWORD = os.getenv("DB_PASSWORD") # REMOVED - Not needed for Windows Auth
DB_DRIVER = os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}") # Default driver

# --- Input Validation ---
if not DB_SERVER:
    logger.critical("❌ DB_SERVER environment variable not set.")
    raise ValueError("Missing DB_SERVER environment variable")
if not DB_DATABASE:
    logger.critical("❌ DB_DATABASE environment variable not set.")
    raise ValueError("Missing DB_DATABASE environment variable")
# --- End Input Validation ---


# Construct the connection string for Windows Authentication
connection_string = (
    f"DRIVER={DB_DRIVER};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_DATABASE};"
    f"Trusted_Connection=yes;" # Use Windows Authentication
    # Remove UID and PWD lines
)
# Log the connection string details being used (safe as it contains no secrets now)
logger.info(f"Using DB Connection String (Trusted): DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_DATABASE};Trusted_Connection=yes;")


@contextmanager
def get_db_connection():
    """Provides a database connection using a context manager (Windows Auth)."""
    conn = None
    try:
        logger.debug("Attempting to connect to the database using Windows Authentication...")
        # Set autocommit=False for better transaction control within DAO functions
        conn = pyodbc.connect(connection_string, autocommit=False)
        logger.debug("Database connection successful.")
        yield conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logger.error(f"Database connection error (SQLSTATE: {sqlstate}): {ex}")
        # Re-raise as a standard ConnectionError for consistent handling
        raise ConnectionError(f"Failed to connect to database: {ex}") from ex
    except Exception as e:
        logger.error(f"An unexpected error occurred during database connection: {e}")
        raise ConnectionError(f"Unexpected error connecting to database: {e}") from e
    finally:
        if conn:
            logger.debug("Closing database connection.")
            conn.close()

# --- REMOVED DAO FUNCTIONS ---
# All fetch/save functions previously here have been moved to email_dao.py
# or removed if duplicated.
