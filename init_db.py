from app import create_app, db

app = create_app()

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()

    print("Database initialized successfully!")
