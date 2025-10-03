from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, request, jsonify
from flask_restx import Resource
from marshmallow import ValidationError
import logging
from .. import db
from ..models import FixedAsset, Category
from ..schemas import FixedAssetSchema, CategorySchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission, generate_barcode, generate_unique_product_code
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
    @categories_ns.marshal_with(pagination_model)
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

        paginated = Category.query.paginate(page=page, per_page=per_page)
        return {
            "items": categories_schema.dump(paginated.items),
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages
        }

    @categories_ns.doc('create_category', security='Bearer Auth')
    @categories_ns.expect(category_input_model)
    @categories_ns.marshal_with(category_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new category"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        try:
            data = category_schema.load(request.get_json())
            new_category = Category(**data)
            db.session.add(new_category)
            db.session.commit()
            return category_schema.dump(new_category), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            error_str = str(e.orig)
            
            if "duplicate key value violates unique constraint" in error_str:
                return {
                    "error": "Duplicate entry",
                    "message": "A category with this information already exists in the system."
                }, 400
            else:
                return {
                    "error": "Database constraint violation",
                    "message": "The data provided violates database constraints."
                }, 400
        except Exception as e:
            db.session.rollback()
            return {
                "error": "Internal server error",
                "message": "An unexpected error occurred while creating the category."
            }, 500


@categories_ns.route("/<int:category_id>")
class CategoryResource(Resource):
    @categories_ns.doc('get_category', security='Bearer Auth')
    @categories_ns.marshal_with(category_model)
    @jwt_required()
    def get(self, category_id):
        """Get a specific category"""
        error = check_permission("can_read_asset")
        if error:
            return error

        category = db.session.get(Category, category_id)
        if not category:
            return {"error": "Category not found"}, 404
        return category_schema.dump(category)

    @categories_ns.doc('update_category', security='Bearer Auth')
    @categories_ns.expect(category_input_model)
    @categories_ns.marshal_with(category_model)
    @jwt_required()
    def put(self, category_id):
        """Update a category"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        category = db.session.get(Category, category_id)
        if not category:
            return {"error": "Category not found"}, 404

        try:
            data = category_schema.load(request.get_json(), partial=True)
            for key, value in data.items():
                setattr(category, key, value)
            db.session.commit()
            return category_schema.dump(category)
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            error_str = str(e.orig)
            
            if "duplicate key value violates unique constraint" in error_str:
                return {
                    "error": "Duplicate entry",
                    "message": "A category with this information already exists in the system."
                }, 400
            else:
                return {
                    "error": "Database constraint violation",
                    "message": "The data provided violates database constraints."
                }, 400
        except Exception as e:
            db.session.rollback()
            return {
                "error": "Internal server error",
                "message": "An unexpected error occurred while updating the category."
            }, 500

    @categories_ns.doc('delete_category', security='Bearer Auth')
    @categories_ns.marshal_with(success_model)
    @jwt_required()
    def delete(self, category_id):
        """Delete a category"""
        error = check_permission("can_delete_asset")
        if error:
            return error

        category = db.session.get(Category, category_id)
        if not category:
            return {"error": "Category not found"}, 404

        try:
            db.session.delete(category)
            db.session.commit()
            return {"message": f"Category {category_id} deleted successfully"}
        except Exception as e:
            db.session.rollback()
            return {"error": "Cannot delete category with associated assets"}, 400

@assets_ns.route("/")
class AssetList(Resource):
    @assets_ns.doc('list_assets', security='Bearer Auth')
    @assets_ns.marshal_with(pagination_model)
    @assets_ns.param('page', 'Page number', type=int, default=1)
    @assets_ns.param('per_page', 'Items per page', type=int, default=10)
    @assets_ns.param('category_id', 'Filter assets by category ID', type=int)
    @jwt_required()
    def get(self):
        """Get all fixed assets with pagination and optional category filtering"""
        error = check_permission("can_read_asset")
        if error:
            return error

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        category_id = request.args.get("category_id", type=int)

        query = FixedAsset.query
        if category_id:
            query = query.filter_by(category_id=category_id)

        paginated = query.paginate(page=page, per_page=per_page)
        return {
            "items": assets_schema.dump(paginated.items),
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages
        }
    
    @assets_ns.doc('create_asset', security='Bearer Auth')
    @assets_ns.expect(asset_input_model)
    @assets_ns.marshal_with(asset_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new fixed asset"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        data = request.get_json()
        required_fields = ["name_ar", "name_en", "category_id", "is_active"]
        missing = [field for field in required_fields if field not in data or data[field] in [None, ""]]
        errors = {}
        if missing:
            errors["missing_fields"] = {
                "message": "Required fields are missing.",
                "fields": missing
            }

        # Validate quantity
        if "quantity" in data and (not isinstance(data["quantity"], int) or data["quantity"] < 0):
            errors["quantity"] = {
                "message": "Quantity must be a non-negative integer.",
                "value": data["quantity"]
            }

        # Validate category existence
        from app.models import Category
        if "category_id" in data:
            category = db.session.get(Category, data["category_id"])
            if not category:
                errors["category_id"] = {
                    "message": "Category does not exist.",
                    "value": data["category_id"]
                }

        if errors:
            return {"errors": errors}, 400

        try:
            asset_data = asset_schema.load(data)
            new_asset = FixedAsset(**asset_data)
            db.session.add(new_asset)
            db.session.commit()
            return asset_schema.dump(new_asset), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
            if "duplicate key value violates unique constraint" in error_str and "product_code" in error_str:
                return {
                    "error": "Product code already exists",
                    "message": "The product code you provided is already in use. Please use a different product code.",
                    "field": "product_code"
                }, 400
            elif "duplicate key value violates unique constraint" in error_str:
                return {
                    "error": "Duplicate entry",
                    "message": "A record with this information already exists in the system."
                }, 400
            else:
                return {
                    "error": "Database constraint violation",
                    "message": "The data provided violates database constraints."
                }, 400
        except Exception as e:
            db.session.rollback()
            return {
                "error": "Internal server error",
                "message": "An unexpected error occurred while creating the asset."
            }, 500


@assets_ns.route("/<int:asset_id>/barcode")
class AssetBarcode(Resource):
    @assets_ns.doc('get_asset_barcode', security='Bearer Auth')
    @assets_ns.marshal_with(barcode_model, code=200, description='Successfully generated barcode')
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @jwt_required()
    def get(self, asset_id):
        """Generate a barcode for a specific asset"""
        error = check_permission("can_print_barcode")
        if error:
            return error
            
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



@assets_ns.route("/<int:asset_id>")
class AssetResource(Resource):
    @assets_ns.doc('get_asset', security='Bearer Auth')
    @assets_ns.marshal_with(asset_model)
    @jwt_required()
    def get(self, asset_id):
        """Get a specific asset"""
        error = check_permission("can_read_asset")
        if error:
            return error

        asset = db.session.get(FixedAsset, asset_id)
        if not asset:
            return {"error": "Asset not found"}, 404
        return asset_schema.dump(asset)

    @assets_ns.doc('update_asset', security='Bearer Auth')
    @assets_ns.expect(asset_input_model)
    @assets_ns.marshal_with(asset_model)
    @jwt_required()
    def put(self, asset_id):
        """Update a specific asset"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        asset = db.session.get(FixedAsset, asset_id)
        if not asset:
            return {"error": "Asset not found"}, 404

        try:
            data = asset_schema.load(request.get_json(), partial=True)
            for key, value in data.items():
                setattr(asset, key, value)
            db.session.commit()
            return asset_schema.dump(asset)
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except IntegrityError as e:
            db.session.rollback()
            error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            if "duplicate key value violates unique constraint" in error_str and "product_code" in error_str:
                return {
                    "error": "Product code already exists",
                    "message": "The product code you provided is already in use by another asset. Please use a different product code.",
                    "field": "product_code"
                }, 400
            elif "duplicate key value violates unique constraint" in error_str:
                return {
                    "error": "Duplicate entry",
                    "message": "A record with this information already exists in the system."
                }, 400
            else:
                return {
                    "error": "Database constraint violation",
                    "message": "The data provided violates database constraints."
                }, 400
        except Exception as e:
            db.session.rollback()
            
            # Check if it's actually an IntegrityError that wasn't caught above
            if "duplicate key value violates unique constraint" in str(e) and "product_code" in str(e):
                return {
                    "error": "Product code already exists",
                    "message": "The product code you provided is already in use by another asset. Please use a different product code.",
                    "field": "product_code"
                }, 400
            elif "duplicate key value violates unique constraint" in str(e):
                return {
                    "error": "Duplicate entry",
                    "message": "A record with this information already exists in the system."
                }, 400
            
            return {
                "error": "Internal server error",
                "message": "An unexpected error occurred while updating the asset."
            }, 500

    @assets_ns.doc('delete_asset', security='Bearer Auth')
    @assets_ns.marshal_with(success_model)
    @jwt_required()
    def delete(self, asset_id):
        """Delete a specific asset"""
        error = check_permission("can_delete_asset")
        if error:
            return error

        asset = db.session.get(FixedAsset, asset_id)
        if not asset:
            return {"error": "Asset not found"}, 404

        db.session.delete(asset)
        db.session.commit()
        return {"message": f"Asset {asset_id} deleted successfully"}



# Searching Endpoint
@assets_ns.route("/search")
class AssetSearch(Resource):
    @assets_ns.doc('search_assets', security='Bearer Auth')
    @assets_ns.param('q', 'Search query (text for name search or number for barcode search)', required=True, type=str)
    @assets_ns.param('page', 'Page number', type=int, default=1)
    @assets_ns.param('per_page', 'Items per page', type=int, default=10)
    @assets_ns.marshal_with(asset_search_response_model)
    @assets_ns.response(400, 'Missing Search Query', error_model)
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
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            return {"error": f"Search error: {str(e)}"}, 500