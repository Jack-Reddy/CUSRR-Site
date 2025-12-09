# pylint: disable=duplicate-code,unused-argument
"""
Tests for authentication and role-based authorization
(endpoints in website.__init__ and decorators in website.auth).
"""

from flask import session
import pytest

from website import db
from website.models import User


# role-specific user tests

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


@pytest.fixture
def abstract_grader_user(app):
    """User with abstract-grader role."""
    with app.app_context():
        user = User(
            firstname="Abstract",
            lastname="Grader",
            email="abstract_grader@example.com",
            activity="active",
            auth="abstract-grader",
        )
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture
def banned_user(app):
    """User with banned role."""
    with app.app_context():
        user = User(
            firstname="Banned",
            lastname="User",
            email="banned@example.com",
            activity="inactive",
            auth="banned",
        )
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture
def attendee_user(app):
    """Normal attendee (no special roles)."""
    with app.app_context():
        user = User(
            firstname="Attendee",
            lastname="User",
            email="attendee@example.com",
            activity="active",
            auth="attendee",
        )
        db.session.add(user)
        db.session.commit()
        yield user


#  /me endpoint tests 

def test_me_unauthenticated_returns_401(client):
    """GET /me with no session should report unauthenticated with 401."""
    res = client.get("/me")
    assert res.status_code == 401
    data = res.get_json()
    assert data == {"authenticated": False}


def test_me_authenticated_no_db_user(client):
    """
    GET /me with a Google session but no matching DB user:
    - authenticated=True
    - account_exists=False
    - user_id/auth/etc are None
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": "nouser@example.com",
            "name": "No DB User",
            "picture": "http://example.com/avatar.png",
        }

    res = client.get("/me")
    assert res.status_code == 200
    data = res.get_json()

    assert data["authenticated"] is True
    assert data["email"] == "nouser@example.com"
    assert data["account_exists"] is False
    assert data["user_id"] is None
    assert data["auth"] is None
    assert data["presentation_id"] is None
    assert data["activity"] is None


def test_me_authenticated_existing_user(client, sample_user_fixture):
    """
    GET /me with a Google session and matching DB user:
    - authenticated=True
    - account_exists=True
    - DB fields (auth/activity/presentation_id) are returned
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": sample_user_fixture.email,
            "name": f"{sample_user_fixture.firstname} {sample_user_fixture.lastname}",
            "picture": "http://example.com/avatar.png",
        }

    res = client.get("/me")
    assert res.status_code == 200
    data = res.get_json()

    assert data["authenticated"] is True
    assert data["email"] == sample_user_fixture.email
    assert data["account_exists"] is True
    assert data["user_id"] == sample_user_fixture.id
    assert data["auth"] == sample_user_fixture.auth
    assert data["activity"] == sample_user_fixture.activity
    assert data["presentation_id"] == sample_user_fixture.presentation_id


#  /google/logout tests 

def test_google_logout_clears_session_and_redirects(client):
    """GET /google/logout should clear session['user'] and redirect to '/'."""

    with client.session_transaction() as sess:
        sess["user"] = {"email": "someone@example.com"}

    res = client.get("/google/logout", follow_redirects=False)

    assert res.status_code == 302
    assert res.headers["Location"].endswith("/")

    with client.session_transaction() as sess:
        assert "user" not in sess


#  banned_user_redirect decorator tests 

def test_schedule_accessible_to_anonymous_user(client):
    """
    /schedule uses @banned_user_redirect but should be accessible to
    users with no session at all.
    """
    res = client.get("/schedule")
    assert res.status_code == 200


def test_schedule_allows_normal_user(client, attendee_user):
    """
    /schedule with a non-banned user should render normally (no redirect).
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": attendee_user.email,
            "name": "Normal User",
        }

    res = client.get("/schedule")
    assert res.status_code == 200


def test_schedule_redirects_banned_user_to_fizzbuzz(client, banned_user):
    """
    @banned_user_redirect: banned user should be redirected to /fizzbuzz.
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": banned_user.email,
            "name": "Banned User",
        }

    res = client.get("/schedule", follow_redirects=False)
    assert res.status_code == 302
    assert "/fizzbuzz" in res.headers["Location"]


#  organizer_required decorator tests 

def test_organizer_required_redirects_anonymous_to_google_login(client):
    """
    /organizer-user-status requires organizer role.
    Unauthenticated user should be redirected to /google/login.
    """
    res = client.get("/organizer-user-status", follow_redirects=False)
    assert res.status_code == 302
    assert "/google/login" in res.headers["Location"]


def test_organizer_required_redirects_no_email_to_google_login(client):
    """If session exists but has no email, redirect to /google/login."""
    with client.session_transaction() as sess:
        sess["user"] = {"name": "No Email User"}

    res = client.get("/organizer-user-status", follow_redirects=False)
    assert res.status_code == 302
    assert "/google/login" in res.headers["Location"]


def test_organizer_required_redirects_unknown_email_to_signup(client):
    """
    If Google session has an email but that user doesn't exist in DB,
    redirect to /signup.
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": "nonexistent@example.com",
            "name": "Ghost User",
        }

    res = client.get("/organizer-user-status", follow_redirects=False)
    assert res.status_code == 302
    assert "/signup" in res.headers["Location"]


def test_organizer_required_allows_organizer(client, organizer_user):
    """
    Organizer user should be able to access /organizer-user-status.
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": organizer_user.email,
            "name": "Org User",
        }

    res = client.get("/organizer-user-status")
    assert res.status_code == 200


def test_organizer_required_denies_non_organizer_html(client, attendee_user):
    """
    Non-organizer HTML request:
    Should be redirected to /dashboard (not JSON).
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": attendee_user.email,
            "name": "Attendee User",
        }

    res = client.get("/organizer-user-status", follow_redirects=False)
    assert res.status_code == 302
    assert "/dashboard" in res.headers["Location"]


def test_organizer_required_denies_non_organizer_ajax(client, attendee_user):
    """
    Non-organizer AJAX/JSON request:
    Should return 403 with JSON error.
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": attendee_user.email,
            "name": "Attendee User",
        }

    res = client.get(
        "/organizer-user-status",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert res.status_code == 403
    data = res.get_json()
    assert data["error"] == "forbidden"
    assert data["reason"] == "organizer_required"


#  abstract_grader_required decorator tests 

def test_abstract_grader_required_redirects_anonymous(client):
    """
    /abstract-grader with no session redirects to /google/login.
    """
    res = client.get("/abstract-grader", follow_redirects=False)
    assert res.status_code == 302
    assert "/google/login" in res.headers["Location"]


def test_abstract_grader_required_redirects_unknown_email(client):
    """
    /abstract-grader with email not in DB redirects to /signup.
    """
    with client.session_transaction() as sess:
        sess["user"] = {"email": "unknown@example.com", "name": "Unknown"}

    res = client.get("/abstract-grader", follow_redirects=False)
    assert res.status_code == 302
    assert "/signup" in res.headers["Location"]


def test_abstract_grader_required_allows_abstract_grader(client, abstract_grader_user):
    """
    User whose auth string includes 'abstract-grader' should pass.
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": abstract_grader_user.email,
            "name": "Abstract Grader",
        }

    res = client.get("/abstract-grader")
    assert res.status_code == 200


def test_abstract_grader_required_allows_organizer(client, organizer_user):
    """
    Organizer also has access to /abstract-grader.
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": organizer_user.email,
            "name": "Organizer",
        }

    res = client.get("/abstract-grader")
    assert res.status_code == 200


def test_abstract_grader_required_denies_non_grader_ajax(client, attendee_user):
    """
    Non-graded/non-organizer AJAX request should get 403 JSON error.
    """
    with client.session_transaction() as sess:
        sess["user"] = {
            "email": attendee_user.email,
            "name": "Attendee User",
        }

    res = client.get(
        "/abstract-grader",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert res.status_code == 403
    data = res.get_json()
    assert data["error"] == "forbidden"
    assert data["reason"] == "abstract_grader_required"
