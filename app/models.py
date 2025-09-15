from datetime import datetime
from . import db
from werkzeug.security import generate_password_hash, check_password_hash


class Branch(db.Model):
    __tablename__ = "branches"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(255), nullable=False)
    name_en = db.Column(db.String(255), nullable=False)
    address_ar = db.Column(db.String(500), nullable=False)
    address_en = db.Column(db.String(500), nullable=False)

    warehouses = db.relationship("Warehouse", back_populates="branch", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Branch {self.id} {self.name_en or self.name_ar}>"


class Warehouse(db.Model):
    __tablename__ = "warehouses"
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="CASCADE"), nullable=True)
    name_ar = db.Column(db.String(255), nullable=False)
    name_en = db.Column(db.String(255), nullable=False)
    address_ar = db.Column(db.String(500), nullable=False)
    address_en = db.Column(db.String(500), nullable=False)

    branch = db.relationship("Branch", back_populates="warehouses")
    # assets = db.relationship("FixedAsset", back_populates="warehouse", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Warehouse {self.id} {self.name_en or self.name_ar}>"


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    subcategory = db.Column(db.String(100), nullable=False)
    
    # Relationship with FixedAsset
    assets = db.relationship("FixedAsset", back_populates="category_rel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category {self.category} - {self.subcategory}>"


class FixedAsset(db.Model):
    __tablename__ = "fixed_assets"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(255), nullable=False)
    name_en = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    product_code = db.Column(db.String(100), unique=True, nullable=True)  # used for barcode
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # New relationship with Category
    category_rel = db.relationship("Category", back_populates="assets")
    #transactions = db.relationship("AssetTransaction", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FixedAsset {self.id} {self.name_en or self.name_ar}>"

# class AssetTransaction(db.Model):
#     __tablename__ = "asset_transactions"
#     id = db.Column(db.Integer, primary_key=True)

#     asset_id = db.Column(db.Integer, db.ForeignKey("fixed_assets.id", ondelete="CASCADE"), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))  # who added
#     quantity_added = db.Column(db.Integer, nullable=False)
#     created_at = db.Column(db.DateTime, default=db.func.now())

#     # Relationships
#     asset = db.relationship("FixedAsset", back_populates="transactions")
#     user = db.relationship("User", back_populates="asset_transactions")
#     files = db.relationship("AssetTransactionFile", back_populates="transaction", cascade="all, delete-orphan")


# class AssetTransactionFile(db.Model):
#     __tablename__ = "asset_transaction_files"
#     id = db.Column(db.Integer, primary_key=True)

#     transaction_id = db.Column(db.Integer, db.ForeignKey("asset_transactions.id", ondelete="CASCADE"), nullable=False)
#     file_path = db.Column(db.String(255), nullable=False)  # path in your uploads folder
#     uploaded_at = db.Column(db.DateTime, default=db.func.now())

#     # Relationship
#     transaction = db.relationship("AssetTransaction", back_populates="files")


class JobDescription(db.Model):
    __tablename__ = "job_descriptions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # permissions template
    can_read_branch = db.Column(db.Boolean, default=False)
    can_edit_branch = db.Column(db.Boolean, default=False)
    can_delete_branch = db.Column(db.Boolean, default=False)
    can_read_warehouse = db.Column(db.Boolean, default=False)
    can_edit_warehouse = db.Column(db.Boolean, default=False)
    can_delete_warehouse = db.Column(db.Boolean, default=False)
    can_read_asset = db.Column(db.Boolean, default=False)
    can_edit_asset = db.Column(db.Boolean, default=False)
    can_delete_asset = db.Column(db.Boolean, default=False)
    can_print_barcode = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<JobDescription {self.name}>"


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(100), nullable=False)

    # permissions (copied from JobDescription at signup)
    can_read_branch = db.Column(db.Boolean, default=False)
    can_edit_branch = db.Column(db.Boolean, default=False)
    can_delete_branch = db.Column(db.Boolean, default=False)
    can_read_warehouse = db.Column(db.Boolean, default=False)
    can_edit_warehouse = db.Column(db.Boolean, default=False)
    can_delete_warehouse = db.Column(db.Boolean, default=False)
    can_read_asset = db.Column(db.Boolean, default=False)
    can_edit_asset = db.Column(db.Boolean, default=False)
    can_delete_asset = db.Column(db.Boolean, default=False)
    can_print_barcode = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.id} {self.email}>"
