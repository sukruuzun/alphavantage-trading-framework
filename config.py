import os
from urllib.parse import urlparse

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///trading_dashboard.db'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Handle Railway/Heroku PostgreSQL URL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Fallback to development SQLite if no DATABASE_URL (for local testing)
        import warnings
        warnings.warn("DATABASE_URL not found in production config, falling back to SQLite")
        SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/trading_dashboard.db'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 