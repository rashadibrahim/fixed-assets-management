from flask_restx import fields
from .swagger import api, branches_ns, warehouses_ns, assets_ns, categories_ns, auth_ns, job_roles_ns, transactions_ns, asset_transactions_ns

# Common response models
error_model = api.model('ErrorResponse', {
    'error': fields.String(description='Error message'),
    'errors': fields.Raw(description='Validation errors (object with field names as keys)')
})

success_model = api.model('SuccessResponse', {
    'message': fields.String(description='Success message')
})

# Barcode response model
barcode_model = api.model('BarcodeResponse', {
    'product_code': fields.String(description='Product code used for the barcode'),
    'barcode_image': fields.String(description='Base64 encoded barcode image')
})

# Pagination response model
pagination_model = api.model('PaginationResponse', {
    'items': fields.Raw(description='List of items'),
    'total': fields.Integer(description='Total number of items'),
    'page': fields.Integer(description='Current page number'),
    'pages': fields.Integer(description='Total number of pages')
})


# Warehouse models
warehouse_model = api.model('Warehouse', {
    'id': fields.Integer(readonly=True, description='Warehouse unique identifier'),
    'branch_id': fields.Integer(description='Branch ID this warehouse belongs to'),
    'name_ar': fields.String(required=True, description='Warehouse name in Arabic'),
    'name_en': fields.String(description='Warehouse name in English'),
    'address_ar': fields.String(description='Warehouse address in Arabic'),
    'address_en': fields.String(description='Warehouse address in English'),
})


warehouse_input_model = api.model('WarehouseInput', {
    'branch_id': fields.Integer(description='Branch ID this warehouse belongs to'),
    'name_ar': fields.String(required=True, description='Warehouse name in Arabic'),
    'name_en': fields.String(description='Warehouse name in English'),
    'address_ar': fields.String(description='Warehouse address in Arabic'),
    'address_en': fields.String(description='Warehouse address in English'),
})

# Branch models
branch_model = api.model('Branch', {
    'id': fields.Integer(readonly=True, description='Branch unique identifier'),
    'name_ar': fields.String(required=True, description='Branch name in Arabic'),
    'name_en': fields.String(description='Branch name in English'),
    'address_ar': fields.String(description='Branch address in Arabic'),
    'address_en': fields.String(description='Branch address in English')
})

branch_with_warehouses_model = api.clone('BranchWithCounts', branch_model, {
    'warehouse_count': fields.Integer(description='Number of warehouses in branch'),
    'warehouses': fields.List(fields.Nested(warehouse_model), description='List of warehouses in branch')
})

branch_input_model = api.model('BranchInput', {
    'name_ar': fields.String(required=True, description='Branch name in Arabic'),
    'name_en': fields.String(description='Branch name in English'),
    'address_ar': fields.String(description='Branch address in Arabic'),
    'address_en': fields.String(description='Branch address in English'),
})



# Category models
category_model = api.model('Category', {
    'id': fields.Integer(readonly=True, description='Category unique identifier'),
    'category': fields.String(required=True, description='Asset category'),
    'subcategory': fields.String(required=True, description='Asset subcategory')
})

category_input_model = api.model('CategoryInput', {
    'category': fields.String(required=True, description='Asset category'),
    'subcategory': fields.String(required=True, description='Asset subcategory')
})

# Fixed Asset models
asset_model = api.model('FixedAsset', {
    'id': fields.Integer(readonly=True, description='Asset unique identifier'),
    'name_ar': fields.String(required=True, description='Asset name in Arabic'),
    'name_en': fields.String(required=True, description='Asset name in English'),
    'quantity': fields.Integer(required=True, description='Asset quantity', default=1),
    'product_code': fields.String(description='Product code or serial number (used for barcode)'),
    'category_id': fields.Integer(required=True, description='Category ID this asset belongs to'),
    'is_active': fields.Boolean(required=True, description='Whether the asset is active')
})

asset_input_model = api.model('FixedAssetInput', {
    'name_ar': fields.String(required=True, description='Asset name in Arabic'),
    'name_en': fields.String(required=True, description='Asset name in English'),
    'quantity': fields.Integer(description='Asset quantity', default=1),
    'product_code': fields.String(description='Product code or serial number'),
    'category_id': fields.Integer(required=True, description='Category ID this asset belongs to'),
    'is_active': fields.Boolean(description='Whether the asset is active', default=True)
})

asset_search_response_model = api.model('AssetSearchResponse', {
    'items': fields.List(fields.Nested(asset_model), description='List of found assets'),
    'total': fields.Integer(description='Total number of matching assets'),
    'page': fields.Integer(description='Current page number'),
    'pages': fields.Integer(description='Total number of pages')
})

# User models
user_model = api.model('User', {
    'id': fields.Integer(readonly=True, description='User unique identifier'),
    'full_name': fields.String(required=True, description='User full name'),
    'email': fields.String(required=True, description='User email address'),
    'role': fields.String(required=True, description='User role'),
    'can_read_branch': fields.Boolean(description='Permission to read branches'),
    'can_edit_branch': fields.Boolean(description='Permission to edit branches'),
    'can_delete_branch': fields.Boolean(description='Permission to delete branches'),
    'can_read_warehouse': fields.Boolean(description='Permission to read warehouses'),
    'can_edit_warehouse': fields.Boolean(description='Permission to edit warehouses'),
    'can_delete_warehouse': fields.Boolean(description='Permission to delete warehouses'),
    'can_read_asset': fields.Boolean(description='Permission to read assets'),
    'can_edit_asset': fields.Boolean(description='Permission to edit assets'),
    'can_delete_asset': fields.Boolean(description='Permission to delete assets'),
    'can_print_barcode': fields.Boolean(description='Permission to print barcodes')
})

user_input_model = api.model('UserInput', {
    'full_name': fields.String(required=True, description='User full name'),
    'email': fields.String(required=True, description='User email address'),
    'password': fields.String(required=True, description='User password'),
    'role': fields.String(required=True, description='User role')
})

user_update_model = api.model('UserUpdate', {
    'full_name': fields.String(description='Username'),
    'email': fields.String(description='User email address'),
    'role': fields.String(description='User role'),
    'permissions': fields.Nested(api.model('UserPermissions', {
        'can_read_branch': fields.Boolean(description='Permission to read branches'),
        'can_edit_branch': fields.Boolean(description='Permission to edit branches'),
        'can_delete_branch': fields.Boolean(description='Permission to delete branches'),
        'can_read_warehouse': fields.Boolean(description='Permission to read warehouses'),
        'can_edit_warehouse': fields.Boolean(description='Permission to edit warehouses'),
        'can_delete_warehouse': fields.Boolean(description='Permission to delete warehouses'),
        'can_read_asset': fields.Boolean(description='Permission to read assets'),
        'can_edit_asset': fields.Boolean(description='Permission to edit assets'),
        'can_delete_asset': fields.Boolean(description='Permission to delete assets'),
        'can_print_barcode': fields.Boolean(description='Permission to print barcodes')
    }), description='User permissions')
})

# Job Role models
job_role_model = api.model('JobRole', {
    'id': fields.Integer(readonly=True, description='Job role unique identifier'),
    'name': fields.String(required=True, description='Job role name'),
    'can_read_branch': fields.Boolean(required=True, description='Permission to read branches'),
    'can_edit_branch': fields.Boolean(required=True, description='Permission to edit branches'),
    'can_delete_branch': fields.Boolean(required=True, description='Permission to delete branches'),
    'can_read_warehouse': fields.Boolean(required=True, description='Permission to read warehouses'),
    'can_edit_warehouse': fields.Boolean(required=True, description='Permission to edit warehouses'),
    'can_delete_warehouse': fields.Boolean(required=True, description='Permission to delete warehouses'),
    'can_read_asset': fields.Boolean(required=True, description='Permission to read assets'),
    'can_edit_asset': fields.Boolean(required=True, description='Permission to edit assets'),
    'can_delete_asset': fields.Boolean(required=True, description='Permission to delete assets'),
    'can_print_barcode': fields.Boolean(required=True, description='Permission to print barcodes')
})

job_role_input_model = api.model('JobRoleInput', {
    'name': fields.String(required=True, description='Job role name'),
    'can_read_branch': fields.Boolean(description='Permission to read branches', default=False),
    'can_edit_branch': fields.Boolean(description='Permission to edit branches', default=False),
    'can_delete_branch': fields.Boolean(description='Permission to delete branches', default=False),
    'can_read_warehouse': fields.Boolean(description='Permission to read warehouses', default=False),
    'can_edit_warehouse': fields.Boolean(description='Permission to edit warehouses', default=False),
    'can_delete_warehouse': fields.Boolean(description='Permission to delete warehouses', default=False),
    'can_read_asset': fields.Boolean(description='Permission to read assets', default=False),
    'can_edit_asset': fields.Boolean(description='Permission to edit assets', default=False),
    'can_delete_asset': fields.Boolean(description='Permission to delete assets', default=False),
    'can_print_barcode': fields.Boolean(description='Permission to print barcodes', default=False)
})

# Authentication models
login_model = api.model('Login', {
    'email': fields.String(required=True, description='User email address'),
    'password': fields.String(required=True, description='User password')
})

auth_response_model = api.model('AuthResponse', {
    'access_token': fields.String(description='JWT access token'),
    'user': fields.Nested(user_model, description='User information')
})

# Statistics model
stats_model = api.model('Statistics', {
    'total_branches': fields.Integer(description='Total number of branches'),
    'total_warehouses': fields.Integer(description='Total number of warehouses'),
    'total_assets': fields.Integer(description='Total number of assets'),
    'active_assets': fields.Integer(description='Number of active assets'),
    'inactive_assets': fields.Integer(description='Number of inactive assets'),
    'total_users': fields.Integer(description='Total number of users'),
    'job_roles_count': fields.Integer(description='Number of job roles')
})



# Transaction Models
# Asset Transaction Models (define before transaction_model since it's referenced)
asset_transaction_model = api.model('AssetTransaction', {
    'id': fields.Integer(required=True, description='Asset Transaction ID'),
    'transaction_id': fields.Integer(required=True, description='Transaction ID'),
    'asset_id': fields.Integer(required=True, description='Asset ID'),
    'quantity': fields.Integer(required=True, description='Quantity'),
    'amount': fields.Float(description='Unit amount/price'),
    'total_value': fields.Float(description='Total value (quantity * amount)'),
    'asset': fields.Nested(asset_model, description='Asset details')
})

# Transaction Models
transaction_model = api.model('Transaction', {
    'id': fields.Integer(required=True, description='Transaction ID'),
    'custom_id': fields.String(required=True, description='Custom transaction ID (Branch-specific)'),
    'date': fields.Date(required=True, description='Transaction date'),
    'description': fields.String(description='Transaction description'),
    'reference_number': fields.String(description='Reference number'),
    'warehouse_id': fields.Integer(required=True, description='Warehouse ID'),
    'user_id': fields.Integer(description='User ID who created the transaction'),
    'attached_file': fields.String(description='Attached file path/URL'),
    'transaction_type': fields.Boolean(required=True, description='Transaction type (true=IN, false=OUT)'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'warehouse': fields.Nested(warehouse_model, description='Warehouse details'),
    'user': fields.Nested(user_model, description='User who created the transaction'),
    'asset_transactions': fields.List(fields.Nested(asset_transaction_model), description='Asset transactions')
})

transaction_input_model = api.model('TransactionInput', {
    'date': fields.Date(required=True, description='Transaction date'),
    'description': fields.String(description='Transaction description'),
    'reference_number': fields.String(description='Reference number'),
    'warehouse_id': fields.Integer(required=True, description='Warehouse ID'),
    'attached_file': fields.String(description='Attached file path/URL'),
    'transaction_type': fields.Boolean(required=True, description='Transaction type (true=IN, false=OUT)')
})

asset_transaction_input_create = api.model('AssetTransactionInputCreate', {
    'asset_id': fields.Integer(required=True, description='Asset ID'),
    'quantity': fields.Integer(required=True, description='Quantity', min=1),
    'amount': fields.Float(description='Unit amount/price')
})

transaction_create_model = api.model('TransactionCreate', {
    'date': fields.Date(required=True, description='Transaction date'),
    'description': fields.String(description='Transaction description'),
    'reference_number': fields.String(description='Reference number'),
    'warehouse_id': fields.Integer(required=True, description='Warehouse ID'),
    'attached_file': fields.String(description='Attached file path/URL'),
    'transaction_type': fields.Boolean(required=True, description='Transaction type (true=IN, false=OUT)'),
    'asset_transactions': fields.List(fields.Nested(asset_transaction_input_create), 
                                     required=True, description='Asset transactions', min_items=1)
})

asset_transaction_input_model = api.model('AssetTransactionInput', {
    'asset_id': fields.Integer(required=True, description='Asset ID'),
    'quantity': fields.Integer(required=True, description='Quantity', min=1),
    'amount': fields.Float(description='Unit amount/price')
})

# Transaction Summary Model
transaction_summary_model = api.model('TransactionSummary', {
    'total_transactions': fields.Integer(description='Total number of transactions'),
    'total_in_transactions': fields.Integer(description='Total IN transactions'),
    'total_out_transactions': fields.Integer(description='Total OUT transactions'),
    'total_in_value': fields.Float(description='Total value of IN transactions'),
    'total_out_value': fields.Float(description='Total value of OUT transactions'),
    'net_value': fields.Float(description='Net value (IN - OUT)')
})

