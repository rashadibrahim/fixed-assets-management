import os
from random import random
import uuid
import io
import base64
from flask import current_app, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from functools import wraps
from .models import User, FixedAsset
try:
    from barcode.codex import Code128
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

# def save_upload(file_storage):
#     """
#     Save uploaded FileStorage to UPLOAD_FOLDER with a unique name.
#     Returns the stored filename (not full path).
#     """
#     if not file_storage:
#         return None
#     # original filename for extension
#     filename = file_storage.filename
#     _, ext = os.path.splitext(filename)
#     unique_name = f"{uuid.uuid4().hex}{ext}"
#     path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
#     file_storage.save(path)
#     return unique_name

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


# NEW STANDARDIZED ERROR RESPONSE FUNCTIONS
def create_error_response(message, status_code=400, field=None):
    """
    Create a standardized error response
    
    Args:
        message (str): Error message to display
        status_code (int): HTTP status code
        field (str, optional): Specific field that caused the error
    
    Returns:
        tuple: (error_dict, status_code)
    """
    error_response = {
        "error": message,
        "status_code": status_code
    }
    
    if field:
        error_response["field"] = field
        
    return error_response, status_code

def create_validation_error_response(validation_errors, status_code=400):
    """
    Create a standardized validation error response
    
    Args:
        validation_errors (dict): Validation errors from marshmallow
        status_code (int): HTTP status code
    
    Returns:
        tuple: (error_dict, status_code)
    """
    # Extract first error message for main error field
    first_field = next(iter(validation_errors))
    first_error = validation_errors[first_field][0] if isinstance(validation_errors[first_field], list) else validation_errors[first_field]
    
    error_response = {
        "error": f"Validation failed: {first_error}",
        "status_code": status_code,
        "field": first_field,
        "validation_errors": validation_errors
    }
    
    return error_response, status_code


def check_permission(permission_field):
    """Check if the logged-in user has a given permission field."""
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return create_error_response("User not found", 404)

    if not getattr(user, permission_field, False):
        return create_error_response(f"Permission '{permission_field}' denied", 403)

    return None  # Means permission granted

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        user = User.query.get(identity)

        if not user or user.role.lower() != "admin":
            return create_error_response("Admin access required", 403)

        return fn(*args, **kwargs)
    return wrapper


def generate_unique_product_code():
    """
    Generate a unique 6-digit product code for an asset.
    Format: 6 random digits (e.g., 482913).
    """
    from . import db
    
    while True:
        # Generate a random 6-digit number
        random_number = str(uuid.uuid4().int)[:6]

        # Check if this code already exists in the database
        existing = db.session.query(FixedAsset).filter_by(product_code=random_number).first()
        if not existing:
            return random_number

def generate_barcode(product_code):
    """
    Generate a barcode image as base64 encoded string from a product code.
    
    Args:
        product_code: The product code to encode in the barcode
        
    Returns:
        dict: Dictionary containing the barcode image as base64 string and the product code
    """
    if not product_code:
        return None
    
    if not BARCODE_AVAILABLE:
        return {
            'product_code': product_code,
            'barcode_image': None,
            'error': 'Barcode library not available'
        }
        
    try:
        # Create a Code128 barcode (good for alphanumeric data)
        code128 = Code128(product_code, writer=ImageWriter())
        
        # Save the barcode to a bytes buffer instead of a file
        buffer = io.BytesIO()
        code128.write(buffer)
        
        # Get the bytes value and encode as base64
        buffer.seek(0)
        barcode_bytes = buffer.getvalue()
        barcode_base64 = base64.b64encode(barcode_bytes).decode('utf-8')
        
        return {
            'product_code': product_code,
            'barcode_image': barcode_base64
        }
    except Exception as e:
        return {
            'product_code': product_code,
            'barcode_image': None,
            'error': str(e)
        }