from marshmallow import Schema, fields, validates, ValidationError, post_load, INCLUDE
from decimal import Decimal
from .models import db, Category, Branch, Warehouse, FixedAsset, Transaction


class BranchSchema(Schema):
    id = fields.Int(dump_only=True)
    name_ar = fields.Str(required=True)
    name_en = fields.Str(required=True)
    address_ar = fields.Str(required=True)
    address_en = fields.Str(required=True)


class WarehouseSchema(Schema):
    id = fields.Int(dump_only=True)
    branch_id = fields.Int()
    name_ar = fields.Str(required=True)
    name_en = fields.Str(required=True)
    address_ar = fields.Str()
    address_en = fields.Str()
    
    @validates("branch_id")
    def validate_branch(self, value, **kwargs):
        branch = db.session.get(Branch, value)
        if branch is None:
            raise ValidationError("Invalid branch_id: branch does not exist.")


class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    category = fields.Str(required=True)
    category_ar = fields.Str(required=False, allow_none=True)
    subcategory = fields.Str(required=False, allow_none=True)
    subcategory_ar = fields.Str(required=False, allow_none=True)

class FixedAssetSchema(Schema):
    id = fields.Int(dump_only=True)
    name_ar = fields.Str(required=True)
    name_en = fields.Str(required=True)
    quantity = fields.Int()
    product_code = fields.Str()
    category_id = fields.Int(required=True)
    is_active = fields.Bool(required=True)

    @validates("category_id")
    def validate_category(self, value, **kwargs):
        category = db.session.get(Category, value)
        if category is None:
            raise ValidationError("Invalid category_id: category does not exist.")

class TransactionSchema(Schema):
    id = fields.Int(dump_only=True)
    custom_id = fields.Str(dump_only=True)  # Generated automatically
    date = fields.Date(required=True)
    description = fields.Str(allow_none=True)
    reference_number = fields.Str(allow_none=True)
    warehouse_id = fields.Int(required=True)
    user_id = fields.Int(dump_only=True)  # NEW: Show which user created the transaction
    attached_file = fields.Str(allow_none=True)
    transaction_type = fields.Bool(required=True)  # True for IN, False for OUT
    created_at = fields.DateTime(dump_only=True)
    
    # Nested relationships for response
    warehouse = fields.Nested(WarehouseSchema, dump_only=True)
    user = fields.Nested('UserSchema', dump_only=True)  # NEW: Show user info
    asset_transactions = fields.Nested('AssetTransactionSchema', many=True, dump_only=True)
    
    @validates("warehouse_id")
    def validate_warehouse(self, value, **kwargs):
        warehouse = db.session.get(Warehouse, value)
        if warehouse is None:
            raise ValidationError("Invalid warehouse_id: warehouse does not exist.")


class AssetTransactionSchema(Schema):
    id = fields.Int(dump_only=True)
    transaction_id = fields.Int(dump_only=True)  # Bound to Transaction.id (primary key)
    asset_id = fields.Int(required=True)
    quantity = fields.Int(required=True)
    amount = fields.Float()
    total_value = fields.Float(dump_only=True)  # Calculated field
    
    # Nested relationships for response
    asset = fields.Nested(FixedAssetSchema, dump_only=True)
    
    @validates("asset_id")
    def validate_asset(self, value, **kwargs):
        asset = db.session.get(FixedAsset, value)
        if asset is None:
            raise ValidationError("Invalid asset_id: asset does not exist.")
    
    @validates("quantity")
    def validate_quantity(self, value, **kwargs):
        if value <= 0:
            raise ValidationError("Quantity must be greater than 0.")
    
    @validates("amount")
    def validate_amount(self, value, **kwargs):
        if value is not None and value < 0:
            raise ValidationError("Amount cannot be negative.")


class TransactionCreateSchema(Schema):
    """Schema for creating transactions with nested asset transactions"""
    date = fields.Date(required=True)
    description = fields.Str(allow_none=True)
    reference_number = fields.Str(allow_none=True)
    warehouse_id = fields.Int(required=True)
    # NOTE: user_id is NOT included here - it should be set from the current authenticated user in the view
    attached_file = fields.Str(allow_none=True)
    transaction_type = fields.Bool(required=True)  # True for IN, False for OUT
    asset_transactions = fields.Nested('AssetTransactionCreateSchema', many=True, required=True)
    
    @validates("warehouse_id")
    def validate_warehouse(self, value, **kwargs):
        warehouse = db.session.get(Warehouse, value)
        if warehouse is None:
            raise ValidationError("Invalid warehouse_id: warehouse does not exist.")
    
    @validates("asset_transactions")
    def validate_asset_transactions(self, value, **kwargs):
        if not value or len(value) == 0:
            raise ValidationError("At least one asset transaction is required.")

    @staticmethod
    def generate_branch_specific_transaction_id(branch_id):
        """Generate branch-specific transaction ID like '1-1', '1-2', etc."""
        # Count existing transactions for this branch
        from sqlalchemy import func
        count = db.session.query(func.count(Transaction.id)).join(Warehouse).filter(
            Warehouse.branch_id == branch_id
        ).scalar() or 0
        
        return f"{branch_id}-{count + 1}"


class AssetTransactionCreateSchema(Schema):
    """Schema for creating asset transactions (without transaction_id)"""
    asset_id = fields.Int(required=True)
    quantity = fields.Int(required=True)
    amount = fields.Decimal(places=2, allow_none=True)
    
    @validates("asset_id")
    def validate_asset(self, value, **kwargs):
        asset = db.session.get(FixedAsset, value)
        if asset is None:
            raise ValidationError("Invalid asset_id: asset does not exist.")
    
    @validates("quantity")
    def validate_quantity(self, value, **kwargs):
        if value <= 0:
            raise ValidationError("Quantity must be greater than 0.")
    
    @validates("amount")
    def validate_amount(self, value, **kwargs):
        if value is not None and value < 0:
            raise ValidationError("Amount cannot be negative.")


class JobDescriptionSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    can_read_branch = fields.Bool(load_default=False, required=False)
    can_edit_branch = fields.Bool(load_default=False, required=False)
    can_delete_branch = fields.Bool(load_default=False, required=False)
    can_read_warehouse = fields.Bool(load_default=False, required=False)
    can_edit_warehouse = fields.Bool(load_default=False, required=False)
    can_delete_warehouse = fields.Bool(load_default=False, required=False)
    can_read_asset = fields.Bool(load_default=False, required=False)
    can_edit_asset = fields.Bool(load_default=False, required=False)
    can_delete_asset = fields.Bool(load_default=False, required=False)
    can_print_barcode = fields.Bool(load_default=False, required=False)
    can_make_report = fields.Bool(load_default=False, required=False)
    can_make_transaction = fields.Bool(load_default=False, required=False)


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    full_name = fields.Str(required=True)
    email = fields.Email(required=True)
    role = fields.Str(required=True)

    # permissions - dump_only for response, not required for input
    can_read_branch = fields.Bool(dump_only=True)
    can_edit_branch = fields.Bool(dump_only=True)
    can_delete_branch = fields.Bool(dump_only=True)
    can_read_warehouse = fields.Bool(dump_only=True)
    can_edit_warehouse = fields.Bool(dump_only=True)
    can_delete_warehouse = fields.Bool(dump_only=True)
    can_read_asset = fields.Bool(dump_only=True)
    can_edit_asset = fields.Bool(dump_only=True)
    can_delete_asset = fields.Bool(dump_only=True)
    can_print_barcode = fields.Bool(dump_only=True)
    can_make_report = fields.Bool(dump_only=True)
    can_make_transaction = fields.Bool(dump_only=True)


class UserCreateSchema(Schema):
    """Schema for creating users - only requires basic info"""
    full_name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True)
    role = fields.Str(required=True)
    permissions = fields.Dict(required=False)


class UserUpdateSchema(Schema):
    """Schema for updating users - all fields optional"""
    full_name = fields.Str(required=False)
    email = fields.Email(required=False)
    role = fields.Str(required=False)
    
    # Optional permission updates
    permissions = fields.Dict(required=False)