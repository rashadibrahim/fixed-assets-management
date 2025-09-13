import os
import uuid
from flask import current_app, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from functools import wraps
from .models import User

def save_upload(file_storage):
    """
    Save uploaded FileStorage to UPLOAD_FOLDER with a unique name.
    Returns the stored filename (not full path).
    """
    if not file_storage:
        return None
    # original filename for extension
    filename = file_storage.filename
    _, ext = os.path.splitext(filename)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
    file_storage.save(path)
    return unique_name

def error_response(message, code=400, details=None):
    """Convenience to return JSON error responses.
    
    Args:
        message: Main error message
        code: HTTP status code
        details: Optional dictionary with additional error details
    """
    response = {"error": message}
    if details:
        response["details"] = details
    return jsonify(response), code


def handle_validation_exception(e):
    """Centralized handler for validation exceptions.
    
    This function can be used in try/except blocks to handle validation errors
    consistently across the application.
    """
    if hasattr(e, 'messages'):
        return error_response("Validation Error", 400, e.messages)
    return error_response(str(e), 400)




def check_permission(permission_field):
    """Check if the logged-in user has a given permission field."""
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not getattr(user, permission_field, False):
        return jsonify({"error": f"Permission '{permission_field}' denied"}), 403

    return None  # Means permission granted


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        user = User.query.get(identity)

        if not user or user.role.lower() != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return fn(*args, **kwargs)
    return wrapper