from flask import Blueprint, request, jsonify, send_file
from flask_restx import Resource
from marshmallow import ValidationError
from werkzeug.utils import secure_filename
from .. import db
from ..models import FixedAsset, AttachedFile
from ..schemas import FixedAssetSchema, AttachedFileSchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission, generate_barcode, generate_unique_product_code, save_upload
from ..swagger import assets_ns, add_standard_responses, api
from ..swagger_models import (
    asset_model, asset_input_model, pagination_model, 
    error_model, success_model, barcode_model, file_upload_response_model
)
import os
from flask import current_app, send_from_directory

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


@assets_ns.route("/<int:asset_id>/files")
@assets_ns.param('asset_id', 'The asset identifier')
class AssetFiles(Resource):
    @assets_ns.doc('get_asset_files', security='Bearer Auth')
    @assets_ns.marshal_with(pagination_model, code=200, description='Successfully retrieved files')
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @assets_ns.param('page', 'Page number for pagination', type='integer', default=1)
    @assets_ns.param('per_page', 'Number of items per page', type='integer', default=10)
    @jwt_required()
    def get(self, asset_id):
        """Get all files attached to a specific asset"""
        error = check_permission("can_read_asset")
        if error:
            return error
            
        # Check if asset exists
        asset = db.session.query(FixedAsset).filter_by(id=asset_id).first()
        if not asset:
            return {"error": "Asset not found"}, 404
            
        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        
        # Query files
        query = db.session.query(AttachedFile).filter_by(asset_id=asset_id)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Return paginated files
        file_schema = AttachedFileSchema(many=True)
        return {
            "items": file_schema.dump(paginated.items),
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages
        }
    
    @assets_ns.doc('upload_asset_file', security='Bearer Auth')
    @assets_ns.marshal_with(file_upload_response_model, code=201, description='Successfully uploaded file')
    @assets_ns.response(400, 'Bad Request', error_model)
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'Asset not found', error_model)
    @assets_ns.expect(api.parser().add_argument('file', location='files', type='file', required=True, help='File to upload'))
    @jwt_required()
    def post(self, asset_id):
        """Upload a file attachment for a specific asset"""
        error = check_permission("can_edit_asset")
        if error:
            return error
            
        # Check if asset exists
        asset = db.session.query(FixedAsset).filter_by(id=asset_id).first()
        if not asset:
            return {"error": "Asset not found"}, 404
            
        # Check if file was uploaded
        if 'file' not in request.files:
            return {"error": "No file part in the request"}, 400
            
        file = request.files['file']
        if file.filename == '':
            return {"error": "No file selected"}, 400
            
        # Save the file
        filename = save_upload(file)
        if not filename:
            return {"error": "Failed to save file"}, 500
            
        # Create file record in database
        file_record = AttachedFile(asset_id=asset_id, file_path=filename)
        db.session.add(file_record)
        db.session.commit()
        
        # Return the file record
        file_schema = AttachedFileSchema()
        return file_schema.dump(file_record), 201


@assets_ns.route("/files/<int:file_id>")
# @assets_ns.param('asset_id', 'The asset identifier')
@assets_ns.param('file_id', 'The file identifier')
class AssetFileResource(Resource):
    @assets_ns.doc('download_asset_file', security='Bearer Auth', description='Download a file attachment from a specific asset')
    @assets_ns.produces(['application/octet-stream'])
    @assets_ns.response(200, 'File download successful')
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'File not found', error_model)
    @assets_ns.response(500, 'Server error', error_model)
    @jwt_required()
    def get(self, file_id):
        """Download a file attachment from a specific asset"""
        error = check_permission("can_read_asset")
        if error:
            return error
            
        # Check if file exists and belongs to the specified asset
        file_record = db.session.query(AttachedFile).filter_by(id=file_id).first()
        # if not file_record:
        #     return {"error": "File not found or does not belong to this asset"}, 404
            
        # # Get the file path
        file_path = file_record.file_path
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        
        # # Check if file exists
        full_path = os.path.join(upload_folder, file_path)
        if not os.path.exists(full_path):
            return {"error": "File not found on server"}, 404
        
        # Return the file as an attachment
        return send_file(
            full_path,
            as_attachment=True,
            download_name=os.path.basename(file_record.file_path)  # original filename
        )
        
    
    # @assets_ns.doc('download_asset_file', security='Bearer Auth', description='Download a file attachment from a specific asset')
    # @assets_ns.produces(['application/octet-stream'])
    # @assets_ns.response(200, 'File download successful')
    # @assets_ns.response(401, 'Unauthorized', error_model)
    # @assets_ns.response(403, 'Forbidden', error_model)
    # @assets_ns.response(404, 'File not found', error_model)
    # @assets_ns.response(500, 'Server error', error_model)
    # #@jwt_required()
    # def get(self, asset_id, file_id):
    #     """Download a file attachment from a specific asset"""
    #     # error = check_permission("can_read_asset")
    #     # if error:
    #     #     return error
            
    #     # Check if file exists and belongs to the specified asset
    #     file_record = db.session.query(AttachedFile).filter_by(id=file_id, asset_id=asset_id).first()
    #     if not file_record:
    #         return {"error": "File not found or does not belong to this asset"}, 404
            
    #     # Get the file path
    #     import os
    #     from flask import current_app, send_from_directory
        
    #     file_path = file_record.file_path
    #     upload_folder = current_app.config["UPLOAD_FOLDER"]
        
    #     # Check if file exists
    #     full_path = os.path.join(upload_folder, file_path)
    #     if not os.path.exists(full_path):
    #         return {"error": "File not found on server"}, 404
        
    #     # Get original filename if available, otherwise use the stored filename
    #     filename = os.path.basename(file_path)
        
    #     # Return the file as an attachment
    #     return send_from_directory(
    #         directory=upload_folder,
    #         path=file_path,
    #         as_attachment=True,
    #         download_name=filename
    #     )
    @assets_ns.doc('delete_asset_file', security='Bearer Auth')
    @assets_ns.marshal_with(success_model, code=200, description='Successfully deleted file')
    @assets_ns.response(401, 'Unauthorized', error_model)
    @assets_ns.response(403, 'Forbidden', error_model)
    @assets_ns.response(404, 'File not found', error_model)
    @jwt_required()
    def delete(self, asset_id, file_id):
        """Delete a file attachment from a specific asset"""
        error = check_permission("can_edit_asset")
        if error:
            return error
            
        # Check if file exists and belongs to the specified asset
        file_record = db.session.query(AttachedFile).filter_by(id=file_id, asset_id=asset_id).first()
        if not file_record:
            return {"error": "File not found or does not belong to this asset"}, 404
            
        # Delete the physical file from storage
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_record.file_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # Log the error but continue with database deletion
                print(f"Error deleting file {file_path}: {str(e)}")
        
        # Delete the file record from database
        db.session.delete(file_record)
        db.session.commit()
        
        return {"message": f"File {file_id} deleted successfully from asset {asset_id}"}, 200


@assets_ns.route("/files/<int:file_id>")
@assets_ns.param('file_id', 'The file identifier')
class FileResource(Resource):
    @assets_ns.doc('get_file_by_id', description='Download a file attachment by ID only')
    @assets_ns.produces(['application/octet-stream'])
    @assets_ns.response(200, 'File download successful')
    @assets_ns.response(404, 'File not found', error_model)
    @assets_ns.response(500, 'Server error', error_model)
    @jwt_required()
    def get(self, file_id):
        """Download a file attachment by ID only"""
        error = check_permission("can_read_asset")
        if error:
            return error
        
        # Check if file exists
        file_record = db.session.query(AttachedFile).filter_by(id=file_id).first()
        if not file_record:
            return {"error": "File not found"}, 404
            
        # Get the file path
        file_path = file_record.file_path
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        
        # Check if file exists
        full_path = os.path.join(upload_folder, file_path)
        if not os.path.exists(full_path):
            return {"error": "File not found on server"}, 404
        
        # Get original filename if available, otherwise use the stored filename
        filename = os.path.basename(file_path)
        
        # Return the file as an attachment
        return send_from_directory(
            directory=upload_folder,
            path=file_path,
            as_attachment=True,
            download_name=filename
        )


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

    