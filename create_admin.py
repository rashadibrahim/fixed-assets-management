from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    email = "ahmed@gmail.com"
    password = "1234"
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    
    if existing_user:
        print(f"User with email {email} already exists.")
        existing_user.set_password(password)
        db.session.commit()
        print(f"Password updated for {email}.")
    else:
        new_user = User(
            full_name="Admin User",
            email=email,
            role="Admin",
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
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        print(f"User {email} created successfully.")
