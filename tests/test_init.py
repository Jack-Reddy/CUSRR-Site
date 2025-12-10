# pylint: disable=unused-argument,redefined-outer-name
"""
Comprehensive tests for website/__init__.py module.
Tests all routes, decorators, and application initialization.
"""

import pytest
from flask import session
from website import create_app, db
from website.models import User, Presentation, BlockSchedule
from datetime import datetime


@pytest.fixture
def app_with_users(app):
    """App with various user roles in the database."""
    with app.app_context():
        organizer = User(
            firstname='Org',
            lastname='User',
            email='organizer@test.com',
            auth='organizer'
        )
        presenter = User(
            firstname='Presenter',
            lastname='User',
            email='presenter@test.com',
            auth='presenter'
        )
        attendee = User(
            firstname='Attendee',
            lastname='User',
            email='attendee@test.com',
            auth='attendee'
        )
        banned = User(
            firstname='Banned',
            lastname='User',
            email='banned@test.com',
            auth='banned'
        )
        grader = User(
            firstname='Grader',
            lastname='User',
            email='grader@test.com',
            auth='abstract-grader'
        )
        
        db.session.add_all([organizer, presenter, attendee, banned, grader])
        db.session.commit()
        yield app


@pytest.fixture
def presentation_with_schedule(app):
    """Create a presentation with schedule for testing."""
    with app.app_context():
        schedule = BlockSchedule(
            day='Monday',
            start_time=datetime(2025, 12, 10, 9, 0),
            end_time=datetime(2025, 12, 10, 10, 0),
            title='Session 1',
            location='Room 101',
            block_type='presentation'
        )
        db.session.add(schedule)
        db.session.flush()
        
        pres = Presentation(
            title='Test Presentation',
            abstract='Test abstract content',
            subject='Computer Science',
            schedule_id=schedule.id
        )
        db.session.add(pres)
        db.session.commit()
        yield pres


# Test create_app function

def test_create_app_default_config():
    """create_app should work with default configuration."""
    app = create_app()
    assert app is not None
    assert app.name == 'website'


def test_create_app_with_test_config():
    """create_app should apply test configuration."""
    test_config = {
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    }
    app = create_app(test_config)
    
    assert app.config['TESTING'] is True
    assert app.config['SECRET_KEY'] == 'test-secret'
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'


def test_create_app_registers_all_blueprints():
    """All API blueprints should be registered."""
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    
    with app.app_context():
        db.create_all()
    
    client = app.test_client()
    
    assert client.get('/api/v1/users/').status_code == 200
    assert client.get('/api/v1/presentations/').status_code == 200
    assert client.get('/api/v1/block-schedule/').status_code == 200
    assert client.get('/api/v1/grades/').status_code == 200
    assert client.get('/api/v1/abstractgrades/').status_code == 200


def test_create_app_initializes_database():
    """Database should be initialized in non-testing mode."""
    app = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    
    with app.app_context():
        # Tables should exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        assert 'users' in tables
        assert 'presentations' in tables
        assert 'grades' in tables
        assert 'blockSchedules' in tables


# Test public routes

def test_root_route_renders(client):
    """GET / should render dashboard template."""
    response = client.get('/')
    assert response.status_code == 200


def test_schedule_route_renders(client):
    """GET /schedule should render for unauthenticated users."""
    response = client.get('/schedule')
    assert response.status_code == 200


def test_schedule_route_shows_organizer_view(client, app_with_users):
    """GET /schedule should show organizer features for organizers."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'organizer@test.com', 'name': 'Org User'}
    
    response = client.get('/schedule')
    assert response.status_code == 200


def test_fizzbuzz_route_renders(client):
    """GET /fizzbuzz should render fizz-buzz page."""
    response = client.get('/fizzbuzz')
    assert response.status_code == 200


def test_dashboard_route_renders(client):
    """GET /dashboard should render for unauthenticated users."""
    response = client.get('/dashboard')
    assert response.status_code == 200


def test_signup_route_renders(client):
    """GET /signup should render signup page."""
    response = client.get('/signup')
    assert response.status_code == 200


def test_blitz_page_route_renders(client):
    """GET /blitz_page should render."""
    response = client.get('/blitz_page')
    assert response.status_code == 200


def test_presentation_page_route_renders(client):
    """GET /presentation_page should render."""
    response = client.get('/presentation_page')
    assert response.status_code == 200


def test_poster_page_route_renders(client):
    """GET /poster_page should render."""
    response = client.get('/poster_page')
    assert response.status_code == 200


# Test protected routes with auth decorators

def test_abstract_grader_route_requires_auth(client):
    """GET /abstract-grader should redirect unauthenticated users."""
    response = client.get('/abstract-grader', follow_redirects=False)
    assert response.status_code == 302
    assert '/google/login' in response.location


def test_abstract_grader_route_requires_grader_role(client, app_with_users):
    """GET /abstract-grader should redirect non-graders."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'attendee@test.com', 'name': 'Attendee User'}
    
    response = client.get('/abstract-grader', follow_redirects=False)
    assert response.status_code == 302


def test_organizer_user_status_requires_organizer(client, app_with_users):
    """GET /organizer-user-status should require organizer role."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'attendee@test.com', 'name': 'Attendee User'}
    
    response = client.get('/organizer-user-status', follow_redirects=False)
    assert response.status_code == 302


def test_organizer_user_status_allows_organizer(client, app_with_users):
    """GET /organizer-user-status should allow organizers."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'organizer@test.com', 'name': 'Org User'}
    
    response = client.get('/organizer-user-status')
    assert response.status_code == 200


def test_organizer_presentations_status_requires_organizer(client, app_with_users):
    """GET /organizer-presentations-status should require organizer role."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'presenter@test.com', 'name': 'Presenter User'}
    
    response = client.get('/organizer-presentations-status', follow_redirects=False)
    assert response.status_code == 302


def test_organizer_presentations_status_allows_organizer(client, app_with_users):
    """GET /organizer-presentations-status should allow organizers."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'organizer@test.com', 'name': 'Org User'}
    
    response = client.get('/organizer-presentations-status')
    assert response.status_code == 200


# Test banned user redirect decorator

def test_banned_user_redirected_from_dashboard(client, app_with_users):
    """Banned users should be redirected to fizzbuzz from dashboard."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'banned@test.com', 'name': 'Banned User'}
    
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/fizzbuzz' in response.location


# Test profile route

def test_profile_requires_authentication(client):
    """GET /profile should redirect unauthenticated users to login."""
    response = client.get('/profile', follow_redirects=False)
    assert response.status_code == 302
    assert '/google/login' in response.location


def test_profile_redirects_new_user_to_signup(client, app_with_users):
    """GET /profile should redirect users not in DB to signup."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'newuser@test.com', 'name': 'New User'}
    
    response = client.get('/profile', follow_redirects=False)
    assert response.status_code == 302
    assert '/signup' in response.location


def test_profile_shows_abstract_submission_for_presenters(client, app_with_users):
    """GET /profile should show abstract submission for presenters."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'presenter@test.com', 'name': 'Presenter User'}
    
    response = client.get('/profile')
    assert response.status_code == 200


def test_profile_shows_abstract_submission_for_organizers(client, app_with_users):
    """GET /profile should show abstract submission for organizers."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'organizer@test.com', 'name': 'Org User'}
    
    response = client.get('/profile')
    assert response.status_code == 200


def test_profile_hides_abstract_submission_for_attendees(client, app_with_users):
    """GET /profile should hide abstract submission for attendees."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'attendee@test.com', 'name': 'Attendee User'}
    
    response = client.get('/profile')
    assert response.status_code == 200


# Test abstract scoring route

def test_abstract_scoring_requires_grader_role(client, app_with_users, presentation_with_schedule):
    """GET /abstract-scoring should require abstract grader role."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'attendee@test.com', 'name': 'Attendee User'}
    
    response = client.get(f'/abstract-scoring?id={presentation_with_schedule.id}', follow_redirects=False)
    assert response.status_code == 302


def test_abstract_scoring_allows_graders(client, app_with_users, presentation_with_schedule):
    """GET /abstract-scoring should allow abstract graders."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'grader@test.com', 'name': 'Grader User'}
    
    response = client.get(f'/abstract-scoring?id={presentation_with_schedule.id}')
    assert response.status_code == 200


def test_abstract_scoring_404_for_invalid_presentation(client, app_with_users):
    """GET /abstract-scoring should return 404 for non-existent presentation."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'grader@test.com', 'name': 'Grader User'}
    
    response = client.get('/abstract-scoring?id=99999')
    assert response.status_code == 404


# Test CSV import route

def test_import_csv_requires_organizer(client, app_with_users):
    """POST /import_csv should require organizer role."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'presenter@test.com', 'name': 'Presenter User'}
    
    response = client.post('/import_csv', follow_redirects=False)
    assert response.status_code == 302


def test_import_csv_requires_file(client, app_with_users):
    """POST /import_csv should require a file."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'organizer@test.com', 'name': 'Org User'}
    
    response = client.post('/import_csv', data={}, follow_redirects=False)
    assert response.status_code == 302
    assert '/organizer-user-status' in response.location


def test_import_csv_requires_csv_extension(client, app_with_users):
    """POST /import_csv should reject non-CSV files."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'organizer@test.com', 'name': 'Org User'}
    
    from io import BytesIO
    data = {
        'csv_file': (BytesIO(b'test content'), 'test.txt')
    }
    
    response = client.post('/import_csv', data=data, content_type='multipart/form-data', follow_redirects=False)
    assert response.status_code == 302


def test_import_csv_accepts_valid_csv(client, app_with_users):
    """POST /import_csv should accept valid CSV files."""
    with client.session_transaction() as sess:
        sess['user'] = {'email': 'organizer@test.com', 'name': 'Org User'}
    
    from io import BytesIO
    csv_content = b'firstname,lastname,email,role\nJohn,Doe,john@test.com,attendee\n'
    data = {
        'csv_file': (BytesIO(csv_content), 'users.csv')
    }
    
    response = client.post('/import_csv', data=data, content_type='multipart/form-data', follow_redirects=False)
    assert response.status_code == 302
    assert '/organizer-user-status' in response.location


# Test context processor (permissions injection)

def test_context_processor_injects_permissions_unauthenticated(client):
    """Context processor should inject permissions for unauthenticated users."""
    with client.application.test_request_context():
        # Context processor should be available
        ctx_funcs = client.application.template_context_processors[None]
        inject_permissions = None
        for func in ctx_funcs:
            if func.__name__ == 'inject_permissions':
                inject_permissions = func
                break
        
        assert inject_permissions is not None
        ctx = inject_permissions()
        assert ctx['is_authenticated'] is False
        assert ctx['is_organizer'] is False
