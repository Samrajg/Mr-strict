from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Register blueprints
    from app.routes.dashboard import dashboard_bp
    from app.routes.rubrics import rubrics_bp
    from app.routes.grading import grading_bp
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rubrics_bp)
    app.register_blueprint(grading_bp)

    with app.app_context():
        db.create_all()

    return app
