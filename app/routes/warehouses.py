from flask import Blueprint, request, jsonify
from flask_restx import Resource
from marshmallow import ValidationError
from .. import db
from ..models import Warehouse
from ..schemas import WarehouseSchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission
from ..swagger import warehouses_ns, add_standard_responses
from ..swagger_models import (
    warehouse_model, warehouse_input_model, 
    pagination_model, error_model, success_model
)

bp = Blueprint("warehouses", __name__, url_prefix="/warehouses")

warehouse_schema = WarehouseSchema()
warehouses_schema = WarehouseSchema(many=True)


@warehouses_ns.route("/")
class WarehouseList(Resource):
    @warehouses_ns.doc('list_warehouses')
    @warehouses_ns.marshal_with(pagination_model, code=200, description='Successfully retrieved warehouses')
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @warehouses_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @jwt_required()
    def get(self):
        """Get all warehouses with pagination"""
        error = check_permission("can_read_warehouse")
        if error:
            return error

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        query = db.session.query(Warehouse).paginate(page=page, per_page=per_page, error_out=False)



        return {
            "items": warehouses_schema.dump(query.items),
            "total": query.total,
            "page": query.page,
            "pages": query.pages
        }

    @warehouses_ns.doc('create_warehouse')
    @warehouses_ns.expect(warehouse_input_model)
    @warehouses_ns.marshal_with(warehouse_model, code=201, description='Successfully created warehouse')
    @warehouses_ns.response(400, 'Bad Request', error_model)
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @jwt_required()
    def post(self):
        """Create a new warehouse"""
        error = check_permission("can_edit_warehouse")
        if error:
            return error

        try:
            data = warehouse_schema.load(request.get_json())
        except ValidationError as err:
            return {"errors": err.messages}, 400

        warehouse = Warehouse(**data)
        db.session.add(warehouse)
        db.session.commit()

        return warehouse_schema.dump(warehouse), 201


@warehouses_ns.route("/<int:warehouse_id>")
class WarehouseResource(Resource):
    @warehouses_ns.doc('get_warehouse')
    @warehouses_ns.marshal_with(warehouse_model, code=200, description='Successfully retrieved warehouse')
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.response(404, 'Warehouse not found', error_model)
    @jwt_required()
    def get(self, warehouse_id):
        """Get a specific warehouse by ID"""
        error = check_permission("can_read_warehouse")
        if error:
            return error

        warehouse = db.session.query(Warehouse).filter_by(id=warehouse_id).first()
        if not warehouse:
            return {"error": "Warehouse not found"}, 404
        return warehouse_schema.dump(warehouse)

    @warehouses_ns.doc('update_warehouse')
    @warehouses_ns.expect(warehouse_input_model, validate=False)
    @warehouses_ns.marshal_with(warehouse_model, code=200, description='Successfully updated warehouse')
    @warehouses_ns.response(400, 'Bad Request', error_model)
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.response(404, 'Warehouse not found', error_model)
    @jwt_required()
    def put(self, warehouse_id):
        """Update a specific warehouse by ID"""
        error = check_permission("can_edit_warehouse")
        if error:
            return error

        warehouse = db.session.query(Warehouse).filter_by(id=warehouse_id).first()
        if not warehouse:
            return {"error": "Warehouse not found"}, 404

        try:
            # partial=True allows updating only some fields
            data = warehouse_schema.load(request.get_json(), partial=True)
        except ValidationError as err:
            return {"errors": err.messages}, 400

        # Apply changes
        for key, value in data.items():
            setattr(warehouse, key, value)

        db.session.commit()

        # Return updated warehouse with asset count
        result = warehouse_schema.dump(warehouse)
        return result, 200

    @warehouses_ns.doc('delete_warehouse')
    @warehouses_ns.marshal_with(success_model, code=200, description='Successfully deleted warehouse')
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.response(404, 'Warehouse not found', error_model)
    @jwt_required()
    def delete(self, warehouse_id):
        """Delete a specific warehouse by ID"""
        error = check_permission("can_delete_warehouse")
        if error:
            return error

        warehouse = db.session.query(Warehouse).filter_by(id=warehouse_id).first()
        if not warehouse:
            return {"error": "Warehouse not found"}, 404
        db.session.delete(warehouse)
        db.session.commit()
        return {"message": f"Warehouse {warehouse_id} deleted successfully"}, 200
