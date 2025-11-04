import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask core settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_secret_key'

    # SQLAlchemy database URI (here we use SQLite by default)
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(basedir, 'app.db')}"
    )

    # Turn off SQLAlchemy event notifications (saves memory)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Optional: Enable debugging logs for SQL (can help during dev)
    SQLALCHEMY_ECHO = False
