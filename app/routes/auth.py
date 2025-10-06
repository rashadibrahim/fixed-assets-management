from flask import Blueprint, request, jsonify
from flask_restx import Resource
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
import logging
from marshmallow import ValidationError
from .. import db
from ..models import User, JobDescription, Branch, Warehouse, FixedAsset
from ..schemas import UserSchema, UserCreateSchema, UserUpdateSchema
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import datetime
from ..utils import admin_required, check_permission, error_response, create_error_response, create_validation_error_response
from ..swagger import auth_ns, add_standard_responses
from ..swagger_models import (
    user_model, user_input_model, user_update_model, login_model, 
    auth_response_model, pagination_model, stats_model, error_model, success_model
)

bp = Blueprint("auth", __name__, url_prefix="/auth")
user_schema = UserSchema()
user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()


@auth_ns.route("/signup")
class Signup(Resource):
    @auth_ns.doc('signup')
    @auth_ns.expect(user_input_model)
    @auth_ns.response(201, 'Successfully created user', user_model)
    @auth_ns.response(400, 'Bad Request', error_model)
    @auth_ns.response(409, 'Conflict - Email already exists', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    @admin_required
    def post(self):
        """Register a new user"""
        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return create_error_response("Request body is required", 400)

        try:
            data = user_create_schema.load(json_data)
        except ValidationError as err:
            return create_validation_error_response(err.messages)

        full_name = data.get("full_name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")
        custom_permissions = data.get("permissions", {})

        if not all([full_name, email, password, role]):
            return create_error_response("Missing required fields: full_name, email, password, role", 400)

        try:
            # Check if email already exists
            if db.session.query(User).filter_by(email=email).first():
                return create_error_response("Email already registered", 409, "email")

            # Get role template as default permissions
            job = db.session.query(JobDescription).filter_by(name=role).first()
            if not job:
                return create_error_response("Invalid role", 400, "role")

            # Use custom permissions if provided, otherwise fall back to job role defaults
            user = User(
                full_name=full_name,
                email=email,
                role=role,
                can_read_branch=custom_permissions.get('can_read_branch', job.can_read_branch),
                can_edit_branch=custom_permissions.get('can_edit_branch', job.can_edit_branch),
                can_delete_branch=custom_permissions.get('can_delete_branch', job.can_delete_branch),
                can_read_warehouse=custom_permissions.get('can_read_warehouse', job.can_read_warehouse),
                can_edit_warehouse=custom_permissions.get('can_edit_warehouse', job.can_edit_warehouse),
                can_delete_warehouse=custom_permissions.get('can_delete_warehouse', job.can_delete_warehouse),
                can_read_asset=custom_permissions.get('can_read_asset', job.can_read_asset),
                can_edit_asset=custom_permissions.get('can_edit_asset', job.can_edit_asset),
                can_delete_asset=custom_permissions.get('can_delete_asset', job.can_delete_asset),
                can_print_barcode=custom_permissions.get('can_print_barcode', job.can_print_barcode),
                can_make_report=custom_permissions.get('can_make_report', job.can_make_report),
                can_make_transaction=custom_permissions.get('can_make_transaction', job.can_make_transaction),
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            return user_schema.dump(user), 201
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error creating user: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return create_error_response("Email already registered", 409, "email")
            return create_error_response("Data integrity constraint violation", 409)
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error creating user: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error creating user: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error creating user: {str(e)}")
            return create_error_response("Internal server error", 500)


@auth_ns.route("/register")
class Register(Resource):
    @auth_ns.doc('register')
    @auth_ns.expect(user_input_model)
    @auth_ns.response(201, 'Successfully created user', user_model)
    @auth_ns.response(400, 'Bad Request', error_model)
    @auth_ns.response(409, 'Conflict - Email already exists', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Register a new user (alternative endpoint)"""
        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return create_error_response("Request body is required", 400)

        try:
            data = user_create_schema.load(json_data)
        except ValidationError as err:
            return create_validation_error_response(err.messages)

        full_name = data.get("full_name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")
        custom_permissions = data.get("permissions", {})

        if not all([full_name, email, password, role]):
            return create_error_response("Missing required fields: full_name, email, password, role", 400)

        try:
            # Check if email already exists
            if db.session.query(User).filter_by(email=email).first():
                return create_error_response("Email already registered", 409, "email")

            # Get role template as default permissions
            job = db.session.query(JobDescription).filter_by(name=role).first()
            if not job:
                return create_error_response("Invalid role", 400, "role")

            # Use custom permissions if provided, otherwise fall back to job role defaults
            user = User(
                full_name=full_name,
                email=email,
                role=role,
                can_read_branch=custom_permissions.get('can_read_branch', job.can_read_branch),
                can_edit_branch=custom_permissions.get('can_edit_branch', job.can_edit_branch),
                can_delete_branch=custom_permissions.get('can_delete_branch', job.can_delete_branch),
                can_read_warehouse=custom_permissions.get('can_read_warehouse', job.can_read_warehouse),
                can_edit_warehouse=custom_permissions.get('can_edit_warehouse', job.can_edit_warehouse),
                can_delete_warehouse=custom_permissions.get('can_delete_warehouse', job.can_delete_warehouse),
                can_read_asset=custom_permissions.get('can_read_asset', job.can_read_asset),
                can_edit_asset=custom_permissions.get('can_edit_asset', job.can_edit_asset),
                can_delete_asset=custom_permissions.get('can_delete_asset', job.can_delete_asset),
                can_print_barcode=custom_permissions.get('can_print_barcode', job.can_print_barcode),
                can_make_report=custom_permissions.get('can_make_report', job.can_make_report),
                can_make_transaction=custom_permissions.get('can_make_transaction', job.can_make_transaction),
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            return user_schema.dump(user), 201
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error creating user: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return create_error_response("Email already registered", 409, "email")
            return create_error_response("Data integrity constraint violation", 409)
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error creating user: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error creating user: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error creating user: {str(e)}")
            return create_error_response("Internal server error", 500)


@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.doc('login')
    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Successfully logged in', auth_response_model)
    @auth_ns.response(400, 'Bad Request', error_model)
    @auth_ns.response(401, 'Invalid credentials', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Login user and get access token"""
        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return create_error_response("Request body is required", 400)

        email = json_data.get("email")
        password = json_data.get("password")
        
        if not email or not password:
            return create_error_response("Email and password are required", 400)

        try:
            user = db.session.query(User).filter_by(email=email).first()
            if not user or not user.check_password(password):
                return create_error_response("Invalid email or password", 401)

            access_token = create_access_token(
                identity=str(user.id), expires_delta=datetime.timedelta(hours=5)
            )
            return {"access_token": access_token, "user": user_schema.dump(user)}
        except OperationalError as e:
            logging.error(f"Database operational error during login: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            logging.error(f"Database error during login: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            logging.error(f"Unexpected error during login: {str(e)}")
            return create_error_response("Internal server error", 500)


@auth_ns.route("/me")
class Me(Resource):
    @auth_ns.doc('get_current_user', security='Bearer Auth')
    @auth_ns.response(200, 'Successfully retrieved current user', user_model)
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(404, 'User not found', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def get(self):
        """Get current user information"""
        try:
            user_id = get_jwt_identity()
            user = db.session.query(User).get(int(user_id))
            if not user:
                return create_error_response("User not found", 404)
            return user_schema.dump(user)
        except OperationalError as e:
            logging.error(f"Database operational error getting current user: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            logging.error(f"Database error getting current user: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            logging.error(f"Unexpected error getting current user: {str(e)}")
            return create_error_response("Internal server error", 500)


@auth_ns.route("/users")
class UserList(Resource):
    @auth_ns.doc('list_users', security='Bearer Auth')
    @auth_ns.response(200, 'Successfully retrieved users', pagination_model)
    @auth_ns.response(400, 'Bad Request', error_model)
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(403, 'Forbidden', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @auth_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @auth_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @auth_ns.param('id', 'Filter by user ID', type='integer')
    @auth_ns.param('name', 'Filter by user name (partial match)', type='string')
    @jwt_required()
    @admin_required
    def get(self):
        """Get all users with pagination + optional search by id or name (Admin only)"""
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        user_id = request.args.get("id", type=int)
        name = request.args.get("name", type=str)
        
        # Validate pagination parameters
        if page < 1:
            return create_error_response("Page number must be positive", 400, "page")
        if per_page < 1 or per_page > 100:
            return create_error_response("Items per page must be between 1 and 100", 400, "per_page")

        try:
            query = db.session.query(User)

            if user_id:
                query = query.filter(User.id == user_id)
            if name:
                query = query.filter(User.full_name.ilike(f"%{name}%"))

            # Order by ID descending for consistent ordering
            query = query.order_by(User.id.desc())

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            return {
                "items": user_schema.dump(pagination.items, many=True),
                "total": pagination.total,
                "page": pagination.page,
                "pages": pagination.pages
            }
        except OperationalError as e:
            logging.error(f"Database operational error in user list: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            logging.error(f"Database error in user list: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            logging.error(f"Unexpected error in user list: {str(e)}")
            return create_error_response("Internal server error", 500)


@auth_ns.route("/<int:user_id>")
class UserResource(Resource):
    @auth_ns.doc('update_user', security='Bearer Auth')
    @auth_ns.expect(user_update_model, validate=False)
    @auth_ns.response(200, 'Successfully updated user', user_model)
    @auth_ns.response(400, 'Bad Request', error_model)
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(403, 'Forbidden', error_model)
    @auth_ns.response(404, 'User not found', error_model)
    @auth_ns.response(409, 'Conflict - Email already exists', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    @admin_required
    def put(self, user_id):
        """Update a specific user by ID (Admin only)"""
        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return create_error_response("Request body is required", 400)

        try:
            user = db.session.query(User).get(int(user_id))
            if not user:
                return create_error_response("User not found", 404)

            # Check for email uniqueness if email is being updated
            if "email" in json_data and json_data["email"] != user.email:
                existing_user = db.session.query(User).filter_by(email=json_data["email"]).first()
                if existing_user:
                    return create_error_response("Email already registered", 409, "email")

            if "email" in json_data:
                user.email = json_data["email"]
            if "role" in json_data:
                user.role = json_data["role"]
            if "full_name" in json_data:
                user.full_name = json_data["full_name"]

            # Update permissions if provided
            if "permissions" in json_data:
                perms = json_data["permissions"]
                user.can_read_branch = perms.get("can_read_branch", user.can_read_branch)
                user.can_edit_branch = perms.get("can_edit_branch", user.can_edit_branch)
                user.can_delete_branch = perms.get("can_delete_branch", user.can_delete_branch)

                user.can_read_warehouse = perms.get("can_read_warehouse", user.can_read_warehouse)
                user.can_edit_warehouse = perms.get("can_edit_warehouse", user.can_edit_warehouse)
                user.can_delete_warehouse = perms.get("can_delete_warehouse", user.can_delete_warehouse)

                user.can_read_asset = perms.get("can_read_asset", user.can_read_asset)
                user.can_edit_asset = perms.get("can_edit_asset", user.can_edit_asset)
                user.can_delete_asset = perms.get("can_delete_asset", user.can_delete_asset)

                user.can_print_barcode = perms.get("can_print_barcode", user.can_print_barcode)
                user.can_make_report = perms.get("can_make_report", user.can_make_report)
                user.can_make_transaction = perms.get("can_make_transaction", user.can_make_transaction)

            db.session.commit()
            return user_schema.dump(user), 200
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error updating user {user_id}: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return create_error_response("Email already registered", 409, "email")
            return create_error_response("Data integrity constraint violation", 409)
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error updating user {user_id}: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error updating user {user_id}: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error updating user {user_id}: {str(e)}")
            return create_error_response("Internal server error", 500)

    @auth_ns.doc('delete_user', security='Bearer Auth')
    @auth_ns.response(200, 'Successfully deleted user', success_model)
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(403, 'Forbidden', error_model)
    @auth_ns.response(404, 'User not found', error_model)
    @auth_ns.response(409, 'Conflict - Cannot delete referenced user', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    @admin_required
    def delete(self, user_id):
        """Delete a specific user by ID (Admin only)"""
        try:
            user = db.session.query(User).get(int(user_id))
            if not user:
                return create_error_response("User not found", 404)

            db.session.delete(user)
            db.session.commit()
            return {"message": "User deleted successfully"}, 200
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error deleting user {user_id}: {str(e)}")
            return create_error_response("Cannot delete user: user may be referenced by other records", 409)
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error deleting user {user_id}: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error deleting user {user_id}: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error deleting user {user_id}: {str(e)}")
            return create_error_response("Internal server error", 500)


@auth_ns.route("/stats")
class Statistics(Resource):
    @auth_ns.doc('get_statistics')
    @auth_ns.response(200, 'Successfully retrieved statistics', stats_model)
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(403, 'Forbidden', error_model)
    @auth_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def get(self):
        """Get system statistics (requires read permissions)"""
        try:
            # Get current user to check permissions
            identity = get_jwt_identity()
            user = db.session.query(User).get(int(identity))
            
            if not user:
                return {"error": "User not found"}, 404
            
            stats = {}
            
            # Only include stats for entities the user can read
            if user.can_read_branch:
                stats["total_branches"] = db.session.query(Branch).count()
            
            if user.can_read_warehouse:
                stats["total_warehouses"] = db.session.query(Warehouse).count()
            
            if user.can_read_asset:
                stats["total_assets"] = db.session.query(FixedAsset).count()
                stats["active_assets"] = db.session.query(FixedAsset).filter_by(is_active=True).count()
                stats["inactive_assets"] = db.session.query(FixedAsset).filter_by(is_active=False).count()
            
            # User and job role counts only for admins
            if user.role.lower() == "admin":
                stats["total_users"] = db.session.query(User).count()
                stats["job_roles_count"] = db.session.query(JobDescription).count()
            
            # If user has no read permissions, deny access
            if not stats:
                return {"error": "Insufficient permissions to view statistics"}, 403

            return stats, 200
        except OperationalError as e:
            logging.error(f"Database operational error getting statistics: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            logging.error(f"Database error getting statistics: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            logging.error(f"Unexpected error getting statistics: {str(e)}")
            return create_error_response("Internal server error", 500)