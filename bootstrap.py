from app import create_app, db
from app.models import JobDescription, User

app = create_app()

with app.app_context():
    # Create tables
    db.create_all()
    
    # Create admin job role
    admin_role = JobDescription(
        name='Admin',
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
    
    # Check if role already exists
    if not JobDescription.query.filter_by(name='Admin').first():
        db.session.add(admin_role)
        db.session.commit()
        print("Admin role created")
    
    # Create admin user
    if not User.query.filter_by(email='admin@example.com').first():
        admin_user = User(
            full_name='Administrator',
            email='admin@example.com',
            role='Admin',
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
        admin_user.set_password('1234')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: admin@example.com / 1234")

    print("Bootstrap complete!")