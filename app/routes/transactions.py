from flask import Blueprint, request, jsonify, send_file, abort
from flask_restx import Resource
from marshmallow import ValidationError
from datetime import datetime, date
from sqlalchemy import and_, or_
from .. import db
import os
import uuid
import json
from werkzeug.utils import secure_filename
from flask import request, current_app
from flask_restx import Resource, reqparse
from ..models import Transaction, AssetTransaction, Warehouse, FixedAsset, Branch
from ..schemas import (
    TransactionSchema, TransactionCreateSchema, 
    AssetTransactionSchema, AssetTransactionCreateSchema
)
from flask_jwt_extended import jwt_required
from ..utils import check_permission
from ..swagger import transactions_ns, asset_transactions_ns, add_standard_responses, api
from ..swagger_models import (
    transaction_model, transaction_input_model, transaction_create_model,
    asset_transaction_model, asset_transaction_input_model,
    pagination_model, error_model, success_model
)
from werkzeug.datastructures import FileStorage

bp = Blueprint("transactions", __name__, url_prefix="/transactions")

# Initialize schemas
transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)
transaction_create_schema = TransactionCreateSchema()
asset_transaction_schema = AssetTransactionSchema()
asset_transactions_schema = AssetTransactionSchema(many=True)
asset_transaction_create_schema = AssetTransactionCreateSchema()
file_upload_parser = reqparse.RequestParser()
file_upload_parser.add_argument('attached_file', 
                               location='files',
                               type=FileStorage,
                               required=False,
                               help='File attachment')
file_upload_parser.add_argument('data', 
                               location='form',
                               type=str,
                               required=False,
                               help='''Transaction data as JSON string. Example:
{
  "date": "2025-09-24",
  "description": "string", 
  "reference_number": "string",
  "warehouse_id": 0,
  "asset_transactions": [
    {
      "asset_id": 0,
      "quantity": 1,
      "amount": 0,
      "transaction_type": true
    }
  ]
}''')



@transactions_ns.route("/")
class TransactionList(Resource):
    @transactions_ns.doc('list_transactions', security='Bearer Auth')
    @transactions_ns.marshal_with(pagination_model)
    @transactions_ns.param('page', 'Page number', type=int, default=1)
    @transactions_ns.param('per_page', 'Items per page', type=int, default=10)
    @transactions_ns.param('branch_id', 'Filter by branch ID', type=int)
    @transactions_ns.param('warehouse_id', 'Filter by warehouse ID', type=int)
    @transactions_ns.param('date_from', 'Filter transactions from date (YYYY-MM-DD)', type=str)
    @transactions_ns.param('date_to', 'Filter transactions to date (YYYY-MM-DD)', type=str)
    @transactions_ns.param('search', 'Search in description or reference number', type=str)
    @jwt_required()
    def get(self):
        """Get all transactions with pagination and filtering"""
        error = check_permission("can_read_asset")  # Using asset permission for now
        if error:
            return error

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        branch_id = request.args.get("branch_id", type=int)
        warehouse_id = request.args.get("warehouse_id", type=int)
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        search = request.args.get("search", "")

        # Build query with joins
        query = Transaction.query.join(Warehouse)

        # Apply filters
        if branch_id:
            query = query.filter(Warehouse.branch_id == branch_id)
        
        if warehouse_id:
            query = query.filter(Transaction.warehouse_id == warehouse_id)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Transaction.date >= date_from_obj)
            except ValueError:
                return {"error": "Invalid date_from format. Use YYYY-MM-DD"}, 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(Transaction.date <= date_to_obj)
            except ValueError:
                return {"error": "Invalid date_to format. Use YYYY-MM-DD"}, 400
        
        if search:
            query = query.filter(or_(
                Transaction.description.contains(search),
                Transaction.reference_number.contains(search)
            ))

        # Order by date descending (newest first)
        query = query.order_by(Transaction.date.desc(), Transaction.created_at.desc())

        paginated = query.paginate(page=page, per_page=per_page)
        return {
            "items": transactions_schema.dump(paginated.items),
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages
        }
    

    @transactions_ns.doc('create_transaction', security='Bearer Auth')
    #@transactions_ns.expect(transaction_create_model)
    @transactions_ns.expect(file_upload_parser)
    @transactions_ns.marshal_with(transaction_model, code=201)
    @jwt_required()
    def post(self):
        """Create a new transaction with asset transactions"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        try:
            print("Starting transaction creation process")
            
            # Handle file upload
            attached_file_name = None
            
            # Check if request has files
            if 'attached_file' in request.files:
                file = request.files['attached_file']
                
                if file and file.filename and file.filename.strip():
                    try:
                        print(f"Processing file: {file.filename}")
                        # Generate unique filename
                        file_extension = os.path.splitext(secure_filename(file.filename))[1]
                        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
                        
                        # Create upload directory if it doesn't exist
                        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                        os.makedirs(upload_folder, exist_ok=True)
                        
                        # Save file
                        file_path = os.path.join(upload_folder, unique_filename)
                        file.save(file_path)
                        attached_file_name = unique_filename
                        print(f"File saved as: {unique_filename}")
                        
                    except Exception as e:
                        print(f"File upload error: {str(e)}")
                        return {"error": f"File upload failed: {str(e)}"}, 400
            
            # Handle JSON data
            try:
                # For multipart requests, JSON data might be in a form field
                if request.content_type and 'multipart/form-data' in request.content_type:
                    # Try to get JSON from form data
                    json_str = request.form.get('data')
                    if json_str:
                        json_data = json.loads(json_str)
                    else:
                        return {"error": "No transaction data provided in multipart request"}, 400
                else:
                    # Regular JSON request
                    json_data = request.get_json()
                    if not json_data:
                        return {"error": "No JSON data provided"}, 400
                
                data = transaction_create_schema.load(json_data)
                print("Transaction data validated successfully")
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {str(e)}")
                return {"error": f"Invalid JSON format: {str(e)}"}, 400
            except ValidationError as e:
                print(f"Schema validation error: {str(e)}")
                return {"error": f"Data validation failed: {str(e)}"}, 400
            except Exception as e:
                print(f"Data processing error: {str(e)}")
                return {"error": f"Data processing failed: {str(e)}"}, 400
            
            # Get warehouse to determine branch
            warehouse = db.session.get(Warehouse, data['warehouse_id'])
            if not warehouse:
                return {"error": "Warehouse not found"}, 404
            
            # Generate custom_id
            custom_id = Transaction.generate_custom_id(warehouse.branch_id)
            
            # Create transaction
            transaction_data = {
                'custom_id': custom_id,
                'date': data['date'],
                'description': data.get('description'),
                'reference_number': data.get('reference_number'),
                'warehouse_id': data['warehouse_id'],
                'attached_file': attached_file_name  # Store the unique filename
            }
            
            new_transaction = Transaction(**transaction_data)
            db.session.add(new_transaction)
            db.session.flush()  # Get the transaction ID
            
            # Create asset transactions and update asset quantities
            asset_transactions = []
            for asset_trans_data in data['asset_transactions']:
                # Get the asset
                asset = db.session.get(FixedAsset, asset_trans_data['asset_id'])
                if not asset:
                    db.session.rollback()
                    return {"error": f"Asset {asset_trans_data['asset_id']} not found"}, 404
                
                # Check if OUT transaction has enough quantity
                if not asset_trans_data['transaction_type']:  # OUT transaction
                    if asset.quantity < asset_trans_data['quantity']:
                        db.session.rollback()
                        return {
                            "error": f"Insufficient quantity for asset {asset.name_en}. "
                                f"Available: {asset.quantity}, Requested: {asset_trans_data['quantity']}"
                        }, 400
                
                # Update asset quantity
                if asset_trans_data['transaction_type']:  # IN transaction
                    asset.quantity += asset_trans_data['quantity']
                else:  # OUT transaction
                    asset.quantity -= asset_trans_data['quantity']
                
                # Create asset transaction
                asset_trans = AssetTransaction(
                    transaction_id=new_transaction.id,
                    asset_id=asset_trans_data['asset_id'],
                    quantity=asset_trans_data['quantity'],
                    amount=asset_trans_data.get('amount'),
                    transaction_type=asset_trans_data['transaction_type']
                )
                # Calculate total_value automatically via the model's __init__
                asset_transactions.append(asset_trans)
            
            db.session.add_all(asset_transactions)
            db.session.commit()
            
            return transaction_schema.dump(new_transaction), 201
            
        except Exception as e:
            db.session.rollback()
            print(f"Unexpected error: {str(e)}")
            return {"error": str(e)}, 500


@transactions_ns.route("/<int:transaction_id>")
class TransactionResource(Resource):
    @transactions_ns.doc('get_transaction', security='Bearer Auth')
    @transactions_ns.marshal_with(transaction_model)
    @jwt_required()
    def get(self, transaction_id):
        """Get a specific transaction"""
        error = check_permission("can_read_asset")
        if error:
            return error

        transaction = db.session.get(Transaction, transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404
        return transaction_schema.dump(transaction)

    # ...existing code...


    @transactions_ns.doc('update_transaction', security='Bearer Auth')
    @transactions_ns.expect(transaction_input_model)
    @transactions_ns.marshal_with(transaction_model)
    @jwt_required()
    def put(self, transaction_id):
        """Update a transaction"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        transaction = db.session.get(Transaction, transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404

        try:
            data = transaction_schema.load(request.get_json(), partial=True)
            
            # Don't allow updating custom_id
            if 'custom_id' in data:
                del data['custom_id']
            
            for key, value in data.items():
                setattr(transaction, key, value)
            
            db.session.commit()
            return transaction_schema.dump(transaction)
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @transactions_ns.doc('delete_transaction', security='Bearer Auth')
    @transactions_ns.marshal_with(success_model)
    @jwt_required()
    def delete(self, transaction_id):
        """Delete a transaction"""
        error = check_permission("can_delete_asset")
        if error:
            return error

        transaction = db.session.get(Transaction, transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404

        try:
            # Before deleting transaction, reverse all asset quantity changes
            for asset_trans in transaction.asset_transactions:
                asset = db.session.get(FixedAsset, asset_trans.asset_id)
                if asset:
                    if asset_trans.transaction_type:  # Was IN transaction
                        asset.quantity -= asset_trans.quantity  # Remove the added quantity
                    else:  # Was OUT transaction
                        asset.quantity += asset_trans.quantity  # Add back the removed quantity
            
            db.session.delete(transaction)  # Cascade will delete asset_transactions
            db.session.commit()
            return {"message": f"Transaction {transaction_id} deleted successfully"}
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


@transactions_ns.route("/<int:transaction_id>/assets")
class TransactionAssetsList(Resource):
    @transactions_ns.doc('get_transaction_assets', security='Bearer Auth')
    @transactions_ns.marshal_with(pagination_model)
    @transactions_ns.param('page', 'Page number', type=int, default=1)
    @transactions_ns.param('per_page', 'Items per page', type=int, default=10)
    @transactions_ns.param('transaction_type', 'Filter by transaction type (true for IN, false for OUT)', type=bool)
    @jwt_required()
    def get(self, transaction_id):
        """Get all asset transactions for a specific transaction"""
        error = check_permission("can_read_asset")
        if error:
            return error

        # Check if transaction exists
        transaction = db.session.get(Transaction, transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        transaction_type = request.args.get("transaction_type", type=bool)

        query = AssetTransaction.query.filter_by(transaction_id=transaction_id)
        
        if transaction_type is not None:
            query = query.filter_by(transaction_type=transaction_type)

        paginated = query.paginate(page=page, per_page=per_page)
        return {
            "items": asset_transactions_schema.dump(paginated.items),
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages
        }

    @transactions_ns.doc('add_asset_to_transaction', security='Bearer Auth')
    @transactions_ns.expect(asset_transaction_input_model)
    @transactions_ns.marshal_with(asset_transaction_model, code=201)
    @jwt_required()
    def post(self, transaction_id):
        """Add an asset transaction to an existing transaction"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        # Check if transaction exists
        transaction = db.session.get(Transaction, transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404

        try:
            data = asset_transaction_create_schema.load(request.get_json())
            
            # Get the asset and check availability for OUT transactions
            asset = db.session.get(FixedAsset, data['asset_id'])
            if not asset:
                return {"error": "Asset not found"}, 404
            
            # Check if OUT transaction has enough quantity
            if not data['transaction_type']:  # OUT transaction
                if asset.quantity < data['quantity']:
                    return {
                        "error": f"Insufficient quantity for asset {asset.name_en}. "
                               f"Available: {asset.quantity}, Requested: {data['quantity']}"
                    }, 400
            
            # Update asset quantity
            if data['transaction_type']:  # IN transaction
                asset.quantity += data['quantity']
            else:  # OUT transaction
                asset.quantity -= data['quantity']
            
            asset_transaction = AssetTransaction(
                transaction_id=transaction_id,
                asset_id=data['asset_id'],
                quantity=data['quantity'],
                amount=data.get('amount'),
                transaction_type=data['transaction_type']
            )
            
            db.session.add(asset_transaction)
            db.session.commit()
            
            return asset_transaction_schema.dump(asset_transaction), 201
            
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


@asset_transactions_ns.route("/<int:asset_transaction_id>")
class AssetTransactionResource(Resource):
    @asset_transactions_ns.doc('get_asset_transaction', security='Bearer Auth')
    @asset_transactions_ns.marshal_with(asset_transaction_model)
    @jwt_required()
    def get(self, asset_transaction_id):
        """Get a specific asset transaction"""
        error = check_permission("can_read_asset")
        if error:
            return error

        asset_transaction = db.session.get(AssetTransaction, asset_transaction_id)
        if not asset_transaction:
            return {"error": "Asset transaction not found"}, 404
        
        return asset_transaction_schema.dump(asset_transaction)

    @asset_transactions_ns.doc('update_asset_transaction', security='Bearer Auth')
    @asset_transactions_ns.expect(asset_transaction_input_model)
    @asset_transactions_ns.marshal_with(asset_transaction_model)
    @jwt_required()
    def put(self, asset_transaction_id):
        """Update an asset transaction"""
        error = check_permission("can_edit_asset")
        if error:
            return error

        asset_transaction = db.session.get(AssetTransaction, asset_transaction_id)
        if not asset_transaction:
            return {"error": "Asset transaction not found"}, 404

        try:
            data = asset_transaction_create_schema.load(request.get_json(), partial=True)
            
            # Get current values before update
            old_quantity = asset_transaction.quantity
            old_transaction_type = asset_transaction.transaction_type
            old_asset_id = asset_transaction.asset_id
            
            # Get new values
            new_quantity = data.get('quantity', old_quantity)
            new_transaction_type = data.get('transaction_type', old_transaction_type)
            new_asset_id = data.get('asset_id', old_asset_id)
            
            # If asset_id changed, we need to handle both assets
            if new_asset_id != old_asset_id:
                # Reverse the effect on the old asset
                old_asset = db.session.get(FixedAsset, old_asset_id)
                if old_asset:
                    if old_transaction_type:  # Was IN transaction
                        old_asset.quantity -= old_quantity  # Remove the added quantity
                    else:  # Was OUT transaction
                        old_asset.quantity += old_quantity  # Add back the removed quantity
                
                # Get the new asset
                new_asset = db.session.get(FixedAsset, new_asset_id)
                if not new_asset:
                    return {"error": "New asset not found"}, 404
                
                # Check availability for new asset if OUT transaction
                if not new_transaction_type:  # OUT transaction
                    if new_asset.quantity < new_quantity:
                        return {
                            "error": f"Insufficient quantity for asset {new_asset.name_en}. "
                                   f"Available: {new_asset.quantity}, Requested: {new_quantity}"
                        }, 400
                
                # Apply effect to new asset
                if new_transaction_type:  # IN transaction
                    new_asset.quantity += new_quantity
                else:  # OUT transaction
                    new_asset.quantity -= new_quantity
            
            else:
                # Same asset, but quantity or type might have changed
                asset = db.session.get(FixedAsset, old_asset_id)
                if asset:
                    # Reverse the old effect
                    if old_transaction_type:  # Was IN transaction
                        asset.quantity -= old_quantity
                    else:  # Was OUT transaction
                        asset.quantity += old_quantity
                    
                    # Check availability for OUT transaction
                    if not new_transaction_type:  # OUT transaction
                        if asset.quantity < new_quantity:
                            # Restore the old effect before returning error
                            if old_transaction_type:
                                asset.quantity += old_quantity
                            else:
                                asset.quantity -= old_quantity
                            return {
                                "error": f"Insufficient quantity for asset {asset.name_en}. "
                                       f"Available: {asset.quantity}, Requested: {new_quantity}"
                            }, 400
                    
                    # Apply the new effect
                    if new_transaction_type:  # IN transaction
                        asset.quantity += new_quantity
                    else:  # OUT transaction
                        asset.quantity -= new_quantity
            
            # Update asset transaction fields
            for key, value in data.items():
                setattr(asset_transaction, key, value)
            
            # Recalculate total_value if quantity or amount changed
            asset_transaction.calculate_total_value()
            
            db.session.commit()
            return asset_transaction_schema.dump(asset_transaction)
            
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @asset_transactions_ns.doc('delete_asset_transaction', security='Bearer Auth')
    @asset_transactions_ns.marshal_with(success_model)
    @jwt_required()
    def delete(self, asset_transaction_id):
        """Delete an asset transaction"""
        error = check_permission("can_delete_asset")
        if error:
            return error

        asset_transaction = db.session.get(AssetTransaction, asset_transaction_id)
        if not asset_transaction:
            return {"error": "Asset transaction not found"}, 404

        try:
            # Before deleting, reverse the quantity effect on the asset
            asset = db.session.get(FixedAsset, asset_transaction.asset_id)
            if asset:
                if asset_transaction.transaction_type:  # Was IN transaction
                    asset.quantity -= asset_transaction.quantity  # Remove the added quantity
                else:  # Was OUT transaction
                    asset.quantity += asset_transaction.quantity  # Add back the removed quantity
            
            db.session.delete(asset_transaction)
            db.session.commit()
            return {"message": f"Asset transaction {asset_transaction_id} deleted successfully"}
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


@transactions_ns.route("/summary")
class TransactionSummary(Resource):
    @transactions_ns.doc('get_transaction_summary', security='Bearer Auth')
    @transactions_ns.param('branch_id', 'Filter by branch ID', type=int)
    @transactions_ns.param('warehouse_id', 'Filter by warehouse ID', type=int)
    @transactions_ns.param('date_from', 'Summary from date (YYYY-MM-DD)', type=str)
    @transactions_ns.param('date_to', 'Summary to date (YYYY-MM-DD)', type=str)
    @jwt_required()
    def get(self):
        """Get transaction summary statistics"""
        error = check_permission("can_read_asset")
        if error:
            return error

        branch_id = request.args.get("branch_id", type=int)
        warehouse_id = request.args.get("warehouse_id", type=int)
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        # Build base query
        transaction_query = Transaction.query.join(Warehouse)
        asset_transaction_query = AssetTransaction.query.join(Transaction).join(Warehouse)

        # Apply filters
        if branch_id:
            transaction_query = transaction_query.filter(Warehouse.branch_id == branch_id)
            asset_transaction_query = asset_transaction_query.filter(Warehouse.branch_id == branch_id)
        
        if warehouse_id:
            transaction_query = transaction_query.filter(Transaction.warehouse_id == warehouse_id)
            asset_transaction_query = asset_transaction_query.filter(Transaction.warehouse_id == warehouse_id)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
                transaction_query = transaction_query.filter(Transaction.date >= date_from_obj)
                asset_transaction_query = asset_transaction_query.filter(Transaction.date >= date_from_obj)
            except ValueError:
                return {"error": "Invalid date_from format. Use YYYY-MM-DD"}, 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                transaction_query = transaction_query.filter(Transaction.date <= date_to_obj)
                asset_transaction_query = asset_transaction_query.filter(Transaction.date <= date_to_obj)
            except ValueError:
                return {"error": "Invalid date_to format. Use YYYY-MM-DD"}, 400

        # Calculate statistics
        total_transactions = transaction_query.count()
        total_in_transactions = asset_transaction_query.filter(AssetTransaction.transaction_type == True).count()
        total_out_transactions = asset_transaction_query.filter(AssetTransaction.transaction_type == False).count()
        
        # Calculate total values
        from sqlalchemy import func
        total_in_value = asset_transaction_query.filter(
            AssetTransaction.transaction_type == True,
            AssetTransaction.total_value.isnot(None)
        ).with_entities(func.sum(AssetTransaction.total_value)).scalar() or 0
        
        total_out_value = asset_transaction_query.filter(
            AssetTransaction.transaction_type == False,
            AssetTransaction.total_value.isnot(None)
        ).with_entities(func.sum(AssetTransaction.total_value)).scalar() or 0

        return {
            "total_transactions": total_transactions,
            "total_in_transactions": total_in_transactions,
            "total_out_transactions": total_out_transactions,
            "total_in_value": float(total_in_value),
            "total_out_value": float(total_out_value),
            "net_value": float(total_in_value - total_out_value)
        }
    

# New Resource for downloading transaction file
@transactions_ns.route('/<int:transaction_id>/download')
class TransactionDownloadResource(Resource):
    @transactions_ns.doc('download_transaction_file', security='Bearer Auth')
    @jwt_required()
    def get(self, transaction_id):
        """Download the attached file for a transaction"""
        error = check_permission("can_read_asset")
        if error:
            return error

        transaction = db.session.get(Transaction, transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}, 404

        if not transaction.attached_file:
            return {"error": "No file attached to this transaction."}, 404

        file_path = transaction.attached_file
        # If file path is not absolute, assume uploads folder
        if not os.path.isabs(file_path):
            file_path = os.path.join(current_app.root_path, '..', 'uploads', file_path)

        if not os.path.exists(file_path):
            return {"error": "File not found."}, 404

        return send_file(file_path, as_attachment=True)