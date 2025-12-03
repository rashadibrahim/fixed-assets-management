import os
import time
import logging
from sqlalchemy import exc, create_engine, text
from sqlalchemy.engine import URL
from flask import current_app
from flask_migrate import upgrade, stamp, migrate
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_db(db, max_retries=5, retry_interval=2):
    """
    Wait for database to be available with retry mechanism.
    
    Args:
        db: SQLAlchemy database instance
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds to wait between retries
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    retries = 0
    while retries < max_retries:
        try:
            # Use the app's configured database URI instead of db.engine
            from config import Config
            
            # Create a new engine using the same configuration as config.py
            db_url = URL.create(
                drivername="postgresql+psycopg2",
                username=Config.DB_USER,
                password=Config.DB_PASSWORD,
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME
            )
            
            engine = create_engine(db_url)
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Database connection successful")
            return True
            
        except exc.OperationalError as e:
            retries += 1
            if retries < max_retries:
                logger.warning(f"Database connection attempt {retries} failed. Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            return False

def init_db(db, app):
    """
    Initialize database schema automatically.
    
    This function will:
    1. Wait for database to be available
    2. Check if migrations directory exists
    3. If migrations exist, run migrations
    4. If no migrations, create tables directly
    
    Args:
        db: SQLAlchemy database instance
        app: Flask application instance
    """
    with app.app_context():
        # Wait for database to be available
        if not wait_for_db(db):
            logger.error("Could not connect to database. Exiting.")
            return False
        
        try:
            # Check if migrations directory exists
            migrations_dir = os.path.join(app.root_path, '..', 'migrations')
            
            if os.path.exists(migrations_dir):
                logger.info("Migrations directory found. Running migrations...")
                try:
                    # Try to run migrations
                    upgrade()
                    logger.info("Database migrations applied successfully")
                except Exception as e:
                    logger.warning(f"Error applying migrations: {e}")
                    logger.info("Attempting to create database schema directly...")
                    db.create_all()
                    # Stamp the database with the current migration version
                    stamp()
                    logger.info("Database schema created and stamped with current migration")
            else:
                logger.info("No migrations directory found. Creating tables directly...")
                db.create_all()
                logger.info("Database tables created successfully")
                
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

def ensure_schema_updated(db, app):
    """
    Ensure database schema is up-to-date with models.
    
    This function will:
    1. Check if any model changes need migration
    2. If changes detected, auto-generate and apply migrations
    
    Args:
        db: SQLAlchemy database instance
        app: Flask application instance
    """
    with app.app_context():
        try:
            # Auto-generate migrations for any model changes
            migrate(message="Auto-generated migration")
            
            # Apply the migrations
            upgrade()
            
            logger.info("Database schema updated successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to update database schema: {e}")
            return False

def create_database_if_not_exists():
    """
    Check if the configured database exists, and create it if it doesn't.
    Connects to the default 'postgres' database to perform this check.
    """
    from config import Config
    
    db_name = Config.DB_NAME
    
    # Connect to default 'postgres' database to check/create target db
    default_url = URL.create(
        drivername="postgresql+psycopg2",
        username=Config.DB_USER,
        password=Config.DB_PASSWORD,
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database="postgres"
    )
    
    try:
        engine = create_engine(default_url)
        # Use isolation_level="AUTOCOMMIT" to allow CREATE DATABASE
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            # Check if database exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            if not result.scalar():
                logger.info(f"Database {db_name} does not exist. Creating...")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database {db_name} created successfully.")
            else:
                logger.info(f"Database {db_name} already exists.")
    except Exception as e:
        logger.error(f"Error checking/creating database: {e}")
        # We proceed, as the error might be because we can't connect to 'postgres' db,
        # but maybe the target db already exists and is accessible.

def setup_database(config, db):
    """One function to handle everything database-related"""
    # This function seems to be legacy or using a different config structure.
    # Keeping it for now but create_database_if_not_exists is preferred for the new flow.
    pass