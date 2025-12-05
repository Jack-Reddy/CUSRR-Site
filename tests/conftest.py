"""
configures tests for the app
"""
import pytest
from app import app as flask_app
from website import db, create_app

@pytest.fixture
def app():
    """
    Create and configure a new Flask app instance for testing.

    Sets the app in TESTING mode, uses an in-memory SQLite database,
    and sets up the database schema before yielding the app. Cleans
    up the database after the test is done.
    """
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }
    flask_app = create_app(test_config)
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """
    Return a test client for the Flask app.

    This client can be used to make HTTP requests to the application
    routes during testing.
    """
    return app.test_client()

@pytest.fixture
def runner(app):
    """
    Return a CLI runner for the Flask app.

    Useful for testing custom Flask CLI commands.
    """
    return app.test_cli_runner()
