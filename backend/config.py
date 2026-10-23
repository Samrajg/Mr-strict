import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
# Check for .env in project root first, fallback to parent directory
if os.path.exists(os.path.join(basedir, '.env')):
    load_dotenv(os.path.join(basedir, '.env'))
else:
    load_dotenv(os.path.join(basedir, '../.env'))

class Config:
    ENV = os.environ.get('FLASK_ENV', 'development')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if ENV == 'production':
            raise ValueError("CRITICAL SECURITY ERROR: SECRET_KEY must be set in production environment!")
        SECRET_KEY = 'super-secret-dev-key-change-in-production'
        
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Request & Upload limits (Default: 32MB max per request)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 32 * 1024 * 1024))
    
    # Session cookie security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1')
    
    # Local-first storage directories
    DATA_DIR = os.environ.get('DATA_DIR') or os.path.join(basedir, 'MrStrictData')
    WORKSPACES_DIR = os.path.join(DATA_DIR, 'workspaces')
