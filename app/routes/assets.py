from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
import logging
from flask import Blueprint, request, jsonify
from flask_restx import Resource
from marshmallow import ValidationError
import logging
from .. import db
from ..models import FixedAsset, Category, AssetTransaction, Transaction
from ..schemas import FixedAssetSchema, CategorySchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission, generate_barcode, generate_unique_product_code, error_response
from ..swagger import assets_ns, categories_ns, add_standard_responses, api
from ..swagger_models import (
    asset_model, asset_input_model, category_model, category_input_model,
    pagination_model, error_model, success_model, barcode_model, asset_search_response_model
)

bp = Blueprint("assets", __name__, url_prefix="/assets")
asset_schema = FixedAssetSchema()
assets_schema = FixedAssetSchema(many=True)
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)

@categories_ns.route("/")
class CategoryList(Resource):
    @categories_ns.doc('list_categories', security='Bearer Auth')
    @categories_ns.response(200, 'Successfully retrieved categories', pagination_model)
    @categories_ns.response(400, 'Bad Request', error_model)
    @categories_ns.response(401, 'Unauthorized', error_model)
    @categories_ns.response(403, 'Forbidden', error_model)
    @categories_ns.response(500, 'Internal Server Error', error_model)
    @categories_ns.param('page', 'Page number', type=int, default=1)
    @categories_ns.param('per_page', 'Items per page', type=int, default=10)
    @jwt_required()
    def get(self):
        """Get all categories with pagination"""
        error = check_permission("can_read_asset")
        if error:
            return error

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        
        # Validate pagination parameters
        if page < 1:
            return {"error": "Page number must be positive"}, 400
        if per_page < 1 or per_page > 100:
            return {"error": "Items per page must be between 1 and 100"}, 400

        try:
            paginated = Category.query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                "items": categories_schema.dump(paginated.items),
                "total": paginated.total,
                "page": paginated.page,
                "pages": paginated.pages
            }
        except OperationalError as e:
            logging.error(f"Database operational error in category list: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error in category list: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error in category list: {str(e)}")
            return {"error": "Internal server error"}, 500

    @categories_ns.doc('create_category', security='Bearer Auth')
    @categories_ns.expect(category_input_model)
    @categories_ns.response(201, 'Successfully created category', category_model)
    @categories_ns.response(400, 'Bad Request', error_model)
    @categories_ns.response(401, 'Unauthorized', error_model)
    @categories_ns.response(403, 'Forbidden', error_model)
    @categories_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @categories_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def post(self):
        """Create a new category"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return {"error": "Request body is required"}, 400

        try:
            data = category_schema.load(json_data)
            new_category = Category(**data)
            db.session.add(new_category)
            db.session.commit()
            return category_schema.dump(new_category), 201
        except ValidationError as err:
            return {"error": "Validation error", "details": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error creating category: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return {"error": "Category with this name already exists"}, 409
            return {"error": "Data integrity constraint violation"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error creating category: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error creating category: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error creating category: {str(e)}")
            return {"error": "Internal server error"}, 500


@categories_ns.route("/<int:category_id>")
class CategoryResource(Resource):
    @categories_ns.doc('get_category', security='Bearer Auth')
    @categories_ns.response(200, 'Successfully retrieved category', category_model)
    @categories_ns.response(401, 'Unauthorized', error_model)
    @categories_ns.response(403, 'Forbidden', error_model)
    @categories_ns.response(404, 'Category not found', error_model)
    @categories_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def get(self, category_id):
        """Get a specific category"""
        error = check_permission("can_read_asset")
        if error:
            return error

        try:
            category = db.session.get(Category, category_id)
            if not category:
                return {"error": "Category not found"}, 404
            return category_schema.dump(category)
        except OperationalError as e:
            logging.error(f"Database operational error getting category {category_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error getting category {category_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error getting category {category_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

    @categories_ns.doc('update_category', security='Bearer Auth')
    @categories_ns.expect(category_input_model)
    @categories_ns.response(200, 'Successfully updated category', category_model)
    @categories_ns.response(400, 'Bad Request', error_model)
    @categories_ns.response(401, 'Unauthorized', error_model)
    @categories_ns.response(403, 'Forbidden', error_model)
    @categories_ns.response(404, 'Category not found', error_model)
    @categories_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @categories_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def put(self, category_id):
        """Update a category"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return {"error": "Request body is required"}, 400

        try:
            category = db.session.get(Category, category_id)
            if not category:
                return {"error": "Category not found"}, 404

            try:
                data = category_schema.load(json_data, partial=True)
            except ValidationError as err:
                return {"error": "Validation error", "details": err.messages}, 400
            
            for key, value in data.items():
                setattr(category, key, value)
            db.session.commit()
            return category_schema.dump(category)
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error updating category {category_id}: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return {"error": "Category with this name already exists"}, 409
            return {"error": "Data integrity constraint violation"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error updating category {category_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error updating category {category_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error updating category {category_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

    @categories_ns.doc('delete_category', security='Bearer Auth')
    @categories_ns.response(200, 'Successfully deleted category', success_model)
    @categories_ns.response(401, 'Unauthorized', error_model)
    @categories_ns.response(403, 'Forbidden', error_model)
    @categories_ns.response(404, 'Category not found', error_model)
    @categories_ns.response(409, 'Conflict - Cannot delete referenced category', error_model)
    @categories_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def delete(self, category_id):
        """Delete a category"""
        error = check_permission("can_delete_asset")
        if error:
            return error

        try:
            category = db.session.get(Category, category_id)
            if not category:
                return {"error": "Category not found"}, 404

            db.session.delete(category)
            db.session.commit()
            return {"message": f"Category {category_id} deleted successfully"}
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error deleting category {category_id}: {str(e)}")
            return {"error": "Cannot delete category: it may be referenced by assets"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error deleting category {category_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error deleting category {category_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error deleting category {category_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

@assets_ns.route("/")
class AssetList(Resource):
    @assets_ns.doc('list_assets', security='Bearer Auth')
    @assets_ns.response(200, 'Successfully retrieved assets', pagination_model)
    @assets_ns.response(400, 'Bad Request', error_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(500, 'Internal Server Error', error_model)
    @assets_ns.param('page', 'Page number', type=int, default=1)
    @assets_ns.param('per_page', 'Items per page', type=int, default=10)
    @assets_ns.param('category_ids', 'Filter assets by category IDs (comma-separated, e.g., "1,2,3" or single "1")', type=str)
    @jwt_required()
    def get(self):
        """Get all fixed assets with pagination and optional category filtering
        
        Supports filtering by multiple categories using comma-separated category IDs.
        Examples:
        - Single category: ?category_ids=1
        - Multiple categories: ?category_ids=1,2,3
        """
        error = check_permission("can_read_asset")
        if error:
            return error

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        category_ids_param = request.args.get("category_ids", type=str)
        
        # Validate pagination parameters
        if page < 1:
            return {"error": "Page number must be positive"}, 400
        if per_page < 1 or per_page > 100:
            return {"error": "Items per page must be between 1 and 100"}, 400

        try:
            query = FixedAsset.query
            
            # Handle multiple category filtering
            if category_ids_param:
                try:
                    # Parse comma-separated category IDs
                    category_ids = [int(id.strip()) for id in category_ids_param.split(',') if id.strip()]
                    if category_ids:
                        # Filter assets that belong to any of the specified categories
                        query = query.filter(FixedAsset.category_id.in_(category_ids))
                except ValueError:
                    return {"error": "Invalid category_ids format. Use comma-separated integers (e.g., '1,2,3')"}, 400

            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                "items": assets_schema.dump(paginated.items),
                "total": paginated.total,
                "page": paginated.page,
                "pages": paginated.pages
            }
        except OperationalError as e:
            logging.error(f"Database operational error in asset list: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error in asset list: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error in asset list: {str(e)}")
            return {"error": "Internal server error"}, 500
    
    @assets_ns.doc('create_asset', security='Bearer Auth')
    @assets_ns.expect(asset_input_model)
    @assets_ns.response(201, 'Successfully created asset', asset_model)
    @assets_ns.response(400, 'Bad Request', error_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @assets_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def post(self):
        """Create a new fixed asset"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return {"error": "Request body is required"}, 400

        try:
            data = asset_schema.load(json_data)
            new_asset = FixedAsset(**data)
            db.session.add(new_asset)
            db.session.commit()
            return asset_schema.dump(new_asset), 201
        except ValidationError as err:
            return {"error": "Validation error", "details": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error creating asset: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return {"error": "Asset with this identifier already exists"}, 409
            return {"error": "Data integrity constraint violation"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error creating asset: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error creating asset: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error creating asset: {str(e)}")
            return {"error": "Internal server error"}, 500


@assets_ns.route("/<int:asset_id>/barcode")
class AssetBarcode(Resource):
    @assets_ns.doc('get_asset_barcode', security='Bearer Auth')
    @assets_ns.response(200, 'Successfully generated barcode', barcode_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @assets_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def get(self, asset_id):
        """Generate a barcode for a specific asset"""
        error = check_permission("can_print_barcode")
        if error:
            return error
            
        try:
            # Get the asset
            asset = db.session.query(FixedAsset).filter_by(id=asset_id).first()
            if not asset:
                return {"error": "Asset not found"}, 404
                
            # Check if asset has a product code, if not generate one
            if not asset.product_code:
                asset.product_code = generate_unique_product_code()
                db.session.commit()
                
            # Generate barcode
            barcode_data = generate_barcode(asset.product_code)
            return barcode_data
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error generating barcode for asset {asset_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error generating barcode for asset {asset_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error generating barcode for asset {asset_id}: {str(e)}")
            return {"error": "Internal server error"}, 500



@assets_ns.route("/<int:asset_id>")
class AssetResource(Resource):
    @assets_ns.doc('get_asset', security='Bearer Auth')
    @assets_ns.response(200, 'Successfully retrieved asset', asset_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @assets_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def get(self, asset_id):
        """Get a specific asset"""
        error = check_permission("can_read_asset")
        if error:
            return error

        try:
            asset = db.session.get(FixedAsset, asset_id)
            if not asset:
                return {"error": "Asset not found"}, 404
            return asset_schema.dump(asset)
        except OperationalError as e:
            logging.error(f"Database operational error getting asset {asset_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error getting asset {asset_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error getting asset {asset_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

    @assets_ns.doc('update_asset', security='Bearer Auth')
    @assets_ns.expect(asset_input_model)
    @assets_ns.response(200, 'Successfully updated asset', asset_model)
    @assets_ns.response(400, 'Bad Request', error_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @assets_ns.response(409, 'Conflict - Duplicate entry', error_model)
    @assets_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def put(self, asset_id):
        """Update a specific asset"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        # Validate request body
        json_data = request.get_json()
        if not json_data:
            return {"error": "Request body is required"}, 400

        try:
            asset = db.session.get(FixedAsset, asset_id)
            if not asset:
                return {"error": "Asset not found"}, 404

            try:
                data = asset_schema.load(json_data, partial=True)
            except ValidationError as err:
                return {"error": "Validation error", "details": err.messages}, 400
            
            for key, value in data.items():
                setattr(asset, key, value)
            db.session.commit()
            return asset_schema.dump(asset)
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error updating asset {asset_id}: {str(e)}")
            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                return {"error": "Asset with this identifier already exists"}, 409
            return {"error": "Data integrity constraint violation"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error updating asset {asset_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error updating asset {asset_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error updating asset {asset_id}: {str(e)}")
            return {"error": "Internal server error"}, 500

    @assets_ns.doc('delete_asset', security='Bearer Auth')
    @assets_ns.response(200, 'Successfully deleted asset', success_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @assets_ns.response(409, 'Conflict - Cannot delete referenced asset', error_model)
    @assets_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def delete(self, asset_id):
        """Delete a specific asset"""
        error = check_permission("can_delete_asset")
        if error:
            return error

        try:
            asset = db.session.get(FixedAsset, asset_id)
            if not asset:
                return {"error": "Asset not found"}, 404

            db.session.delete(asset)
            db.session.commit()
            return {"message": f"Asset {asset_id} deleted successfully"}
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error deleting asset {asset_id}: {str(e)}")
            return {"error": "Cannot delete asset: it may be referenced by transactions"}, 409
        except OperationalError as e:
            db.session.rollback()
            logging.error(f"Database operational error deleting asset {asset_id}: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error deleting asset {asset_id}: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error deleting asset {asset_id}: {str(e)}")
            return {"error": "Internal server error"}, 500



@assets_ns.route("/search")
class AssetSearch(Resource):
    @assets_ns.doc('search_assets', security='Bearer Auth')
    @assets_ns.param('q', 'Search query (text for name search or number for barcode search)', required=True, type=str)
    @assets_ns.param('page', 'Page number', type=int, default=1)
    @assets_ns.param('per_page', 'Items per page', type=int, default=10)
    @assets_ns.response(200, 'Successfully searched assets', asset_search_response_model)
    @assets_ns.response(400, 'Missing Search Query', error_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(500, 'Internal Server Error', error_model)
    @jwt_required()
    def get(self):
        """Search assets by name (text) or product code/barcode (number)
        
        - If query contains letters: searches in name_ar and name_en fields
        - If query is numeric: searches by exact product_code match
        """
        error = check_permission("can_read_asset")
        if error:
            return error

        search_query = request.args.get('q', '').strip()
        if not search_query:
            return {"error": "Search query parameter 'q' is required"}, 400

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        
        # Validate pagination parameters
        if page < 1:
            return {"error": "Page number must be positive"}, 400
        if per_page < 1 or per_page > 100:
            return {"error": "Items per page must be between 1 and 100"}, 400

        try:
            # Build base query
            query = FixedAsset.query.filter(FixedAsset.is_active == True)
            
            
            # Determine search type and build search conditions
            search_conditions = []
            
            # Check if query is purely numeric (for barcode search)
            if search_query.isdigit():
                # Pure number - search by product_code (exact match)
                search_conditions.append(FixedAsset.product_code == search_query)
            else:
                # Contains letters - search by name (partial match, case-insensitive)
                name_search = f"%{search_query}%"
                search_conditions.extend([
                    FixedAsset.name_ar.ilike(name_search),
                    FixedAsset.name_en.ilike(name_search)
                ])
                
                # Also check if it might be a product_code (partial match)
                if search_query.replace('-', '').replace('_', '').isalnum():
                    search_conditions.append(FixedAsset.product_code.ilike(f"%{search_query}%"))
            
            # Apply search conditions with OR logic
            if search_conditions:
                query = query.filter(or_(*search_conditions))
            else:
                # If no conditions, return empty result
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "pages": 0
                }
            
            # Order results
            if search_query.isdigit():
                # For numeric queries, order by product_code match, then by name
                query = query.order_by(FixedAsset.product_code, FixedAsset.name_en)
            else:
                # For text queries, order by name
                query = query.order_by(FixedAsset.name_en, FixedAsset.name_ar)
            
            # Execute paginated query
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return {
                "items": assets_schema.dump(paginated.items),
                "total": paginated.total,
                "page": paginated.page,
                "pages": paginated.pages
            }
            
        except OperationalError as e:
            logging.error(f"Database operational error in asset search: {str(e)}")
            return {"error": "Database connection error"}, 503
        except SQLAlchemyError as e:
            logging.error(f"Database error in asset search: {str(e)}")
            return {"error": "Database error occurred"}, 500
        except Exception as e:
            logging.error(f"Unexpected error in asset search: {str(e)}")
            return {"error": "Internal server error"}, 500