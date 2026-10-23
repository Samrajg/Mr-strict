import sys
from app import create_app, db

app = create_app()

with app.app_context():
    if '--reset-dangerously' in sys.argv:
        print("WARNING: Dropping all database tables...")
        db.drop_all()
        db.create_all()
        print("Database schema reset successfully!")
    else:
        # Non-destructive: create tables if they do not exist
        db.create_all()
        print("Database tables verified / created non-destructively.")
