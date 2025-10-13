from flask import Blueprint, request, jsonify
from flask_restx import Resource
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
import logging
from marshmallow import ValidationError
from .. import db
from ..models import JobDescription
from ..schemas import JobDescriptionSchema
from flask_jwt_extended import jwt_required
from ..utils import admin_required, error_response, create_error_response, create_validation_error_response
from ..swagger import job_roles_ns, add_standard_responses
from ..swagger_models import (
    job_role_model, job_role_input_model, pagination_model, 
    error_model, success_model
)

bp = Blueprint("job_roles", __name__, url_prefix="/job_roles")

job_role_schema = JobDescriptionSchema()
job_roles_schema = JobDescriptionSchema(many=True)


@job_roles_ns.route("/")
class JobRoleList(Resource):
    @job_roles_ns.doc('list_job_roles')
    @job_roles_ns.response(200, 'Successfully retrieved job roles', pagination_model)
    @job_roles_ns.response(400, 'Bad Request', error_model)
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.response(403, 'Forbidden', error_model)
    @job_roles_ns.response(500, 'Internal Server Error', error_model)
    @job_roles_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @job_roles_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @jwt_required()
    @admin_required
    def get(self):
        """Get all job roles with pagination"""
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        
        # Validate pagination parameters
        if page < 1:
            return create_error_response("Page number must be positive", 400, "page")
        if per_page < 1 or per_page > 100:
            return create_error_response("Items per page must be between 1 and 100", 400, "per_page")

        try:
            # Order by ID descending for consistent ordering
            query = db.session.query(JobDescription).order_by(JobDescription.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

            return {
                "items": job_roles_schema.dump(query.items),
                "total": query.total,
                "page": query.page,
                "pages": query.pages
            }
        except OperationalError as e:
            logging.error(f"Database operational error in job roles list: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            logging.error(f"Database error in job roles list: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            logging.error(f"Unexpected error in job roles list: {str(e)}")
            return create_error_response("Internal server error", 500)

    @job_roles_ns.doc('create_job_role')
    @job_roles_ns.expect(job_role_input_model)
    @job_roles_ns.response(201, 'Successfully created job role', job_role_model)
    @job_roles_ns.response(400, 'Bad Request', error_model)
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.response(403, 'Forbidden', error_model)
    @job_roles_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @job_roles_ns.response(500, 'Internal Server Error', error_model)
    #@jwt_required()
    #@admin_required
    def post(self):
        """Create a new job role"""
        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return create_error_response("Request body is required", 400)

        try:
            data = job_role_schema.load(json_data)
        except ValidationError as err:
            return create_validation_error_response(err.messages)

        # Validate required fields
        if "name" not in json_data:
            return create_error_response("Missing required field: name", 400, "name")

        try:
            # Create new job description
            job_desc = JobDescription(
                name=json_data["name"],
                can_read_branch=json_data.get("can_read_branch", False),
                can_edit_branch=json_data.get("can_edit_branch", False),
                can_delete_branch=json_data.get("can_delete_branch", False),
                can_read_warehouse=json_data.get("can_read_warehouse", False),
                can_edit_warehouse=json_data.get("can_edit_warehouse", False),
                can_delete_warehouse=json_data.get("can_delete_warehouse", False),
                can_read_asset=json_data.get("can_read_asset", False),
                can_edit_asset=json_data.get("can_edit_asset", False),
                can_delete_asset=json_data.get("can_delete_asset", False),
                can_print_barcode=json_data.get("can_print_barcode", False),
                can_make_report=json_data.get("can_make_report", False),
                can_make_transaction=json_data.get("can_make_transaction", False),
            )

            db.session.add(job_desc)
            db.session.commit()

            return job_role_schema.dump(job_desc), 201
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error creating job role: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return create_error_response("Job role with this name already exists", 409, "name")
            return create_error_response("Data integrity constraint violation", 409)
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error creating job role: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error creating job role: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error creating job role: {str(e)}")
            return create_error_response("Internal server error", 500)


@job_roles_ns.route("/<int:role_id>")
class JobRoleResource(Resource):
    @job_roles_ns.doc('get_job_role')
    @job_roles_ns.response(200, 'Successfully retrieved job role', job_role_model)
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.response(403, 'Forbidden', error_model)
    @job_roles_ns.response(404, 'Job role not found', error_model)
    @job_roles_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    @admin_required
    def get(self, role_id):
        """Get a specific job role by ID"""
        try:
            job_desc = db.session.query(JobDescription).filter_by(id=role_id).first()
            if not job_desc:
                return create_error_response("Job role not found", 404)
            return job_role_schema.dump(job_desc)
        except OperationalError as e:
            logging.error(f"Database operational error getting job role {role_id}: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            logging.error(f"Database error getting job role {role_id}: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            logging.error(f"Unexpected error getting job role {role_id}: {str(e)}")
            return create_error_response("Internal server error", 500)

    @job_roles_ns.doc('update_job_role')
    @job_roles_ns.expect(job_role_input_model, validate=False)
    @job_roles_ns.response(200, 'Successfully updated job role', job_role_model)
    @job_roles_ns.response(400, 'Bad Request', error_model)
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.response(403, 'Forbidden', error_model)
    @job_roles_ns.response(404, 'Job role not found', error_model)
    @job_roles_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @job_roles_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    @admin_required
    def put(self, role_id):
        """Update a specific job role by ID (Admin only)"""
        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return create_error_response("Request body is required", 400)

        try:
            job_desc = db.session.query(JobDescription).filter_by(id=role_id).first()
            if not job_desc:
                return create_error_response("Job role not found", 404)

            # Check for name uniqueness if name is being updated
            if "name" in json_data and json_data["name"] != job_desc.name:
                existing_job = db.session.query(JobDescription).filter_by(name=json_data["name"]).first()
                if existing_job:
                    return create_error_response("Job role with this name already exists", 409, "name")

            # Update fields if present
            if "name" in json_data:
                job_desc.name = json_data["name"]

            for field in [
                "can_read_branch", "can_edit_branch", "can_delete_branch",
                "can_read_warehouse", "can_edit_warehouse", "can_delete_warehouse",
                "can_read_asset", "can_edit_asset", "can_delete_asset",
                "can_print_barcode", "can_make_report", "can_make_transaction"
            ]:
                if field in json_data:
                    setattr(job_desc, field, json_data[field])

            db.session.commit()
            return job_role_schema.dump(job_desc), 200
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error updating job role {role_id}: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return create_error_response("Job role with this name already exists", 409, "name")
            return create_error_response("Data integrity constraint violation", 409)
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error updating job role {role_id}: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error updating job role {role_id}: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error updating job role {role_id}: {str(e)}")
            return create_error_response("Internal server error", 500)

    @job_roles_ns.doc('delete_job_role')
    @job_roles_ns.response(200, 'Successfully deleted job role', success_model)
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.response(403, 'Forbidden', error_model)
    @job_roles_ns.response(404, 'Job role not found', error_model)
    @job_roles_ns.response(409, 'Conflict - Cannot delete referenced job role', error_model)
    @job_roles_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    @admin_required
    def delete(self, role_id):
        """Delete a specific job role by ID (Admin only)"""
        try:
            role = db.session.query(JobDescription).filter_by(id=role_id).first()
            if not role:
                return create_error_response("Job role not found", 404)
                
            db.session.delete(role)
            db.session.commit()
            return {"message": f"Role {role_id} deleted successfully"}, 200
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error deleting job role {role_id}: {str(e)}")
            return create_error_response("Cannot delete job role: it may be referenced by users", 409)
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error deleting job role {role_id}: {str(e)}")
            return create_error_response("Database connection error", 503)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error deleting job role {role_id}: {str(e)}")
            return create_error_response("Database error occurred", 500)
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error deleting job role {role_id}: {str(e)}")
            return create_error_response("Internal server error", 500)
