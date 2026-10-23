import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    env = app.config.get('ENV') or os.environ.get('FLASK_ENV', 'development')
    secret_key = app.config.get('SECRET_KEY')
    if env == 'production' and (not secret_key or secret_key.startswith('super-secret')):
        raise ValueError("CRITICAL SECURITY ERROR: A secure, unique SECRET_KEY must be configured in production environment!")

    db.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.workspaces import workspace_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.rubrics import rubrics_bp
    from app.routes.grading import grading_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(workspace_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rubrics_bp)
    app.register_blueprint(grading_bp)

    from flask import render_template, flash, redirect, url_for
    from werkzeug.exceptions import RequestEntityTooLarge

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        flash('Upload failed: File payload exceeds maximum permitted upload limit.', 'error')
        return redirect(url_for('grading.evaluate')), 413

    with app.app_context():
        db.create_all()

    return app
