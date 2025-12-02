import os


class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET') or 'dev_secret_key'

    # Get DATABASE_URL from environment
    DATABASE_URL = os.environ.get('DATABASE_URL')

    # Fix old Heroku-style Postgres URLs
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # Fallback to local SQLite file
    # SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///app.db"

    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
