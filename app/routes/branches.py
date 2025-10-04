from flask import Blueprint, request, jsonify
from flask_restx import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
import logging
from .. import db
from ..models import Branch
from ..schemas import BranchSchema, WarehouseSchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission, error_response
from ..swagger import branches_ns, add_standard_responses
from ..swagger_models import (
    branch_model, branch_input_model, branch_with_warehouses_model,
    pagination_model, error_model, success_model
)

bp = Blueprint("branches", __name__, url_prefix="/branches")

branch_schema = BranchSchema()
branches_schema = BranchSchema(many=True)

warehouses_schema = WarehouseSchema(many=True)

@branches_ns.route("/")
class BranchList(Resource):
    @branches_ns.doc('list_branches')
    @branches_ns.response(200, 'Successfully retrieved branches', pagination_model)
    @branches_ns.response(400, 'Bad Request', error_model)
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.response(500, 'Internal Server Error', error_model)
    @branches_ns.response(503, 'Service Unavailable', error_model)
    @branches_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @branches_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @branches_ns.param('search', 'Search in branch name', type=str)
    @jwt_required()
    def get(self):
        """Get all branches with pagination, including warehouses count and optional search"""
        error = check_permission("can_read_branch")
        if error:
            return error

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "").strip()
        
        # Validate pagination parameters
        if page < 1:
            return {"error": "Page number must be positive"}, 400
        if per_page < 1 or per_page > 100:
            return {"error": "Items per page must be between 1 and 100"}, 400

        try:
            query = db.session.query(Branch)
            
            # Apply search filter if provided
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(Branch.name_en.ilike(search_pattern))
            
            # Order results by name
            query = query.order_by(Branch.name_en)

            # Apply pagination
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)

            branches_data = []
            for branch in paginated.items:
                branch_dict = branch_schema.dump(branch)

                # Count warehouses in this branch
                warehouse_count = len(branch.warehouses)
                branch_dict["warehouse_count"] = warehouse_count
                branches_data.append(branch_dict)

            return {
                "items": branches_data,
                "total": paginated.total,
                "page": paginated.page,
                "pages": paginated.pages
            }
        except OperationalError as e:
            logging.error(f"Database operational error in branch list: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error in branch list: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error in branch list: {str(e)}")
            return {"error": "Internal server error"}, 500


    @branches_ns.doc('create_branch')
    @branches_ns.expect(branch_input_model)
    @branches_ns.response(201, 'Successfully created branch', branch_model)
    @branches_ns.response(400, 'Bad Request', error_model)
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @branches_ns.response(500, 'Internal Server Error', error_model)
    @branches_ns.response(503, 'Service Unavailable', error_model)
    @jwt_required()
    def post(self):
        """Create a new branch"""
        error = check_permission("can_edit_branch")
        if error:
            return error

        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return {"error": "Request body is required"}, 400

        try:
            try:
                data = branch_schema.load(json_data)
            except ValidationError as err:
                return {"error": "Validation error", "details": err.messages}, 400

            branch = Branch(**data)
            db.session.add(branch)
            db.session.commit()

            return branch_schema.dump(branch), 201
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error creating branch: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return {"error": "Branch with this name already exists"}, 409
            return {"error": "Data integrity constraint violation"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error creating branch: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error creating branch: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error creating branch: {str(e)}")
            return {"error": "Internal server error"}, 500


@branches_ns.route("/<int:branch_id>")
class BranchResource(Resource):
    @branches_ns.doc('get_branch')
    @branches_ns.response(200, 'Successfully retrieved branch', branch_with_warehouses_model)
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.response(404, 'Branch not found', error_model)
    @branches_ns.response(500, 'Internal Server Error', error_model)
    @branches_ns.response(503, 'Service Unavailable', error_model)
    @jwt_required()
    def get(self, branch_id):
        """Get a specific branch by ID"""
        error = check_permission("can_read_branch")
        if error:
            return error

        try:
            branch = db.session.query(Branch).filter_by(id=branch_id).first()
            if not branch:
                return {"error": "Branch not found"}, 404
                
            branch_data = branch_schema.dump(branch)
            # Add warehouse count to the response
            branch_data["warehouse_count"] = len(branch.warehouses)
            # Add warehouses to the response
            branch_data["warehouses"] = warehouses_schema.dump(branch.warehouses)
            print(branch_data)
            
            return branch_data
        except OperationalError as e:
            logging.error(f"Database operational error getting branch {branch_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error getting branch {branch_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error getting branch {branch_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

    @branches_ns.doc('update_branch')
    @branches_ns.expect(branch_input_model, validate=False)
    @branches_ns.response(200, 'Successfully updated branch', branch_model)
    @branches_ns.response(400, 'Bad Request', error_model)
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.response(404, 'Branch not found', error_model)
    @branches_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @branches_ns.response(500, 'Internal Server Error', error_model)
    @branches_ns.response(503, 'Service Unavailable', error_model)
    @jwt_required()
    def put(self, branch_id):
        """Update a specific branch by ID"""
        error = check_permission("can_edit_branch")
        if error:
            return error

        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return {"error": "Request body is required"}, 400

        try:
            branch = db.session.query(Branch).filter_by(id=branch_id).first()
            if not branch:
                return {"error": "Branch not found"}, 404

            try:
                data = branch_schema.load(json_data, partial=True)
            except ValidationError as err:
                return {"error": "Validation error", "details": err.messages}, 400

            # Check for name uniqueness if name is being updated
            if "name" in data and data["name"] != branch.name:
                existing_branch = db.session.query(Branch).filter_by(name=data["name"]).first()
                if existing_branch:
                    return {"error": "Branch with this name already exists"}, 409

            for key, value in data.items():
                setattr(branch, key, value)

            db.session.commit()
            return branch_schema.dump(branch), 200
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error updating branch {branch_id}: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return {"error": "Branch with this name already exists"}, 409
            return {"error": "Data integrity constraint violation"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error updating branch {branch_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error updating branch {branch_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error updating branch {branch_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

    @branches_ns.doc('delete_branch')
    @branches_ns.response(200, 'Successfully deleted branch', success_model)
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.response(404, 'Branch not found', error_model)
    @branches_ns.response(409, 'Conflict - Cannot delete referenced branch', error_model)
    @branches_ns.response(500, 'Internal Server Error', error_model)
    @branches_ns.response(503, 'Service Unavailable', error_model)
    @jwt_required()
    def delete(self, branch_id):
        """Delete a specific branch by ID"""
        error = check_permission("can_delete_branch")
        if error:
            return error

        try:
            branch = db.session.query(Branch).filter_by(id=branch_id).first()
            if not branch:
                return {"error": "Branch not found"}, 404
                
            db.session.delete(branch)
            db.session.commit()
            return {"message": f"Branch {branch_id} deleted successfully"}, 200
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error deleting branch {branch_id}: {str(e)}")
            return {"error": "Cannot delete branch: it may be referenced by warehouses or other records"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error deleting branch {branch_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error deleting branch {branch_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error deleting branch {branch_id}: {str(e)}")
            return {"error": "Internal server error"}, 500
