from flask import Blueprint, request, jsonify
from flask_restx import Resource
from .. import db
from ..models import JobDescription
from ..schemas import JobDescriptionSchema
from flask_jwt_extended import jwt_required
from ..utils import admin_required
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
    @job_roles_ns.marshal_with(pagination_model, code=200, description='Successfully retrieved job roles')
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @job_roles_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @jwt_required()
    def get(self):
        """Get all job roles with pagination"""
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        query = db.session.query(JobDescription).paginate(page=page, per_page=per_page, error_out=False)

        return {
            "items": job_roles_schema.dump(query.items),
            "total": query.total,
            "page": query.page,
            "pages": query.pages
        }

    @job_roles_ns.doc('create_job_role')
    @job_roles_ns.expect(job_role_input_model)
    @job_roles_ns.marshal_with(job_role_model, code=201, description='Successfully created job role')
    @job_roles_ns.response(400, 'Bad Request', error_model)
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.response(403, 'Forbidden', error_model)
    @jwt_required()
    @admin_required
    def post(self):
        """Create a new job role (Admin only)"""
        data = request.get_json()

        # ✅ Validate required fields
        if "name" not in data:
            return {"error": "Missing required field: name"}, 400

        # ✅ Create new job description
        job_desc = JobDescription(
            name=data["name"],
            can_read_branch=data.get("can_read_branch", False),
            can_edit_branch=data.get("can_edit_branch", False),
            can_delete_branch=data.get("can_delete_branch", False),
            can_read_warehouse=data.get("can_read_warehouse", False),
            can_edit_warehouse=data.get("can_edit_warehouse", False),
            can_delete_warehouse=data.get("can_delete_warehouse", False),
            can_read_asset=data.get("can_read_asset", False),
            can_edit_asset=data.get("can_edit_asset", False),
            can_delete_asset=data.get("can_delete_asset", False),
            can_print_barcode=data.get("can_print_barcode", False),
        )

        db.session.add(job_desc)
        db.session.commit()

        return job_role_schema.dump(job_desc), 201


@job_roles_ns.route("/<int:role_id>")
class JobRoleResource(Resource):
    @job_roles_ns.doc('update_job_role')
    @job_roles_ns.expect(job_role_input_model, validate=False)
    @job_roles_ns.marshal_with(job_role_model, code=200, description='Successfully updated job role')
    @job_roles_ns.response(400, 'Bad Request', error_model)
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.response(403, 'Forbidden', error_model)
    @job_roles_ns.response(404, 'Job role not found', error_model)
    @jwt_required()
    @admin_required
    def put(self, role_id):
        """Update a specific job role by ID (Admin only)"""
        job_desc = db.session.query(JobDescription).filter_by(id=role_id).first()
        if not job_desc:
            return {"error": "Job description not found"}, 404

        data = request.get_json()

        # ✅ Update fields if present
        if "name" in data:
            job_desc.name = data["name"]

        for field in [
            "can_read_branch", "can_edit_branch", "can_delete_branch",
            "can_read_warehouse", "can_edit_warehouse", "can_delete_warehouse",
            "can_read_asset", "can_edit_asset", "can_delete_asset",
            "can_print_barcode"
        ]:
            if field in data:
                setattr(job_desc, field, data[field])

        db.session.commit()

        return job_role_schema.dump(job_desc), 200

    @job_roles_ns.doc('delete_job_role')
    @job_roles_ns.marshal_with(success_model, code=200, description='Successfully deleted job role')
    @job_roles_ns.response(401, 'Unauthorized', error_model)
    @job_roles_ns.response(403, 'Forbidden', error_model)
    @job_roles_ns.response(404, 'Job role not found', error_model)
    @jwt_required()
    @admin_required
    def delete(self, role_id):
        """Delete a specific job role by ID (Admin only)"""
        role = db.session.query(JobDescription).filter_by(id=role_id).first()
        if not role:
            return {"error": "Job role not found"}, 404
        db.session.delete(role)
        db.session.commit()
        return {"message": f"Role {role_id} deleted successfully"}, 200