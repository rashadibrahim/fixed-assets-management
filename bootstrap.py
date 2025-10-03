from app import create_app, db
from app.models import User, JobDescription, Branch, Warehouse, Category, FixedAsset, Transaction, AssetTransaction
from datetime import date, datetime
import sys

app = create_app()

with app.app_context():
    try:
        print("🚀 Starting bootstrap process...")
        
        # Create job roles first
        print("\n📋 Creating job roles...")
        
        # Admin role with full permissions
        admin_role = JobDescription(
            name="admin",
            can_read_branch=True,
            can_edit_branch=True,
            can_delete_branch=True,
            can_read_warehouse=True,
            can_edit_warehouse=True,
            can_delete_warehouse=True,
            can_read_asset=True,
            can_edit_asset=True,
            can_delete_asset=True,
            can_print_barcode=True,
            can_make_report=True,
            can_make_transaction=True
        )
        
        # Manager role with most permissions
        manager_role = JobDescription(
            name="manager",
            can_read_branch=True,
            can_edit_branch=True,
            can_delete_branch=False,
            can_read_warehouse=True,
            can_edit_warehouse=True,
            can_delete_warehouse=False,
            can_read_asset=True,
            can_edit_asset=True,
            can_delete_asset=False,
            can_print_barcode=True,
            can_make_report=True,
            can_make_transaction=True
        )
        
        # Employee role with limited permissions
        employee_role = JobDescription(
            name="employee",
            can_read_branch=True,
            can_edit_branch=False,
            can_delete_branch=False,
            can_read_warehouse=True,
            can_edit_warehouse=False,
            can_delete_warehouse=False,
            can_read_asset=True,
            can_edit_asset=False,
            can_delete_asset=False,
            can_print_barcode=True,
            can_make_report=False,
            can_make_transaction=True
        )
        
        # Viewer role with read-only permissions
        viewer_role = JobDescription(
            name="viewer",
            can_read_branch=True,
            can_edit_branch=False,
            can_delete_branch=False,
            can_read_warehouse=True,
            can_edit_warehouse=False,
            can_delete_warehouse=False,
            can_read_asset=True,
            can_edit_asset=False,
            can_delete_asset=False,
            can_print_barcode=False,
            can_make_report=True,
            can_make_transaction=False
        )
        
        job_roles = [admin_role, manager_role, employee_role, viewer_role]
        
        for role in job_roles:
            existing_role = db.session.query(JobDescription).filter_by(name=role.name).first()
            if not existing_role:
                db.session.add(role)
                print(f"  ✅ Created job role: {role.name}")
            else:
                print(f"  ✅ Job role already exists: {role.name}")
        
        db.session.commit()
        
        # Create users
        print("\n👥 Creating users...")
        
        users_data = [
            {
                "full_name": "System Administrator",
                "email": "admin@example.com",
                "password": "admin",
                "role": "admin"
            },
            {
                "full_name": "Branch Manager",
                "email": "manager@example.com", 
                "password": "manager123",
                "role": "manager"
            },
            {
                "full_name": "Warehouse Employee",
                "email": "employee@example.com",
                "password": "employee123",
                "role": "employee"
            },
            {
                "full_name": "Report Viewer",
                "email": "viewer@example.com",
                "password": "viewer123",
                "role": "viewer"
            }
        ]
        
        for user_data in users_data:
            existing_user = db.session.query(User).filter_by(email=user_data["email"]).first()
            if not existing_user:
                # Get job role permissions
                role = db.session.query(JobDescription).filter_by(name=user_data["role"]).first()
                
                user = User(
                    full_name=user_data["full_name"],
                    email=user_data["email"],
                    role=user_data["role"],
                    can_read_branch=role.can_read_branch,
                    can_edit_branch=role.can_edit_branch,
                    can_delete_branch=role.can_delete_branch,
                    can_read_warehouse=role.can_read_warehouse,
                    can_edit_warehouse=role.can_edit_warehouse,
                    can_delete_warehouse=role.can_delete_warehouse,
                    can_read_asset=role.can_read_asset,
                    can_edit_asset=role.can_edit_asset,
                    can_delete_asset=role.can_delete_asset,
                    can_print_barcode=role.can_print_barcode,
                    can_make_report=role.can_make_report,
                    can_make_transaction=role.can_make_transaction
                )
                user.set_password(user_data["password"])
                
                db.session.add(user)
                print(f"  ✅ Created user: {user_data['full_name']} ({user_data['email']})")
            else:
                print(f"  ✅ User already exists: {user_data['email']}")
        
        db.session.commit()
        
        # Create branches
        print("\n🏢 Creating branches...")
        
        branches_data = [
            {
                "name_ar": "الفرع الرئيسي",
                "name_en": "Main Branch",
                "address_ar": "الرياض، المملكة العربية السعودية",
                "address_en": "Riyadh, Saudi Arabia"
            },
            {
                "name_ar": "فرع جدة",
                "name_en": "Jeddah Branch", 
                "address_ar": "جدة، المملكة العربية السعودية",
                "address_en": "Jeddah, Saudi Arabia"
            },
            {
                "name_ar": "فرع الدمام",
                "name_en": "Dammam Branch",
                "address_ar": "الدمام، المملكة العربية السعودية", 
                "address_en": "Dammam, Saudi Arabia"
            }
        ]
        
        created_branches = []
        for branch_data in branches_data:
            existing_branch = db.session.query(Branch).filter_by(name_en=branch_data["name_en"]).first()
            if not existing_branch:
                branch = Branch(**branch_data)
                db.session.add(branch)
                created_branches.append(branch)
                print(f"  ✅ Created branch: {branch_data['name_en']}")
            else:
                created_branches.append(existing_branch)
                print(f"  ✅ Branch already exists: {branch_data['name_en']}")
        
        db.session.commit()
        
        # Create warehouses
        print("\n🏭 Creating warehouses...")
        
        warehouses_data = [
            {
                "branch_id": 1,
                "name_ar": "المستودع الرئيسي",
                "name_en": "Main Warehouse",
                "address_ar": "المستودع الرئيسي - الرياض",
                "address_en": "Main Warehouse - Riyadh"
            },
            {
                "branch_id": 1,
                "name_ar": "مستودع الأجهزة",
                "name_en": "Equipment Warehouse",
                "address_ar": "مستودع الأجهزة - الرياض",
                "address_en": "Equipment Warehouse - Riyadh"
            },
            {
                "branch_id": 2,
                "name_ar": "مستودع جدة",
                "name_en": "Jeddah Warehouse",
                "address_ar": "المستودع الرئيسي - جدة",
                "address_en": "Main Warehouse - Jeddah"
            },
            {
                "branch_id": 3,
                "name_ar": "مستودع الدمام",
                "name_en": "Dammam Warehouse",
                "address_ar": "المستودع الرئيسي - الدمام",
                "address_en": "Main Warehouse - Dammam"
            }
        ]
        
        for warehouse_data in warehouses_data:
            existing_warehouse = db.session.query(Warehouse).filter_by(
                name_en=warehouse_data["name_en"],
                branch_id=warehouse_data["branch_id"]
            ).first()
            if not existing_warehouse:
                warehouse = Warehouse(**warehouse_data)
                db.session.add(warehouse)
                print(f"  ✅ Created warehouse: {warehouse_data['name_en']}")
            else:
                print(f"  ✅ Warehouse already exists: {warehouse_data['name_en']}")
        
        db.session.commit()
        
        # Create categories
        print("\n� Creating categories...")
        
        categories_data = [
            {"category": "Computer Equipment", "subcategory": "Laptops"},
            {"category": "Computer Equipment", "subcategory": "Desktop PCs"},
            {"category": "Computer Equipment", "subcategory": "Servers"},
            {"category": "Computer Equipment", "subcategory": "Network Equipment"},
            {"category": "Office Furniture", "subcategory": "Desks"},
            {"category": "Office Furniture", "subcategory": "Chairs"},
            {"category": "Office Furniture", "subcategory": "Cabinets"},
            {"category": "Vehicles", "subcategory": "Cars"},
            {"category": "Vehicles", "subcategory": "Trucks"},
            {"category": "Tools & Equipment", "subcategory": "Power Tools"},
            {"category": "Tools & Equipment", "subcategory": "Hand Tools"},
            {"category": "Electronics", "subcategory": "Printers"},
            {"category": "Electronics", "subcategory": "Phones"},
            {"category": "Electronics", "subcategory": "Projectors"}
        ]
        
        for category_data in categories_data:
            existing_category = db.session.query(Category).filter_by(
                category=category_data["category"],
                subcategory=category_data["subcategory"]
            ).first()
            if not existing_category:
                category = Category(**category_data)
                db.session.add(category)
                print(f"  ✅ Created category: {category_data['category']} - {category_data['subcategory']}")
            else:
                print(f"  ✅ Category already exists: {category_data['category']} - {category_data['subcategory']}")
        
        db.session.commit()
        
        # Create fixed assets
        print("\n� Creating fixed assets...")
        
        assets_data = [
            {
                "name_ar": "لابتوب ديل",
                "name_en": "Dell Laptop",
                "quantity": 10,
                "product_code": "DELL-LP-001",
                "category_id": 1,  # Laptops
                "is_active": True
            },
            {
                "name_ar": "جهاز كمبيوتر مكتبي HP",
                "name_en": "HP Desktop PC",
                "quantity": 15,
                "product_code": "HP-PC-001",
                "category_id": 2,  # Desktop PCs
                "is_active": True
            },
            {
                "name_ar": "خادم IBM",
                "name_en": "IBM Server",
                "quantity": 2,
                "product_code": "IBM-SRV-001",
                "category_id": 3,  # Servers
                "is_active": True
            },
            {
                "name_ar": "مكتب خشبي",
                "name_en": "Wooden Desk",
                "quantity": 25,
                "product_code": "DESK-WD-001",
                "category_id": 5,  # Desks
                "is_active": True
            },
            {
                "name_ar": "كرسي مكتب",
                "name_en": "Office Chair",
                "quantity": 30,
                "product_code": "CHR-OFF-001",
                "category_id": 6,  # Chairs
                "is_active": True
            },
            {
                "name_ar": "طابعة كانون",
                "name_en": "Canon Printer",
                "quantity": 8,
                "product_code": "CAN-PRT-001",
                "category_id": 12,  # Printers
                "is_active": True
            },
            {
                "name_ar": "جهاز عرض إبسون",
                "name_en": "Epson Projector",
                "quantity": 5,
                "product_code": "EPS-PRJ-001",
                "category_id": 14,  # Projectors
                "is_active": True
            },
            {
                "name_ar": "سيارة تويوتا كامري",
                "name_en": "Toyota Camry",
                "quantity": 3,
                "product_code": "TOY-CAM-001",
                "category_id": 8,  # Cars
                "is_active": True
            }
        ]
        
        for asset_data in assets_data:
            existing_asset = db.session.query(FixedAsset).filter_by(product_code=asset_data["product_code"]).first()
            if not existing_asset:
                asset = FixedAsset(**asset_data)
                db.session.add(asset)
                print(f"  ✅ Created asset: {asset_data['name_en']} ({asset_data['product_code']})")
            else:
                print(f"  ✅ Asset already exists: {asset_data['product_code']}")
        
        db.session.commit()
        
        print("\n🎉 Bootstrap completed successfully!")
        print("\n📋 Summary:")
        print("👥 Users created:")
        print("  📧 admin@example.com (password: admin)")
        print("  📧 manager@example.com (password: manager123)")
        print("  📧 employee@example.com (password: employee123)")
        print("  📧 viewer@example.com (password: viewer123)")
        print("\n🏢 Branches: 3 branches created")
        print("🏭 Warehouses: 4 warehouses created")
        print("📂 Categories: 14 categories created")
        print("💻 Assets: 8 sample assets created")
        print("\n⚠️  Please change default passwords after first login!")
            
    except Exception as e:
        print(f"❌ Error during bootstrap: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        sys.exit(1)

