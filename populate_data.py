#!/usr/bin/env python3
"""
Database Population Script for Fixed Assets Management System
This script creates realistic test data for all models in the system.
"""

import os
import sys
import random
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    Branch, Warehouse, Category, FixedAsset, 
    Transaction, AssetTransaction, JobDescription, User
)

def clear_existing_data():
    """Clear all existing data from the database"""
    print("🗑️  Clearing existing data...")
    
    # Order matters due to foreign key constraints
    AssetTransaction.query.delete()
    Transaction.query.delete()
    FixedAsset.query.delete()
    Category.query.delete()
    Warehouse.query.delete()
    Branch.query.delete()
    User.query.delete()
    JobDescription.query.delete()
    
    db.session.commit()
    print("✅ Existing data cleared")

def create_job_descriptions():
    """Create job roles with different permission levels"""
    print("👥 Creating job descriptions...")
    
    job_descriptions = [
        {
            'name': 'Administrator',
            'can_read_branch': True,
            'can_edit_branch': True,
            'can_delete_branch': True,
            'can_read_warehouse': True,
            'can_edit_warehouse': True,
            'can_delete_warehouse': True,
            'can_read_asset': True,
            'can_edit_asset': True,
            'can_delete_asset': True,
            'can_print_barcode': True,
            'can_make_report': True,
            'can_make_transaction': True,
        },
        {
            'name': 'Manager',
            'can_read_branch': True,
            'can_edit_branch': True,
            'can_delete_branch': False,
            'can_read_warehouse': True,
            'can_edit_warehouse': True,
            'can_delete_warehouse': False,
            'can_read_asset': True,
            'can_edit_asset': True,
            'can_delete_asset': False,
            'can_print_barcode': True,
            'can_make_report': True,
            'can_make_transaction': True,
        },
        {
            'name': 'Employee',
            'can_read_branch': True,
            'can_edit_branch': False,
            'can_delete_branch': False,
            'can_read_warehouse': True,
            'can_edit_warehouse': False,
            'can_delete_warehouse': False,
            'can_read_asset': True,
            'can_edit_asset': False,
            'can_delete_asset': False,
            'can_print_barcode': True,
            'can_make_report': False,
            'can_make_transaction': True,
        },
        {
            'name': 'Viewer',
            'can_read_branch': True,
            'can_edit_branch': False,
            'can_delete_branch': False,
            'can_read_warehouse': True,
            'can_edit_warehouse': False,
            'can_delete_warehouse': False,
            'can_read_asset': True,
            'can_edit_asset': False,
            'can_delete_asset': False,
            'can_print_barcode': False,
            'can_make_report': True,
            'can_make_transaction': False,
        }
    ]
    
    created_jobs = []
    for job_data in job_descriptions:
        job = JobDescription(**job_data)
        db.session.add(job)
        created_jobs.append(job)
    
    db.session.commit()
    print(f"✅ Created {len(created_jobs)} job descriptions")
    return created_jobs

def create_users(job_descriptions):
    """Create users with different roles"""
    print("👤 Creating users...")
    
    users_data = [
        {'full_name': 'Ahmed Al-Rashid', 'email': 'ahmed.admin@company.com', 'password': 'admin123', 'role': 'Administrator'},
        {'full_name': 'Fatima Al-Zahra', 'email': 'fatima.manager@company.com', 'password': 'manager123', 'role': 'Manager'},
        {'full_name': 'Mohammed Hassan', 'email': 'mohammed.manager@company.com', 'password': 'manager123', 'role': 'Manager'},
        {'full_name': 'Aisha Ibrahim', 'email': 'aisha.employee@company.com', 'password': 'employee123', 'role': 'Employee'},
        {'full_name': 'Omar Khalil', 'email': 'omar.employee@company.com', 'password': 'employee123', 'role': 'Employee'},
        {'full_name': 'Layla Mahmoud', 'email': 'layla.employee@company.com', 'password': 'employee123', 'role': 'Employee'},
        {'full_name': 'Yusuf Ahmad', 'email': 'yusuf.viewer@company.com', 'password': 'viewer123', 'role': 'Viewer'},
        {'full_name': 'Maryam Ali', 'email': 'maryam.viewer@company.com', 'password': 'viewer123', 'role': 'Viewer'},
    ]
    
    # Create a mapping of role names to job descriptions
    job_map = {job.name: job for job in job_descriptions}
    
    created_users = []
    for user_data in users_data:
        role_name = user_data['role']
        job = job_map.get(role_name)
        
        if job:
            user = User(
                full_name=user_data['full_name'],
                email=user_data['email'],
                role=role_name,
                can_read_branch=job.can_read_branch,
                can_edit_branch=job.can_edit_branch,
                can_delete_branch=job.can_delete_branch,
                can_read_warehouse=job.can_read_warehouse,
                can_edit_warehouse=job.can_edit_warehouse,
                can_delete_warehouse=job.can_delete_warehouse,
                can_read_asset=job.can_read_asset,
                can_edit_asset=job.can_edit_asset,
                can_delete_asset=job.can_delete_asset,
                can_print_barcode=job.can_print_barcode,
                can_make_report=job.can_make_report,
                can_make_transaction=job.can_make_transaction,
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            created_users.append(user)
    
    db.session.commit()
    print(f"✅ Created {len(created_users)} users")
    return created_users

def create_branches():
    """Create branches in different locations"""
    print("🏢 Creating branches...")
    
    branches_data = [
        {
            'name_ar': 'فرع الرياض الرئيسي',
            'name_en': 'Riyadh Main Branch',
            'address_ar': 'طريق الملك فهد، الرياض، المملكة العربية السعودية',
            'address_en': 'King Fahd Road, Riyadh, Saudi Arabia'
        },
        {
            'name_ar': 'فرع جدة',
            'name_en': 'Jeddah Branch',
            'address_ar': 'شارع التحلية، جدة، المملكة العربية السعودية',
            'address_en': 'Tahlia Street, Jeddah, Saudi Arabia'
        },
        {
            'name_ar': 'فرع الدمام',
            'name_en': 'Dammam Branch',
            'address_ar': 'حي الفيصلية، الدمام، المملكة العربية السعودية',
            'address_en': 'Al Faisaliyah District, Dammam, Saudi Arabia'
        },
        {
            'name_ar': 'فرع المدينة المنورة',
            'name_en': 'Medina Branch',
            'address_ar': 'شارع قباء، المدينة المنورة، المملكة العربية السعودية',
            'address_en': 'Quba Street, Medina, Saudi Arabia'
        },
        {
            'name_ar': 'فرع أبها',
            'name_en': 'Abha Branch',
            'address_ar': 'طريق الأمير سلطان، أبها، المملكة العربية السعودية',
            'address_en': 'Prince Sultan Road, Abha, Saudi Arabia'
        }
    ]
    
    created_branches = []
    for branch_data in branches_data:
        branch = Branch(**branch_data)
        db.session.add(branch)
        created_branches.append(branch)
    
    db.session.commit()
    print(f"✅ Created {len(created_branches)} branches")
    return created_branches

def create_warehouses(branches):
    """Create warehouses for each branch"""
    print("🏭 Creating warehouses...")
    
    warehouse_types = [
        ('مستودع المعدات', 'Equipment Warehouse'),
        ('مستودع المواد الخام', 'Raw Materials Warehouse'),
        ('مستودع المنتجات النهائية', 'Finished Products Warehouse'),
        ('مستودع قطع الغيار', 'Spare Parts Warehouse'),
        ('مستودع التبريد', 'Cold Storage Warehouse')
    ]
    
    created_warehouses = []
    for branch in branches:
        # Each branch gets 2-4 warehouses
        num_warehouses = random.randint(2, 4)
        selected_types = random.sample(warehouse_types, num_warehouses)
        
        for i, (name_ar, name_en) in enumerate(selected_types, 1):
            warehouse = Warehouse(
                branch_id=branch.id,
                name_ar=f"{name_ar} - {branch.name_ar}",
                name_en=f"{name_en} - {branch.name_en}",
                address_ar=f"{branch.address_ar} - المبنى {i}",
                address_en=f"{branch.address_en} - Building {i}"
            )
            db.session.add(warehouse)
            created_warehouses.append(warehouse)
    
    db.session.commit()
    print(f"✅ Created {len(created_warehouses)} warehouses")
    return created_warehouses

def create_categories():
    """Create asset categories and subcategories"""
    print("📦 Creating categories...")
    
    categories_data = [
        # IT Equipment
        ('معدات تقنية المعلومات', 'IT Equipment', 'أجهزة كمبيوتر', 'Computers'),
        ('معدات تقنية المعلومات', 'IT Equipment', 'طابعات', 'Printers'),
        ('معدات تقنية المعلومات', 'IT Equipment', 'خوادم', 'Servers'),
        ('معدات تقنية المعلومات', 'IT Equipment', 'معدات شبكات', 'Network Equipment'),
        
        # Office Furniture
        ('أثاث مكتبي', 'Office Furniture', 'مكاتب', 'Desks'),
        ('أثاث مكتبي', 'Office Furniture', 'كراسي', 'Chairs'),
        ('أثاث مكتبي', 'Office Furniture', 'خزائن', 'Cabinets'),
        ('أثاث مكتبي', 'Office Furniture', 'طاولات اجتماعات', 'Meeting Tables'),
        
        # Vehicles
        ('مركبات', 'Vehicles', 'سيارات', 'Cars'),
        ('مركبات', 'Vehicles', 'شاحنات', 'Trucks'),
        ('مركبات', 'Vehicles', 'حافلات', 'Buses'),
        
        # Industrial Equipment
        ('معدات صناعية', 'Industrial Equipment', 'آلات', 'Machinery'),
        ('معدات صناعية', 'Industrial Equipment', 'أدوات', 'Tools'),
        ('معدات صناعية', 'Industrial Equipment', 'معدات السلامة', 'Safety Equipment'),
        
        # Electronics
        ('إلكترونيات', 'Electronics', 'هواتف', 'Phones'),
        ('إلكترونيات', 'Electronics', 'أجهزة تلفزيون', 'Televisions'),
        ('إلكترونيات', 'Electronics', 'أجهزة صوتية', 'Audio Equipment'),
    ]
    
    created_categories = []
    for category_ar, category_en, subcategory_ar, subcategory_en in categories_data:
        category = Category(
            category=f"{category_ar} / {category_en}",
            subcategory=f"{subcategory_ar} / {subcategory_en}"
        )
        db.session.add(category)
        created_categories.append(category)
    
    db.session.commit()
    print(f"✅ Created {len(created_categories)} categories")
    return created_categories

def create_assets(categories):
    """Create fixed assets with realistic data"""
    print("💻 Creating fixed assets...")
    
    # Asset templates by category type
    asset_templates = {
        'Computers': [
            ('كمبيوتر مكتبي ديل', 'Dell Desktop Computer', 500, 2500),
            ('لابتوب لينوفو', 'Lenovo Laptop', 300, 3500),
            ('كمبيوتر أبل iMac', 'Apple iMac Computer', 800, 8000),
            ('جهاز Surface Pro', 'Microsoft Surface Pro', 400, 4500),
        ],
        'Printers': [
            ('طابعة ليزر HP', 'HP Laser Printer', 150, 800),
            ('طابعة نافثة للحبر Canon', 'Canon Inkjet Printer', 80, 300),
            ('طابعة متعددة الوظائف Brother', 'Brother Multifunction Printer', 200, 1200),
        ],
        'Servers': [
            ('خادم Dell PowerEdge', 'Dell PowerEdge Server', 2000, 15000),
            ('خادم HP ProLiant', 'HP ProLiant Server', 1800, 12000),
        ],
        'Network Equipment': [
            ('راوتر سيسكو', 'Cisco Router', 300, 2000),
            ('سويتش شبكة', 'Network Switch', 150, 800),
            ('نقطة وصول لاسلكية', 'Wireless Access Point', 80, 400),
        ],
        'Desks': [
            ('مكتب خشبي تنفيذي', 'Executive Wooden Desk', 120, 2000),
            ('مكتب معدني', 'Metal Office Desk', 150, 800),
            ('مكتب قابل للتعديل', 'Adjustable Standing Desk', 180, 1500),
        ],
        'Chairs': [
            ('كرسي مكتب جلدي', 'Leather Office Chair', 100, 800),
            ('كرسي مكتب شبكي', 'Mesh Office Chair', 120, 600),
            ('كرسي اجتماعات', 'Conference Chair', 80, 400),
        ],
        'Cars': [
            ('سيارة تويوتا كامري', 'Toyota Camry', 0.5, 80000),
            ('سيارة نيسان التيما', 'Nissan Altima', 0.3, 75000),
            ('سيارة لكزس ES', 'Lexus ES', 0.2, 150000),
        ],
        'Trucks': [
            ('شاحنة إيسوزو', 'Isuzu Truck', 0.1, 120000),
            ('شاحنة فولفو', 'Volvo Truck', 0.1, 200000),
        ],
        'Machinery': [
            ('آلة تصنيع CNC', 'CNC Manufacturing Machine', 0.05, 500000),
            ('مولد كهرباء', 'Electric Generator', 0.2, 50000),
            ('ضاغط هواء', 'Air Compressor', 0.5, 15000),
        ],
        'Phones': [
            ('هاتف مكتبي سيسكو', 'Cisco Office Phone', 50, 300),
            ('هاتف ذكي سامسونج', 'Samsung Smartphone', 30, 2000),
            ('جهاز اتصال لاسلكي', 'Wireless Communication Device', 40, 500),
        ]
    }
    
    created_assets = []
    
    # Create assets for each category
    for category in categories:
        subcategory = category.subcategory.split(' / ')[1] if ' / ' in category.subcategory else category.subcategory
        
        # Find matching templates
        templates = None
        for key, template_list in asset_templates.items():
            if key.lower() in subcategory.lower():
                templates = template_list
                break
        
        if not templates:
            # Generic template if no specific match found
            templates = [
                (f'أصل ثابت - {category.subcategory}', f'Fixed Asset - {subcategory}', 10, 1000)
            ]
        
        # Create 3-8 assets per category
        num_assets = random.randint(3, 8)
        for i in range(num_assets):
            template = random.choice(templates)
            name_ar, name_en, base_qty, base_price = template
            
            # Add variation to quantities and prices
            quantity = max(1, int(base_qty * random.uniform(0.5, 2.0)))
            
            # Generate unique product code
            product_code = f"{category.id:02d}{i+1:03d}{random.randint(100, 999)}"
            
            asset = FixedAsset(
                name_ar=f"{name_ar} - {i+1}",
                name_en=f"{name_en} - {i+1}",
                quantity=quantity,
                product_code=product_code,
                category_id=category.id,
                is_active=True
            )
            db.session.add(asset)
            created_assets.append(asset)
    
    db.session.commit()
    print(f"✅ Created {len(created_assets)} fixed assets")
    return created_assets

def create_transactions(warehouses, assets, users):
    """Create realistic transactions with asset movements"""
    print("📋 Creating transactions...")
    
    created_transactions = []
    created_asset_transactions = []
    
    # Create transactions over the last 6 months
    start_date = date.today() - timedelta(days=180)
    
    # Get users who can make transactions
    transaction_users = [user for user in users if user.can_make_transaction]
    
    if not transaction_users:
        print("⚠️  No users with transaction permissions found!")
        return [], []
    
    # Create 50-100 transactions
    num_transactions = random.randint(50, 100)
    
    for i in range(num_transactions):
        # Random date within the last 6 months
        transaction_date = start_date + timedelta(days=random.randint(0, 180))
        
        # Random warehouse and user
        warehouse = random.choice(warehouses)
        user = random.choice(transaction_users)
        
        # Random transaction type (70% IN, 30% OUT)
        transaction_type = random.choices([True, False], weights=[70, 30])[0]
        
        # Generate custom_id using the model's method
        custom_id = Transaction.generate_custom_id(warehouse.branch_id)
        
        # Create transaction
        transaction = Transaction(
            custom_id=custom_id,
            date=transaction_date,
            description=f"{'استلام' if transaction_type else 'إصدار'} أصول ثابتة - {'Asset Receipt' if transaction_type else 'Asset Issue'} #{i+1}",
            reference_number=f"REF-{random.randint(1000, 9999)}",
            warehouse_id=warehouse.id,
            user_id=user.id,
            transaction_type=transaction_type,
            attached_file=None
        )
        db.session.add(transaction)
        db.session.flush()  # Get the transaction ID
        
        # Create 1-5 asset transactions per transaction
        num_asset_transactions = random.randint(1, 5)
        selected_assets = random.sample(assets, min(num_asset_transactions, len(assets)))
        
        for asset in selected_assets:
            # Determine quantity based on transaction type and asset current quantity
            if transaction_type:  # IN transaction
                quantity = random.randint(1, 20)
            else:  # OUT transaction
                # Don't exceed available quantity
                max_qty = min(asset.quantity, 10)
                if max_qty <= 0:
                    continue  # Skip this asset if no quantity available
                quantity = random.randint(1, max_qty)
            
            # Generate realistic amount (price per unit)
            amount = Decimal(str(random.uniform(100, 10000))).quantize(Decimal('0.01'))
            
            # Create asset transaction
            asset_transaction = AssetTransaction(
                transaction_id=transaction.id,
                asset_id=asset.id,
                quantity=quantity,
                amount=amount
            )
            
            # Update asset quantity
            if transaction_type:  # IN
                asset.quantity += quantity
            else:  # OUT
                asset.quantity -= quantity
            
            db.session.add(asset_transaction)
            created_asset_transactions.append(asset_transaction)
        
        created_transactions.append(transaction)
        
        # Commit every 10 transactions to avoid memory issues
        if (i + 1) % 10 == 0:
            db.session.commit()
    
    # Final commit
    db.session.commit()
    
    print(f"✅ Created {len(created_transactions)} transactions")
    print(f"✅ Created {len(created_asset_transactions)} asset transactions")
    return created_transactions, created_asset_transactions

def print_summary(branches, warehouses, categories, assets, users, transactions, asset_transactions):
    """Print a summary of created data"""
    print("\n" + "="*60)
    print("📊 DATA POPULATION SUMMARY")
    print("="*60)
    print(f"🏢 Branches: {len(branches)}")
    print(f"🏭 Warehouses: {len(warehouses)}")
    print(f"📦 Categories: {len(categories)}")
    print(f"💻 Fixed Assets: {len(assets)}")
    print(f"👥 Users: {len(users)}")
    print(f"📋 Transactions: {len(transactions)}")
    print(f"🔄 Asset Transactions: {len(asset_transactions)}")
    print("="*60)
    
    print("\n🔑 Default Login Credentials:")
    print("-" * 40)
    print("Administrator: ahmed.admin@company.com / admin123")
    print("Manager: fatima.manager@company.com / manager123")
    print("Employee: aisha.employee@company.com / employee123")
    print("Viewer: yusuf.viewer@company.com / viewer123")
    print("-" * 40)
    
    # Print some sample data
    print(f"\n📈 Sample Branch: {branches[0].name_en}")
    print(f"📈 Sample Warehouse: {warehouses[0].name_en}")
    print(f"📈 Sample Category: {categories[0].category}")
    print(f"📈 Sample Asset: {assets[0].name_en} (Qty: {assets[0].quantity})")
    
    # Calculate total asset value
    total_value = sum(
        float(at.total_value or 0) 
        for at in asset_transactions 
        if at.total_value
    )
    print(f"💰 Total Asset Transaction Value: ${total_value:,.2f}")

def main():
    """Main function to populate the database"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Starting database population...")
        print("=" * 60)
        
        # Check if database is accessible
        try:
            db.create_all()
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return
        
        # Clear existing data
        clear_existing_data()
        
        # Create data in order (respecting foreign key constraints)
        job_descriptions = create_job_descriptions()
        users = create_users(job_descriptions)
        branches = create_branches()
        warehouses = create_warehouses(branches)
        categories = create_categories()
        assets = create_assets(categories)
        transactions, asset_transactions = create_transactions(warehouses, assets, users)
        
        # Print summary
        print_summary(branches, warehouses, categories, assets, users, transactions, asset_transactions)
        
        print("\n✅ Database population completed successfully!")
        print("🎉 You can now test your application with realistic data.")

if __name__ == "__main__":
    main()