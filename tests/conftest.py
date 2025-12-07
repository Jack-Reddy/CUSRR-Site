# pylint: disable=redefined-outer-name
"""
configures tests for the app
"""
#Basic Imports
from datetime import datetime, timedelta

# Third Part Imports
import pytest

# Local
from website.models import User, BlockSchedule, Presentation, Grade, AbstractGrade
from website import db, create_app

@pytest.fixture
def app():
    """Create a new Flask app instance for testing."""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key'
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

@pytest.fixture
def sample_average_fixture(sample_presentation_fixture):
    """Creates a simple object mimicking average grade results."""
    class Avg:
        """average class for testing"""
        def __init__(self, presentation_id, average_score, num_grades):
            self.presentation_id = presentation_id
            self.average_score = average_score
            self.num_grades = num_grades

    avg = Avg(
        presentation_id=sample_presentation_fixture.id,
        average_score=4.5678,
        num_grades=3
    )
    yield [avg]

@pytest.fixture
def sample_grade_fixture(app, sample_user_fixture, sample_presentation_fixture):
    """Creates a sample Grade for testing."""
    with app.app_context():
        grade = Grade(
            user_id=sample_user_fixture.id,
            presentation_id=sample_presentation_fixture.id,
            criteria_1=4,
            criteria_2=3,
            criteria_3=5
        )
        db.session.add(grade)
        db.session.commit()
        yield grade


@pytest.fixture
def multiple_grades_fixture(app, sample_user_fixture, sample_presentation_fixture):
    """Creates multiple grades for testing averages."""
    with app.app_context():
        grades = []
        for i in range(3):
            grade = Grade(
                user_id=sample_user_fixture.id,
                presentation_id=sample_presentation_fixture.id,
                criteria_1=3+i,
                criteria_2=4,
                criteria_3=5
            )
            db.session.add(grade)
            grades.append(grade)
        db.session.commit()
        yield grades


@pytest.fixture
def sample_abstract_grade_fixture(app, sample_user_fixture, sample_presentation_fixture):
    """Creates a single abstract grade for testing."""
    with app.app_context():
        grade = AbstractGrade(
            user_id=sample_user_fixture.id,
            presentation_id=sample_presentation_fixture.id,
            criteria_1=4,
            criteria_2=3,
            criteria_3=5
        )
        db.session.add(grade)
        db.session.commit()
        yield grade


@pytest.fixture
def multiple_abstract_grades_fixture(app, sample_user_fixture, sample_presentation_fixture):
    """Creates multiple abstract grades for testing averages."""
    with app.app_context():
        grades = []
        for i in range(3):
            grade = AbstractGrade(
                user_id=sample_user_fixture.id,
                presentation_id=sample_presentation_fixture.id,
                criteria_1=3+i,
                criteria_2=4,
                criteria_3=5
            )
            db.session.add(grade)
            grades.append(grade)
        db.session.commit()
        yield grades

@pytest.fixture
def sample_block_fixture(app):
    """Insert a sample block schedule into the database for testing."""
    with app.app_context():
        start = datetime.now() + timedelta(hours=1)
        end = start + timedelta(hours=1)
        block = BlockSchedule(
            day="Day 1",
            start_time=start,
            end_time=end,
            title="Sample Block",
            description="A test block schedule",
            location="Room A",
            block_type="poster",
            sub_length=15
        )
        db.session.add(block)
        db.session.commit()
        yield block
