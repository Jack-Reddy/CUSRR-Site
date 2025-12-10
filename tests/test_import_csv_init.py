# pylint: disable=unused-argument
"""Tests for create app csv import functionality."""
import io
import pytest
from website.models import User, db
import website


@pytest.fixture
def organizer_user(app):
    """User with organizer role."""
    with app.app_context():
        user = User(
            firstname="Org",
            lastname="User",
            email="organizer@example.com",
            activity="active",
            auth="organizer",
        )
        db.session.add(user)
        db.session.commit()
        yield user


def test_import_users_from_csv(client, organizer_user):
    """POST /import_csv should import users from a CSV file."""

    with client.session_transaction() as sess:
        sess["user"] = {
            "email": organizer_user.email,
            "name": "Organizer",
        }

    csv_content = """firstname,lastname,email,auth
    John,Doe,johndoe@gmail.com,presenter"""
    data = {
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'users.csv')
    }

    response = client.post(
        '/import_csv',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True)

    assert response.status_code == 200
    assert b"Successfully imported 1 users!" in response.data

    with client.application.app_context():
        user = User.query.filter_by(email="johndoe@gmail.com").first()
        assert user is not None
        assert user.firstname == "John"
        assert user.lastname == "Doe"
        assert user.auth == "presenter"


def test_import_users_from_csv_missing_columns(client, organizer_user):
    """POST /import_csv with missing columns should show an error."""

    with client.session_transaction() as sess:
        sess["user"] = {
            "email": organizer_user.email,
            "name": "Organizer",
        }

    csv_content = """firstname,lastname
    John,Doe"""
    data = {
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'users.csv')
    }

    response = client.post(
        '/import_csv',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True)

    assert response.status_code == 200
    assert b"Missing required CSV columns" in response.data


def test_import_users_from_csv_invalid_data(client, organizer_user):
    """POST /import_csv with invalid data should skip bad rows."""

    with client.session_transaction() as sess:
        sess["user"] = {
            "email": organizer_user.email,
            "name": "Organizer",
        }

    csv_content = """firstname,lastname,email,auth
    John,Doe,invalidemail,presenter
    ,Smith,,"""

    data = {
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'users.csv')
    }
    response = client.post(
        '/import_csv',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid or missing data on rows" in response.data


def test_import_users_from_csv_duplicate_emails(client, organizer_user):
    """POST /import_csv with duplicate emails should skip duplicates."""

    with client.session_transaction() as sess:
        sess["user"] = {
            "email": organizer_user.email,
            "name": "Organizer",
        }

    # Pre-add a user to create a duplicate scenario
    with client.application.app_context():
        existing_user = User(
            firstname="Jane",
            lastname="Doe",
            email="janedoe@gmail.com",
            auth="presenter"
        )
        db.session.add(existing_user)
        db.session.commit()
    csv_content = """firstname,lastname,email,auth
    Jane,Doe,janedoe@gmail.com,presenter"""

    data = {
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'users.csv')
    }
    response = client.post(
        '/import_csv',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True)
    assert response.status_code == 200
    assert b"Duplicate emails found on rows" in response.data


def test_import_users_from_csv_no_file(client, organizer_user):
    """POST /import_csv with no file should show an error."""

    with client.session_transaction() as sess:
        sess["user"] = {
            "email": organizer_user.email,
            "name": "Organizer",
        }

    data = {}
    response = client.post(
        '/import_csv',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True)

    assert response.status_code == 200
    assert b"No file selected." in response.data


def test_import_users_from_csv_wrong_file_type(client, organizer_user):
    """POST /import_csv with wrong file type should show an error."""

    with client.session_transaction() as sess:
        sess["user"] = {
            "email": organizer_user.email,
            "name": "Organizer",
        }

    data = {
        'csv_file': (io.BytesIO(b"Not a CSV content"), 'users.txt')
    }
    response = client.post(
        '/import_csv',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True)

    assert response.status_code == 200
    assert b"File must be a CSV." in response.data


def test_import_users_from_csv_unauthorized(client):
    """POST /import_csv without organizer role should redirect to login."""

    data = {
        'csv_file': (
            io.BytesIO(b"firstname,lastname,email,auth\nJohn,Doe,johndoe@gmail.com,presenter"),
            'users.csv')}
    response = client.post(
        '/import_csv',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=False)
    assert response.status_code == 302
    assert "/google/login" in response.headers["Location"]
