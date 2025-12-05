# pylint: disable=redefined-outer-name
"""
configures tests for the app
"""
import pytest

@pytest.fixture
def app():
    """Create a new Flask app instance for testing."""
    from website import db, create_app
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }
    app_instance = create_app(test_config)

    with app_instance.app_context():
        db.create_all()
        yield app_instance
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
