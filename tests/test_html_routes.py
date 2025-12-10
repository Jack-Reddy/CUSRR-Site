# pylint: disable=unused-argument
"""Tests for init.py html routes."""
from website import db 

def test_root_route_renders(client):
    """GET / should render the root route successfully."""
    res = client.get("/")
    assert res.status_code == 200

def test_schedule_route_renders(client):
    """GET /schedule should render the schedule page successfully."""
    res = client.get("/schedule")
    assert res.status_code == 200

def test_dashboard_route_renders(client):
    """GET /dashboard should render the dashboard page successfully."""
    res = client.get("/dashboard")
    assert res.status_code == 200

def test_abstract_grade_route_renders(client):
    """GET /abstract-grade should render the abstract grade page successfully."""
    res = client.get("/abstract-grader")
    assert res.status_code == 302

def test_organizer_user_status_route_renders(client):
    """GET /organizer-user-status should render the organizer user status page successfully."""
    res = client.get("/organizer-user-status")
    assert res.status_code == 302

def test_organizer_presentations_status_route_renders(client):
    """GET /organizer-presentations-status should render the organizer presentations status page successfully."""
    res = client.get("/organizer-presentations-status")
    assert res.status_code == 302

def test_google_login_route_redirects(client):
    """GET /google-login should redirect to Google OAuth."""
    res = client.get("/google/login")
    assert res.status_code == 302
    assert "accounts.google.com" in res.headers["Location"]

def test_logout_route_redirects(client):
    """GET /logout should log out the user and redirect."""
    res = client.get("/google/logout")
    assert res.status_code == 302
    assert res.headers["Location"] == "/"

def test_me_route_renders(client):
    """GET /me should render the user profile page successfully."""
    res = client.get("/me")
    assert res.status_code == 401

def test_blitz_route_renders(client):
    """GET /blitz should render the blitz page successfully."""
    res = client.get("/blitz_page")
    assert res.status_code == 200

def test_presentation_route_renders(client):
    """GET /presentation should render the presentation page successfully."""
    res = client.get("/presentation_page")
    assert res.status_code == 200

def test_signup_route_renders(client):
    """GET /signup should render the signup page successfully."""
    res = client.get("/signup")
    assert res.status_code == 200

def test_grades_dashboard_route_renders(client):
    """GET /grades-dashboard should render the grades dashboard page successfully."""
    res = client.get("/grades-dashboard")
    assert res.status_code == 302

def test_profile_route_renders(client):
    """GET /profile should render the profile page successfully."""
    res = client.get("/profile")
    assert res.status_code == 302

def test_abstract_scoring_route_renders(client):
    """GET /abstract-scoring should render the abstract scoring page successfully."""
    res = client.get("/abstract-scoring")
    assert res.status_code == 302
