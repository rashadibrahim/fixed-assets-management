from flask import Blueprint, request, jsonify
from flask_restx import Resource, ValidationError
from .. import db
from ..models import Branch
from ..schemas import BranchSchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission
from ..swagger import branches_ns, add_standard_responses
from ..swagger_models import (
    branch_model, branch_input_model, branch_with_counts_model, 
    pagination_model, error_model, success_model
)

bp = Blueprint("branches", __name__, url_prefix="/branches")

branch_schema = BranchSchema()
branches_schema = BranchSchema(many=True)


@branches_ns.route("/")
class BranchList(Resource):
    @branches_ns.doc('list_branches')
    @branches_ns.marshal_with(pagination_model, code=200, description='Successfully retrieved branches')
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @branches_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @jwt_required()
    def get(self):
        """Get all branches with pagination, including warehouses count and assets count"""
        error = check_permission("can_read_branch")
        if error:
            return error

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        query = db.session.query(Branch).paginate(page=page, per_page=per_page, error_out=False)

        branches_data = []
        for branch in query.items:
            branch_dict = branch_schema.dump(branch)

            # Count warehouses in this branch
            warehouse_count = len(branch.warehouses)

            # Count assets across all warehouses in this branch
            asset_count = sum(len(warehouse.assets) for warehouse in branch.warehouses)

            branch_dict["warehouse_count"] = warehouse_count
            branch_dict["asset_count"] = asset_count

            branches_data.append(branch_dict)

        return {
            "items": branches_data,
            "total": query.total,
            "page": query.page,
            "pages": query.pages
        }


    @branches_ns.doc('create_branch')
    @branches_ns.expect(branch_input_model)
    @branches_ns.marshal_with(branch_model, code=201, description='Successfully created branch')
    @branches_ns.response(400, 'Bad Request', error_model)
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @jwt_required()
    def post(self):
        """Create a new branch"""
        error = check_permission("can_edit_branch")
        if error:
            return error

        try:
            data = branch_schema.load(request.get_json())
        except ValidationError as err:
            return {"errors": err.messages}, 400

        branch = Branch(**data)
        db.session.add(branch)
        db.session.commit()

        return branch_schema.dump(branch), 201


@branches_ns.route("/<int:branch_id>")
class BranchResource(Resource):
    @branches_ns.doc('get_branch')
    @branches_ns.marshal_with(branch_model, code=200, description='Successfully retrieved branch')
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.response(404, 'Branch not found', error_model)
    @jwt_required()
    def get(self, branch_id):
        """Get a specific branch by ID"""
        error = check_permission("can_read_branch")
        if error:
            return error

        branch = db.session.query(Branch).filter_by(id=branch_id).first()
        if not branch:
            return {"error": "Branch not found"}, 404
        return branch_schema.dump(branch)

    @branches_ns.doc('update_branch')
    @branches_ns.expect(branch_input_model, validate=False)
    @branches_ns.marshal_with(branch_model, code=200, description='Successfully updated branch')
    @branches_ns.response(400, 'Bad Request', error_model)
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.response(404, 'Branch not found', error_model)
    @jwt_required()
    def put(self, branch_id):
        """Update a specific branch by ID"""
        error = check_permission("can_edit_branch")
        if error:
            return error

        branch = db.session.query(Branch).filter_by(id=branch_id).first()
        if not branch:
            return {"error": "Branch not found"}, 404

        try:
            data = branch_schema.load(request.get_json(), partial=True)
        except ValidationError as err:
            return {"errors": err.messages}, 400

        for key, value in data.items():
            setattr(branch, key, value)

        db.session.commit()
        return branch_schema.dump(branch), 200

    @branches_ns.doc('delete_branch')
    @branches_ns.marshal_with(success_model, code=200, description='Successfully deleted branch')
    @branches_ns.response(401, 'Unauthorized', error_model)
    @branches_ns.response(403, 'Forbidden', error_model)
    @branches_ns.response(404, 'Branch not found', error_model)
    @jwt_required()
    def delete(self, branch_id):
        """Delete a specific branch by ID"""
        error = check_permission("can_delete_branch")
        if error:
            return error

        branch = db.session.query(Branch).filter_by(id=branch_id).first()
        if not branch:
            return {"error": "Branch not found"}, 404
        db.session.delete(branch)
        db.session.commit()
        return {"message": f"Branch {branch_id} deleted successfully"}, 200
