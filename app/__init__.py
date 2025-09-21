from flask import Flask, jsonify, request
from flask_restx import ValidationError
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager
from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy.exc import IntegrityError, DataError
from flask_cors import CORS

db = SQLAlchemy()
ma = Marshmallow()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)
    CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        
    }})
    app.config.from_object("config.Config")

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    
    # Register a middleware to handle exceptions globally
    @app.before_request
    def before_request():
        pass
        
    @app.after_request
    def after_request(response):
        return response

    # Initialize Flask-RESTx API
    from .swagger import api
    api.init_app(app)

    # import blueprints
    from .routes import assets, branches, warehouses, job_roles, transactions
    from .routes import auth

    # Register blueprints with /api prefix
    app.register_blueprint(assets.bp, url_prefix="/api/assets")
    app.register_blueprint(branches.bp, url_prefix="/api/branches")
    app.register_blueprint(warehouses.bp, url_prefix="/api/warehouses")
    app.register_blueprint(job_roles.bp, url_prefix="/api/jobroles")
    app.register_blueprint(auth.bp, url_prefix="/api/auth")
    app.register_blueprint(transactions.bp, url_prefix="/api/transactions")

    @app.errorhandler(ValidationError)
    def handle_restx_validation_error(err):
        return jsonify({
            "error": "Validation Error",
            "messages": err.messages
        }), 400
        
    @app.errorhandler(MarshmallowValidationError)
    def handle_marshmallow_validation_error(err):
        return jsonify({
            "error": "Validation Error",
            "messages": err.messages if hasattr(err, 'messages') else {"_schema": [str(err)]}
        }), 400
        
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(err):
        return jsonify({
            "error": "Database Integrity Error",
            "message": str(err.orig) if hasattr(err, 'orig') else str(err)
        }), 400
        
    @app.errorhandler(DataError)
    def handle_data_error(err):
        return jsonify({
            "error": "Database Data Error",
            "message": str(err.orig) if hasattr(err, 'orig') else str(err)
        }), 400
    @app.errorhandler(404)
    def handle_404_error(err):
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found"
        }), 404
    @app.errorhandler(500)
    def handle_500_error(err):
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server"
        }), 500
        
    @app.errorhandler(Exception)
    def handle_exception(err):
        """Handle all unhandled exceptions"""
        # Log the error for debugging
        app.logger.error(f"Unhandled exception: {str(err)}")
        
        # Return a consistent error response
        return jsonify({
            "error": "Server Error",
            "message": "An unexpected error occurred"
        }), 500
    return app
