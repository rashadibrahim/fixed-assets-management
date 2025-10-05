import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration - directly set the credentials
    
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = 'fixed_assets_management_db'
    DB_USER = 'belal'
    DB_PASSWORD = 'belal'  # Your actual password here
    LOCAL_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" #"sqlite:///fixed_assets.db"
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")
    # Build the database URI directly
    # SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://postgres:yrbAGRBiCpuXYNQmPuUxmbiwQzruQrpt@postgres.railway.internal:5432/railway"
    SQLALCHEMY_DATABASE_URI = LOCAL_URL
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    print(f"🔧 Config loaded - User: {DB_USER}, Host: {DB_HOST}, Port: {DB_PORT}, DB: {DB_NAME}")
    print(f"🔧 Database URI: postgresql://***:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")
