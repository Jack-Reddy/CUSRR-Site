# pylint: disable=redefined-outer-name
"""
Unit tests for the /api/v1/users/ routes.
Tests CRUD operations for the User model.
"""
# Standard library
from unittest.mock import patch

# Third-party
import pytest
from sqlalchemy.exc import IntegrityError

# Local
from website.models import User
from website import db


def test_get_users_empty(client):
    """Test that GET /api/v1/users/ returns an empty list when no users exist."""
    resp = client.get("/api/v1/users/")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_users_with_data(client, sample_user_fixture):
    """Test that GET /api/v1/users/ returns the inserted user."""
    resp = client.get("/api/v1/users/")
    data = resp.get_json()

    assert resp.status_code == 200
    assert len(data) == 1
    assert data[0]["email"] == sample_user_fixture.email
    assert data[0]["presentation"] is None


def test_get_one_user(client, sample_user_fixture):
    """Test GET /api/v1/users/<id> returns the correct user data."""
    resp = client.get(f"/api/v1/users/{sample_user_fixture.id}")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["firstname"] == "Jane"
    assert data["lastname"] == "Doe"
    assert data["presentation"] is None


def test_get_user_not_found(client):
    """Test GET /api/v1/users/<id> returns 404 if user does not exist."""
    resp = client.get("/api/v1/users/9999")
    assert resp.status_code == 404


def test_create_user(client, app):
    """Test POST /api/v1/users/ creates a new user successfully."""
    payload = {
        "firstname": "Bob",
        "lastname": "Smith",
        "email": "bob@example.com",
        "activity": "idle",
        "presentation_id": None,
        "auth": "judge"
    }

    resp = client.post("/api/v1/users/", json=payload)
    data = resp.get_json()

    assert resp.status_code == 201
    assert data["email"] == "bob@example.com"
    assert data["presentation"] is None

    # Confirm in DB
    with app.app_context():
        assert User.query.filter_by(email="bob@example.com").count() == 1


def test_create_user_missing_fields(client):
    """Test POST /api/v1/users/ with missing required fields returns error."""
    resp = client.post("/api/v1/users/", json={"firstname": "NoEmail"})
    assert resp.status_code in (400, 500)


def test_update_user(client, sample_user_fixture):
    """Test PUT /api/v1/users/<id> updates user fields correctly."""
    payload = {
        "firstname": "UpdatedName",
        "activity": "new-activity"
    }

    resp = client.put(f"/api/v1/users/{sample_user_fixture.id}", json=payload)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["firstname"] == "UpdatedName"
    assert data["activity"] == "new-activity"


def test_update_user_auth_list_conversion(client, sample_user_fixture):
    """Test that auth list is converted to a CSV string on update."""
    payload = {"auth": ["role1", "role2"]}

    resp = client.put(f"/api/v1/users/{sample_user_fixture.id}", json=payload)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["auth"] == "role1,role2"


def test_update_user_not_found(client):
    """Test PUT /api/v1/users/<id> returns 404 if user does not exist."""
    resp = client.put("/api/v1/users/9999", json={"firstname": "Nope"})
    assert resp.status_code == 404


def test_delete_user(client, sample_user_fixture, app):
    """Test DELETE /api/v1/users/<id> removes the user successfully."""
    resp = client.delete(f"/api/v1/users/{sample_user_fixture.id}")
    assert resp.status_code == 200
    assert resp.get_json() == {"message": "User deleted"}

    resp2 = client.get(f"/api/v1/users/{sample_user_fixture.id}")
    assert resp2.status_code == 404

    with app.app_context():
        assert User.query.count() == 0


def test_delete_user_not_found(client):
    """Test DELETE /api/v1/users/<id> returns 404 if user does not exist."""
    resp = client.delete("/api/v1/users/9999")
    assert resp.status_code == 404


def test_create_user_integrity_error(client):
    """Test POST /api/v1/users/ triggers IntegrityError."""
    payload = {
        "firstname": "Alice",
        "lastname": "Smith",
        "email": "alice@example.com"
    }

    # Mock commit to raise IntegrityError
    with patch('website.db.session.commit', side_effect=IntegrityError("mock", "mock", "mock")):
        resp = client.post("/api/v1/users/", json=payload)
        data = resp.get_json()

    assert resp.status_code == 400
    assert "already exists" in data["error"]


def test_create_user_generic_exception(client):
    """Test POST /api/v1/users/ triggers general Exception."""
    payload = {
        "firstname": "Alice",
        "lastname": "Smith",
        "email": "alice2@example.com"
    }

    with patch('website.db.session.commit', side_effect=Exception("mock exception")):
        resp = client.post("/api/v1/users/", json=payload)
        data = resp.get_json()

    assert resp.status_code == 500
    assert "mock exception" in data["error"]


def test_update_user_integrity_error(client, sample_user_fixture):
    """Test PUT /api/v1/users/<id> triggers IntegrityError."""
    payload = {"email": "conflict@example.com"}

    with patch('website.db.session.commit', side_effect=IntegrityError("mock", "mock", "mock")):
        resp = client.put(f"/api/v1/users/{sample_user_fixture.id}", json=payload)
        data = resp.get_json()

    assert resp.status_code == 400
    assert "already exists" in data["error"]


def test_update_user_generic_exception(client, sample_user_fixture):
    """Test PUT /api/v1/users/<id> triggers general Exception."""
    payload = {"firstname": "ErrorName"}

    with patch('website.db.session.commit', side_effect=Exception("mock update exception")):
        resp = client.put(f"/api/v1/users/{sample_user_fixture.id}", json=payload)
        data = resp.get_json()

    assert resp.status_code == 500
    assert "mock update exception" in data["error"]


def test_delete_user_generic_exception(client, sample_user_fixture):
    """Test DELETE /api/v1/users/<id> triggers general Exception."""
    with patch('website.db.session.delete', side_effect=Exception("mock delete exception")):
        resp = client.delete(f"/api/v1/users/{sample_user_fixture.id}")
        data = resp.get_json()

    assert resp.status_code == 500
    assert "mock delete exception" in data["error"]
