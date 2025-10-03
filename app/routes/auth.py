from flask import Blueprint, request, jsonify
from flask_restx import Resource
from .. import db
from ..models import User, JobDescription, Branch, Warehouse, FixedAsset
from ..schemas import UserSchema
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import datetime
from ..utils import admin_required, check_permission
from ..swagger import auth_ns, add_standard_responses
from ..swagger_models import (
    user_model, user_input_model, user_update_model, login_model, 
    auth_response_model, pagination_model, stats_model, error_model, success_model
)

bp = Blueprint("auth", __name__, url_prefix="/auth")
user_schema = UserSchema()


@auth_ns.route("/signup")
class Signup(Resource):
    @auth_ns.doc('signup')
    @auth_ns.expect(user_input_model)
    @auth_ns.marshal_with(user_model, code=201, description='Successfully created user')
    @auth_ns.response(400, 'Bad Request', error_model)
    # @jwt_required()
    # @admin_required
    def post(self):
        """Register a new user"""
        data = request.get_json()

        full_name = data.get("full_name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")

        if not all([full_name, email, password, role]):
            return {"error": "Missing required fields"}, 400

        if db.session.query(User).filter_by(email=email).first():
            return {"error": "Email already registered"}, 400

        # get role template
        job = db.session.query(JobDescription).filter_by(name=role).first()
        if not job:
            return {"error": "Invalid role"}, 400

        user = User(
            full_name=full_name,
            email=email,
            role=role,
            can_read_branch=job.can_read_branch,
            can_edit_branch=job.can_edit_branch,
            can_delete_branch=job.can_delete_branch,
            can_read_warehouse=job.can_read_warehouse,
            can_edit_warehouse=job.can_edit_warehouse,
            can_delete_warehouse=job.can_delete_warehouse,
            can_read_asset=job.can_read_asset,
            can_edit_asset=job.can_edit_asset,
            can_delete_asset=job.can_delete_asset,
            can_print_barcode=job.can_print_barcode,
            can_make_report=job.can_make_report,
            can_make_transaction=job.can_make_transaction,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return user_schema.dump(user), 201


@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.doc('login')
    @auth_ns.expect(login_model)
    @auth_ns.marshal_with(auth_response_model, code=200, description='Successfully logged in')
    @auth_ns.response(401, 'Invalid credentials', error_model)
    def post(self):
        """Login user and get access token"""
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        user = db.session.query(User).filter_by(email=email).first()
        if not user or not user.check_password(password):
            return {"error": "Invalid email or password"}, 401

        access_token = create_access_token(
            identity=str(user.id), expires_delta=datetime.timedelta(hours=5)
        )
        return {"access_token": access_token, "user": user_schema.dump(user)}


@auth_ns.route("/me")
class Me(Resource):
    @auth_ns.doc('get_current_user', security='Bearer Auth')
    @auth_ns.marshal_with(user_model, code=200, description='Successfully retrieved current user')
    @auth_ns.response(401, 'Unauthorized', error_model)
    @jwt_required()
    def get(self):
        """Get current user information"""
        user_id = get_jwt_identity()
        user = db.session.query(User).get(user_id)
        return user_schema.dump(user)


@auth_ns.route("/users")
class UserList(Resource):
    @auth_ns.doc('list_users', security='Bearer Auth')
    @auth_ns.marshal_with(pagination_model, code=200, description='Successfully retrieved users')
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(403, 'Forbidden', error_model)
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

        query = db.session.query(User)

        if user_id:
            query = query.filter(User.id == user_id)
        if name:
            query = query.filter(User.full_name.ilike(f"%{name}%"))

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "items": user_schema.dump(pagination.items, many=True),
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages
        }


@auth_ns.route("/<int:user_id>")
class UserResource(Resource):
    @auth_ns.doc('update_user', security='Bearer Auth')
    @auth_ns.expect(user_update_model, validate=False)
    @auth_ns.marshal_with(user_model, code=200, description='Successfully updated user')
    @auth_ns.response(400, 'Bad Request', error_model)
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(403, 'Forbidden', error_model)
    @auth_ns.response(404, 'User not found', error_model)
    @admin_required
    def put(self, user_id):
        """Update a specific user by ID (Admin only)"""
        user = db.session.query(User).get(user_id)
        if not user:
            return {"error": "User not found"}, 404

        data = request.get_json()

        if "email" in data:
            user.email = data["email"]
        if "role" in data:
            user.role = data["role"]
        if "full_name" in data:
            user.full_name = data["full_name"]

        # ✅ Update permissions if provided
        if "permissions" in data:
            perms = data["permissions"]
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

    @auth_ns.doc('delete_user', security='Bearer Auth')
    @auth_ns.marshal_with(success_model, code=200, description='Successfully deleted user')
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(403, 'Forbidden', error_model)
    @auth_ns.response(404, 'User not found', error_model)
    @admin_required
    def delete(self, user_id):
        """Delete a specific user by ID (Admin only)"""
        user = db.session.query(User).get(user_id)
        if not user:
            return {"error": "User not found"}, 404

        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted successfully"}, 200


@auth_ns.route("/stats")
class Statistics(Resource):
    @auth_ns.doc('get_statistics')
    @auth_ns.marshal_with(stats_model, code=200, description='Successfully retrieved statistics')
    @auth_ns.response(401, 'Unauthorized', error_model)
    @auth_ns.response(403, 'Forbidden', error_model)
    @jwt_required()
    @admin_required
    def get(self):
        """Get system statistics (Admin only)"""
        stats = {
            "total_branches": db.session.query(Branch).count(),
            "total_warehouses": db.session.query(Warehouse).count(),
            "total_assets": db.session.query(FixedAsset).count(),
            "active_assets": db.session.query(FixedAsset).filter_by(is_active=True).count(),
            "inactive_assets": db.session.query(FixedAsset).filter_by(is_active=False).count(),
            "total_users": db.session.query(User).count(),
            "job_roles_count": db.session.query(JobDescription).count()
        }

        return stats, 200