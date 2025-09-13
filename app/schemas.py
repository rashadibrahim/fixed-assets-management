from marshmallow import Schema, fields, validates, ValidationError
from .models import db, Warehouse, Branch


class BranchSchema(Schema):
    id = fields.Int(dump_only=True)
    name_ar = fields.Str(required=True)
    name_en = fields.Str()
    address_ar = fields.Str()
    address_en = fields.Str()


class WarehouseSchema(Schema):
    id = fields.Int(dump_only=True)
    branch_id = fields.Int()
    name_ar = fields.Str(required=True)
    name_en = fields.Str()
    address_ar = fields.Str()
    address_en = fields.Str()
    @validates("branch_id")
    def validate_branch(self, value, **kwargs):  # <-- add **kwargs here
        branch = db.session.get(Branch, value)  # SQLAlchemy 2.0 way
        if branch is None:
            raise ValidationError("Invalid branch_id: branch does not exist.")


class AttachedFileSchema(Schema):
    id = fields.Int(dump_only=True)
    asset_id = fields.Int(required=True)
    file_path = fields.Str(required=True)


class FixedAssetSchema(Schema):
    id = fields.Int(dump_only=True)
    name_ar = fields.Str(required=True)
    name_en = fields.Str(required=True)
    purchase_date = fields.Date(required=True)
    warehouse_id = fields.Int(required=True)
    value = fields.Decimal(required=True, as_string=True)
    quantity = fields.Int(required=True)
    purchase_invoice = fields.Str(required=True)
    product_code = fields.Str(required=True)
    category = fields.Str(required=True)
    subcategory = fields.Str(required=True)
    is_active = fields.Bool(required=True)
    created_at = fields.DateTime(dump_only=True)
    attached_files = fields.List(fields.Nested(AttachedFileSchema), dump_only=True)
    @validates("warehouse_id")
    def validate_warehouse(self, value, **kwargs):
        warehouse = db.session.get(Warehouse, value)  # SQLAlchemy 2.0 way
        if warehouse is None:
            raise ValidationError("Invalid warehouse_id: warehouse does not exist.")


class JobDescriptionSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    can_read_branch = fields.Bool(required=True)
    can_edit_branch = fields.Bool(required=True)
    can_delete_branch = fields.Bool(required=True)
    can_read_warehouse = fields.Bool(required=True)
    can_edit_warehouse = fields.Bool(required=True)
    can_delete_warehouse = fields.Bool(required=True)
    can_read_asset = fields.Bool(required=True)
    can_edit_asset = fields.Bool(required=True)
    can_delete_asset = fields.Bool(required=True)
    can_print_barcode = fields.Bool(required=True)


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    full_name = fields.Str(required=True)
    email = fields.Email(required=True)
    role = fields.Str(required=True)

    # permissions
    can_read_branch = fields.Bool(required=True)
    can_edit_branch = fields.Bool(required=True)
    can_delete_branch = fields.Bool(required=True)
    can_read_warehouse = fields.Bool(required=True)
    can_edit_warehouse = fields.Bool(required=True)
    can_delete_warehouse = fields.Bool(required=True)
    can_read_asset = fields.Bool(required=True)
    can_edit_asset = fields.Bool(required=True)
    can_delete_asset = fields.Bool(required=True)
    can_print_barcode = fields.Bool(required=True)
