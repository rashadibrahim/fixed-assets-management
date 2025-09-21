from datetime import datetime
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Numeric


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
    transactions = db.relationship("Transaction", back_populates="warehouse", cascade="all, delete-orphan")

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
    asset_transactions = db.relationship("AssetTransaction", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FixedAsset {self.id} {self.name_en or self.name_ar}>"


class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)  # Automatic ID
    custom_id = db.Column(db.String(50), unique=True, nullable=False)  # Format: "BRANCH_ID-TRANSACTION_ID"
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    description = db.Column(db.Text, nullable=True)
    reference_number = db.Column(db.String(100), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    attached_file = db.Column(db.String(500), nullable=True)  # File path/URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    warehouse = db.relationship("Warehouse", back_populates="transactions")
    asset_transactions = db.relationship("AssetTransaction", back_populates="transaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaction {self.custom_id} - {self.description[:50]}>"

    @property
    def branch(self):
        """Get branch through warehouse relationship"""
        return self.warehouse.branch if self.warehouse else None

    @staticmethod
    def generate_custom_id(branch_id):
        """Generate custom ID in format: BRANCH_ID-TRANSACTION_COUNT"""
        # Count existing transactions for this branch
        from sqlalchemy import func
        count = db.session.query(func.count(Transaction.id)).join(Warehouse).filter(
            Warehouse.branch_id == branch_id
        ).scalar() or 0
        
        return f"{branch_id}-{count + 1}"


class AssetTransaction(db.Model):
    __tablename__ = "asset_transactions"
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("fixed_assets.id", ondelete="RESTRICT"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    amount = db.Column(Numeric(10, 2), nullable=True)  # Using Numeric for monetary values
    total_value = db.Column(Numeric(12, 2), nullable=True)  # Calculated: quantity * amount
    transaction_type = db.Column(db.Boolean, nullable=False)  # True for IN, False for OUT
    
    # Relationships
    transaction = db.relationship("Transaction", back_populates="asset_transactions")
    asset = db.relationship("FixedAsset", back_populates="asset_transactions")

    def __repr__(self):
        type_str = "IN" if self.transaction_type else "OUT"
        return f"<AssetTransaction {self.id} - Asset:{self.asset_id} Qty:{self.quantity} Total:{self.total_value} Type:{type_str}>"

    @property
    def type_display(self):
        """Human readable transaction type"""
        return "IN" if self.transaction_type else "OUT"

    def calculate_total_value(self):
        """Calculate and update total_value based on quantity * amount"""
        if self.quantity is not None and self.amount is not None:
            self.total_value = self.quantity * self.amount
        else:
            self.total_value = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calculate_total_value()


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