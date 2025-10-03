from app import create_app, db
from flask_migrate import Migrate
from app.models import Branch, Warehouse, FixedAsset
import logging

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Changed to WARNING to reduce noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to WARNING level to reduce noise
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# Create app using the factory in app/__init__.py
app = create_app()

# Setup Flask-Migrate (Alembic wrapper) with the app and db
migrate = Migrate(app, db)

# Simple database initialization
with app.app_context():
    try:
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Verify connection by running a simple query
        result = db.session.execute(db.text("SELECT 1"))
        print("✅ Database connection verified")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        logging.error(f"❌ Database initialization failed: {e}")
        exit(1)

# Helpful shell context for `flask shell` or when using python manage.py shell
@app.shell_context_processor
def make_shell_context():
    return {"db": db, "Branch": Branch, "Warehouse": Warehouse, "FixedAsset": FixedAsset}

if __name__ == "__main__":
    try:
        # Start the Flask application
        print("🚀 Starting Flask application...")
        # app.run(host="0.0.0.0", port=8000, debug=True, threaded=True) # For development
        app.run(host="0.0.0.0",threaded=True) # For production
    except Exception as e:
        logging.error(f"Failed to start application: {e}")
        exit(1)

