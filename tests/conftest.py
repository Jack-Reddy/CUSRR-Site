# pylint: disable=redefined-outer-name
"""
configures tests for the app
"""
#Basic Imports
from datetime import datetime, timedelta

# Third Part Imports
import pytest

# Local
from website.models import User, BlockSchedule, Presentation
from website import db, create_app

@pytest.fixture
def app():
    """Create a new Flask app instance for testing."""
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


@pytest.fixture
def sample_user_fixture(app):
    """Insert a sample user into the database for testing."""
    with app.app_context():
        user = User(
            firstname="Jane",
            lastname="Doe",
            email="jane@example.com",
            activity="active",
            presentation_id=None,
            auth="admin,judge"
        )
        db.session.add(user)
        db.session.commit()
        yield user

@pytest.fixture
def sample_block_fixture(app):
    """Create a valid BlockSchedule for testing."""

    with app.app_context():
        start = datetime.now() + timedelta(hours=1)
        end = start + timedelta(minutes=60)

        block = BlockSchedule(
            day="Day 1",
            start_time=start,
            end_time=end,
            title="Poster Session A",
            description="Test poster block",
            location="Room A",
            block_type="poster",
            sub_length=10
        )

        db.session.add(block)
        db.session.commit()
        yield block


@pytest.fixture
def sample_presentation_fixture(app, sample_block_fixture):
    """Create a Presentation for basic testing."""
    with app.app_context():
        sample_presentation = Presentation(
            title="Test Presentation",
            abstract="A test abstract",
            subject="Testing",
            time=datetime.now(),
            schedule_id=sample_block_fixture.id
        )
        db.session.add(sample_presentation)
        db.session.commit()
        yield sample_presentation
