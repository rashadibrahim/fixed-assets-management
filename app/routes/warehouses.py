from flask import Blueprint, request, jsonify
from flask_restx import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
import logging
from .. import db
from ..models import Warehouse
from ..schemas import WarehouseSchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission, error_response
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
    @warehouses_ns.response(200, 'Successfully retrieved warehouses', pagination_model)
    @warehouses_ns.response(400, 'Bad Request', error_model)
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.response(500, 'Internal Server Error', error_model)
    @warehouses_ns.response(503, 'Service Unavailable', error_model)
    @warehouses_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @warehouses_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @warehouses_ns.param('search', 'Search in warehouse English name', type=str)
    @jwt_required()
    def get(self):
        """Get all warehouses with pagination and optional search"""
        error = check_permission("can_read_warehouse")
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
            query = db.session.query(Warehouse)
            
            # Apply search filter if provided
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(Warehouse.name_en.ilike(search_pattern))
            
            # Order results by ID descending for consistent ordering
            query = query.order_by(Warehouse.id.desc())
            
            # Apply pagination
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return {
                "items": warehouses_schema.dump(paginated.items),
                "total": paginated.total,
                "page": paginated.page,
                "pages": paginated.pages
            }
        except OperationalError as e:
            logging.error(f"Database operational error in warehouse list: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error in warehouse list: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error in warehouse list: {str(e)}")
            return {"error": "Internal server error"}, 500

    @warehouses_ns.doc('create_warehouse')
    @warehouses_ns.expect(warehouse_input_model)
    @warehouses_ns.response(201, 'Successfully created warehouse', warehouse_model)
    @warehouses_ns.response(400, 'Bad Request', error_model)
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @jwt_required()
    def post(self):
        """Create a new warehouse"""
        error = check_permission("can_edit_warehouse")
        if error:
            return error

        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return {"error": "Request body is required"}, 400
            
        try:
            data = warehouse_schema.load(json_data)
        except ValidationError as err:
            return {"error": "Validation error", "details": err.messages}, 400
        except Exception as e:
            return {"error": "Invalid JSON format"}, 400

        try:
            warehouse = Warehouse(**data)
            db.session.add(warehouse)
            db.session.commit()
            
            return warehouse_schema.dump(warehouse), 201
            
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error creating warehouse: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return {"error": "Warehouse with this name already exists"}, 409
            return {"error": "Data integrity constraint violation"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error creating warehouse: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error creating warehouse: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error creating warehouse: {str(e)}")
            return {"error": "Internal server error"}, 500


@warehouses_ns.route("/<int:warehouse_id>")
class WarehouseResource(Resource):
    @warehouses_ns.doc('get_warehouse')
    @warehouses_ns.response(200, 'Successfully retrieved warehouse', warehouse_model)
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.response(404, 'Warehouse not found', error_model)
    @warehouses_ns.response(500, 'Internal Server Error', error_model)
    @warehouses_ns.response(503, 'Service Unavailable', error_model)
    @jwt_required()
    def get(self, warehouse_id):
        """Get a specific warehouse by ID"""
        error = check_permission("can_read_warehouse")
        if error:
            return error

        try:
            warehouse = db.session.query(Warehouse).filter_by(id=warehouse_id).first()
            if not warehouse:
                return {"error": "Warehouse not found"}, 404
            return warehouse_schema.dump(warehouse)
        except OperationalError as e:
            logging.error(f"Database operational error getting warehouse {warehouse_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error getting warehouse {warehouse_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error getting warehouse {warehouse_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

    @warehouses_ns.doc('update_warehouse')
    @warehouses_ns.expect(warehouse_input_model, validate=False)
    @warehouses_ns.response(200, 'Successfully updated warehouse', warehouse_model)
    @warehouses_ns.response(400, 'Bad Request', error_model)
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.response(404, 'Warehouse not found', error_model)
    @warehouses_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @jwt_required()
    def put(self, warehouse_id):
        """Update a specific warehouse by ID"""
        error = check_permission("can_edit_warehouse")
        if error:
            return error

        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return {"error": "Request body is required"}, 400
            
        try:
            warehouse = db.session.query(Warehouse).filter_by(id=warehouse_id).first()
            if not warehouse:
                return {"error": "Warehouse not found"}, 404

            # Validate and load data
            try:
                # partial=True allows updating only some fields
                data = warehouse_schema.load(json_data, partial=True)
            except ValidationError as err:
                return {"error": "Validation error", "details": err.messages}, 400
            except Exception as e:
                return {"error": "Invalid JSON format"}, 400

            # Apply changes
            for key, value in data.items():
                setattr(warehouse, key, value)

            db.session.commit()

            # Return updated warehouse
            result = warehouse_schema.dump(warehouse)
            return result, 200
            
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error updating warehouse {warehouse_id}: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return {"error": "Warehouse with this name already exists"}, 409
            return {"error": "Data integrity constraint violation"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error updating warehouse {warehouse_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error updating warehouse {warehouse_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error updating warehouse {warehouse_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

    @warehouses_ns.doc('delete_warehouse')
    @warehouses_ns.response(200, 'Successfully deleted warehouse', success_model)
    @warehouses_ns.response(401, 'Unauthorized', error_model)
    @warehouses_ns.response(403, 'Forbidden', error_model)
    @warehouses_ns.response(404, 'Warehouse not found', error_model)
    @warehouses_ns.response(409, 'Conflict - Cannot delete referenced warehouse', error_model)
    @warehouses_ns.response(500, 'Internal Server Error', error_model)
    @warehouses_ns.response(503, 'Service Unavailable', error_model)
    @jwt_required()
    def delete(self, warehouse_id):
        """Delete a specific warehouse by ID"""
        error = check_permission("can_delete_warehouse")
        if error:
            return error

        try:
            warehouse = db.session.query(Warehouse).filter_by(id=warehouse_id).first()
            if not warehouse:
                return {"error": "Warehouse not found"}, 404
                
            db.session.delete(warehouse)
            db.session.commit()
            return {"message": f"Warehouse {warehouse_id} deleted successfully"}, 200
            
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error deleting warehouse {warehouse_id}: {str(e)}")
            return {"error": "Cannot delete warehouse: it may be referenced by other records"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error deleting warehouse {warehouse_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error deleting warehouse {warehouse_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error deleting warehouse {warehouse_id}: {str(e)}")
            return {"error": "Internal server error"}, 500
