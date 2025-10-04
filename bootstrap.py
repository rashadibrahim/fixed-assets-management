from app import create_app, db
from app.models import User, JobDescription
import sys

app = create_app()

with app.app_context():
    try:
        # Create admin job role first
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
        
        # Check if admin role already exists
        existing_admin_role = db.session.query(JobDescription).filter_by(name="admin").first()
        if not existing_admin_role:
            db.session.add(admin_role)
            db.session.commit()
            print("✅ Admin job role created")
        else:
            admin_role = existing_admin_role
            print("✅ Admin job role already exists")
        
        # Create initial admin user
        existing_admin = db.session.query(User).filter_by(email="admin@example.com").first()
        if not existing_admin:
            admin_user = User(
                full_name="System Administrator",
                email="admin@example.com",
                role="admin",
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
            admin_user.set_password("admin")  
            
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created successfully")
            print("📧 Email: admin@example.com")
            print("🔑 Password: admin")
            print("⚠️  Please change the password after first login!")
        else:
            print("✅ Admin user already exists")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

