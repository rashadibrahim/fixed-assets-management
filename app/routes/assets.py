from flask import Blueprint, request, jsonify
from flask_restx import Resource
from marshmallow import ValidationError
from .. import db
from ..models import FixedAsset, Category
from ..schemas import FixedAssetSchema, CategorySchema
from flask_jwt_extended import jwt_required
from ..utils import check_permission, generate_barcode, generate_unique_product_code
from ..swagger import assets_ns, categories_ns, add_standard_responses, api
from ..swagger_models import (
    asset_model, asset_input_model, category_model, category_input_model,
    pagination_model, error_model, success_model, barcode_model
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

        try:
            data = asset_schema.load(request.get_json())
            new_asset = FixedAsset(**data)
            db.session.add(new_asset)
            db.session.commit()
            return asset_schema.dump(new_asset), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400


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





# @assets_ns.route("/<int:asset_id>/files")
# @assets_ns.param('asset_id', 'The asset identifier')
# class AssetFiles(Resource):
#     @assets_ns.doc('get_asset_files', security='Bearer Auth')
#     @assets_ns.marshal_with(pagination_model, code=200, description='Successfully retrieved files')
#     @assets_ns.response(401, 'Unauthorized', error_model)
#     @assets_ns.response(403, 'Forbidden', error_model)
#     @assets_ns.response(404, 'Asset not found', error_model)
#     @assets_ns.param('page', 'Page number for pagination', type='integer', default=1)
#     @assets_ns.param('per_page', 'Number of items per page', type='integer', default=10)
#     @jwt_required()
#     def get(self, asset_id):
#         """Get all files attached to a specific asset"""
#         error = check_permission("can_read_asset")
#         if error:
#             return error
            
#         # Check if asset exists
#         asset = db.session.query(FixedAsset).filter_by(id=asset_id).first()
#         if not asset:
#             return {"error": "Asset not found"}, 404
            
#         # Pagination
#         page = request.args.get("page", 1, type=int)
#         per_page = request.args.get("per_page", 10, type=int)
        
#         # Query files
#         query = db.session.query(AttachedFile).filter_by(asset_id=asset_id)
#         paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
#         # Return paginated files
#         file_schema = AttachedFileSchema(many=True)
#         return {
#             "items": file_schema.dump(paginated.items),
#             "total": paginated.total,
#             "page": paginated.page,
#             "pages": paginated.pages
#         }
    
   

# # First, create a parser for file upload with both file and comment fields
# file_upload_parser = api.parser()
# file_upload_parser.add_argument('file', type='file', location='files', required=True, 
#     help='The file to upload')
# file_upload_parser.add_argument('comment', type=str, location='form', required=True, 
#     help='Comment describing the file')

# @assets_ns.route("/<int:asset_id>/files")
# @assets_ns.param('asset_id', 'The asset identifier')
# class AssetFiles(Resource):
#     # ...existing get method...

#     @assets_ns.doc('upload_asset_file', 
#         description='Upload a file attachment for a specific asset',
#         security='Bearer Auth')
#     @assets_ns.expect(file_upload_parser)
#     @assets_ns.marshal_with(file_upload_response_model, code=201, 
#         description='Successfully uploaded file')
#     @assets_ns.response(400, 'Bad Request - No file uploaded or invalid format', error_model)
#     @assets_ns.response(401, 'Unauthorized - Missing or invalid token', error_model)
#     @assets_ns.response(403, 'Forbidden - Insufficient permissions', error_model)
#     @assets_ns.response(404, 'Asset not found', error_model)
#     @assets_ns.response(500, 'Server error while saving file', error_model)
#     @jwt_required()
#     def post(self, asset_id):
#         """
#         Upload a file attachment for a specific asset
        
#         Use multipart/form-data to upload the file along with a comment.
#         Supported file types: PDF, DOC, DOCX, XLS, XLSX, JPG, PNG
#         Maximum file size: 10MB
#         """
#         """Upload a file attachment for a specific asset"""
#         error = check_permission("can_edit_asset")
#         if error:
#             return error
            
#         # Check if asset exists
#         asset = db.session.query(FixedAsset).filter_by(id=asset_id).first()
#         if not asset:
#             return {"error": "Asset not found"}, 404
            
#         # Check if file was uploaded
#         if 'file' not in request.files:
#             return {"error": "No file part in the request"}, 400
            
#         file = request.files['file']
#         if file.filename == '':
#             return {"error": "No file selected"}, 400
            
#         # Save the file
#         filename = save_upload(file)
#         if not filename:
#             return {"error": "Failed to save file"}, 500
            
#         # Create file record in database
#         file_record = AttachedFile(asset_id=asset_id, file_path=filename, comment=request.form.get('comment', ''))
#         db.session.add(file_record)
#         db.session.commit()
        
#         # Return the file record
#         file_schema = AttachedFileSchema()
#         return file_schema.dump(file_record), 201


# @assets_ns.route("/files/<int:file_id>")
# # @assets_ns.param('asset_id', 'The asset identifier')
# @assets_ns.param('file_id', 'The file identifier')
# class AssetFileResource(Resource):
#     @assets_ns.doc('download_asset_file', security='Bearer Auth', description='Download a file attachment from a specific asset')
#     @assets_ns.produces(['application/octet-stream'])
#     @assets_ns.response(200, 'File download successful')
#     @assets_ns.response(401, 'Unauthorized', error_model)
#     @assets_ns.response(403, 'Forbidden', error_model)
#     @assets_ns.response(404, 'File not found', error_model)
#     @assets_ns.response(500, 'Server error', error_model)
#     @jwt_required()
#     def get(self, file_id):
#         """Download a file attachment from a specific asset"""
#         error = check_permission("can_read_asset")
#         if error:
#             return error
            
#         # Check if file exists and belongs to the specified asset
#         file_record = db.session.query(AttachedFile).filter_by(id=file_id).first()
#         # if not file_record:
#         #     return {"error": "File not found or does not belong to this asset"}, 404
            
#         # # Get the file path
#         file_path = file_record.file_path
#         upload_folder = current_app.config["UPLOAD_FOLDER"]
        
#         # # Check if file exists
#         full_path = os.path.join(upload_folder, file_path)
#         if not os.path.exists(full_path):
#             return {"error": "File not found on server"}, 404
        
#         # Return the file as an attachment
#         return send_file(
#             full_path,
#             as_attachment=True,
#             download_name=os.path.basename(file_record.file_path)  # original filename
#         )
        
    
#     @assets_ns.doc('delete_asset_file', security='Bearer Auth')
#     @assets_ns.marshal_with(success_model, code=200, description='Successfully deleted file')
#     @assets_ns.response(401, 'Unauthorized', error_model)
#     @assets_ns.response(403, 'Forbidden', error_model)
#     @assets_ns.response(404, 'File not found', error_model)
#     @jwt_required()
#     def delete(self, file_id):
#         """Delete a file attachment from a specific asset"""
#         error = check_permission("can_edit_asset")
#         if error:
#             return error
            
#         # Check if file exists and belongs to the specified asset
#         file_record = db.session.query(AttachedFile).filter_by(id=file_id).first()
#         if not file_record:
#             return {"error": "File not found"}, 404
            
#         # Delete the physical file from storage
#         file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_record.file_path)
#         if os.path.exists(file_path):
#             try:
#                 os.remove(file_path)
#             except Exception as e:
#                 # Log the error but continue with database deletion
#                 print(f"Error deleting file {file_path}: {str(e)}")
        
#         # Delete the file record from database
#         db.session.delete(file_record)
#         db.session.commit()
        
#         return {"message": f"File {file_id} deleted successfully"}, 200

