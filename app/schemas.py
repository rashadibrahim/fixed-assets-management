from marshmallow import Schema, fields, validates, ValidationError
from .models import db, Category, Branch


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
    address_ar = fields.Str(required=True)
    address_en = fields.Str(required=True)
    @validates("branch_id")
    def validate_branch(self, value, **kwargs):  # <-- add **kwargs here
        branch = db.session.get(Branch, value)  # SQLAlchemy 2.0 way
        if branch is None:
            raise ValidationError("Invalid branch_id: branch does not exist.")


class AttachedFileSchema(Schema):
    id = fields.Int(dump_only=True)
    asset_id = fields.Int(required=True)
    file_path = fields.Str(required=True)
    uploaded_at = fields.DateTime(dump_only=True)
    comment = fields.Str()

class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    category = fields.Str(required=True)
    subcategory = fields.Str(required=True)


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
        category = db.session.get(Category, value)  # SQLAlchemy 2.0 way
        if category is None:
            raise ValidationError("Invalid category_id: category does not exist.")


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
