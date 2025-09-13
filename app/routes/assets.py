from flask import Blueprint, request, jsonify
from flask_restx import Resource
from marshmallow import ValidationError
from .. import db
from ..models import FixedAsset
from ..schemas import FixedAssetSchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission
from ..swagger import assets_ns, add_standard_responses
from ..swagger_models import (
    asset_model, asset_input_model, pagination_model, 
    error_model, success_model
)

bp = Blueprint("assets", __name__, url_prefix="/assets")
asset_schema = FixedAssetSchema()
assets_schema = FixedAssetSchema(many=True)


@assets_ns.route("/")
class AssetList(Resource):
    @assets_ns.doc('list_assets', security='Bearer Auth')
    @assets_ns.marshal_with(pagination_model, code=200, description='Successfully retrieved assets')
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @assets_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @assets_ns.param('category', 'Filter assets by category', type='string')
    @jwt_required()
    def get(self):
        """Get all fixed assets with pagination and optional category filtering"""
        error = check_permission("can_read_asset")
        if error:
            return error

        # pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        # category filter
        category = request.args.get("category", type=str)

        query = db.session.query(FixedAsset)
        if category:
            query = query.filter(FixedAsset.category == category)

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "items": assets_schema.dump(paginated.items),
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages
        }
    
    @assets_ns.doc('create_asset', security='Bearer Auth')
    @assets_ns.expect(asset_input_model)
    @assets_ns.marshal_with(asset_model, code=201, description='Successfully created asset')
    @assets_ns.response(400, 'Bad Request', error_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @jwt_required()
    def post(self):
        """Create a new fixed asset"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        try:
            # Validate incoming request JSON
            data = asset_schema.load(request.get_json())
        except ValidationError as err:
            return {"errors": err.messages}, 400

        # If valid, create asset
        new_asset = FixedAsset(**data)
        db.session.add(new_asset)
        db.session.commit()

        return asset_schema.dump(new_asset), 201


@assets_ns.route("/<int:asset_id>")
class AssetResource(Resource):
    @assets_ns.doc('get_asset', security='Bearer Auth')
    @assets_ns.marshal_with(asset_model, code=200, description='Successfully retrieved asset')
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @jwt_required()
    def get(self, asset_id):
        """Get a specific asset by ID"""
        error = check_permission("can_read_asset")
        if error:
            return error
        asset = db.session.query(FixedAsset).filter_by(id=asset_id).first()
        if not asset:
            return {"error": "Asset not found"}, 404
        return asset_schema.dump(asset)


    @assets_ns.doc('update_asset', security='Bearer Auth')
    @assets_ns.expect(asset_input_model, validate=False)
    @assets_ns.marshal_with(asset_model, code=200, description='Successfully updated asset')
    @assets_ns.response(400, 'Bad Request', error_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @jwt_required()
    def put(self, asset_id):
        """Update a specific asset by ID"""
        error = check_permission("can_edit_asset")
        if error:
            return error
        
        asset = db.session.query(FixedAsset).filter_by(id=asset_id).first()
        if not asset:
            return {"error": "Asset not found"}, 404
        try:
            data = asset_schema.load(request.get_json(), partial=True)  
            # `partial=True` allows sending only the fields you want to update
        except ValidationError as err:
            return {"errors": err.messages}, 400

        # Apply updates
        for key, value in data.items():
            setattr(asset, key, value)

        db.session.commit()

        return asset_schema.dump(asset), 200


    @assets_ns.doc('delete_asset')
    @assets_ns.marshal_with(success_model, code=200, description='Successfully deleted asset')
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @jwt_required()
    def delete(self, asset_id):
        """Delete a specific asset by ID"""
        error = check_permission("can_delete_asset")
        if error:
            return error
        asset = db.session.query(FixedAsset).filter_by(id=asset_id).first()
        if not asset:
            return {"error": "Asset not found"}, 404
        db.session.delete(asset)
        db.session.commit()
        return {"message": f"Asset {asset_id} deleted successfully"}, 200

    