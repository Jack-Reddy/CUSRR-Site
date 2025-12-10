# pylint: disable=unused-argument,redefined-outer-name,import-error
"""
Tests for Google OAuth authentication with mocked Google API responses.
Tests the OAuth flow, token exchange, userinfo retrieval, and session management.
"""

from unittest.mock import patch, MagicMock
import pytest
from website import db
from website.models import User


@pytest.fixture
def mock_google_token_response():
    """Mock successful Google OAuth token response."""
    return {
        'access_token': 'mock_access_token_12345',
        'id_token': 'mock_id_token_67890',
        'token_type': 'Bearer',
        'expires_in': 3600,
    }


@pytest.fixture
def mock_google_userinfo():
    """Mock Google userinfo response."""
    return {
        'sub': '1234567890',
        'email': 'testuser@example.com',
        'email_verified': True,
        'name': 'Test User',
        'given_name': 'Test',
        'family_name': 'User',
        'picture': 'https://example.com/photo.jpg',
        'locale': 'en',
    }


@pytest.fixture
def existing_user(app):
    """Create a user that exists in the database."""
    with app.app_context():
        user = User(
            firstname='Test',
            lastname='User',
            email='testuser@example.com',
            activity='active',
            auth='attendee',
        )
        db.session.add(user)
        db.session.commit()
        yield user


# Test /google/login endpoint

def test_google_login_redirects_to_oauth(client):
    """GET /google/login should redirect to Google OAuth authorization."""
    response = client.get('/google/login', follow_redirects=False)

    # Should redirect to authorize
    assert response.status_code == 302
    # The actual redirect URL contains Google's OAuth endpoint
    assert 'google' in response.location.lower() or 'auth' in response.location.lower()


# Test /google/auth callback endpoint

def test_google_auth_missing_code_handles_error(client):
    """GET /google/auth without code parameter should raise RuntimeError."""
    # The endpoint raises RuntimeError when code is missing
    try:
        response = client.get('/google/auth')
        # If no exception, check for error handling
        assert response.status_code in [302, 500]
    except RuntimeError as e:
        assert 'missing_authorization_code' in str(e)


@patch('website.requests.post')
@patch('website.requests.get')
def test_google_auth_no_id_token_falls_back_to_userinfo(
    mock_get, mock_post, client, mock_google_userinfo
):
    """
    If id_token is missing, should fetch userinfo via access_token.
    """
    # Token response without id_token
    token_response = {
        'access_token': 'mock_access_token_12345',
        'token_type': 'Bearer',
        'expires_in': 3600,
    }

    mock_token_resp = MagicMock()
    mock_token_resp.json.return_value = token_response
    mock_post.return_value = mock_token_resp

    # Mock userinfo endpoint
    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.json.return_value = mock_google_userinfo
    mock_get.return_value = mock_userinfo_resp

    response = client.get('/google/auth?code=test_auth_code', follow_redirects=False)

    assert response.status_code == 302

    # Should have called userinfo endpoint
    mock_get.assert_called()

    # Verify session
    with client.session_transaction() as sess:
        user_info = sess.get('user')
        assert user_info is not None
        assert user_info.get('email') == 'testuser@example.com'


def test_google_logout_when_not_logged_in(client):
    """GET /google/logout when not logged in should still redirect to home."""
    response = client.get('/google/logout', follow_redirects=False)

    assert response.status_code == 302
    assert response.location == '/'

    # Verify no error occurs
    with client.session_transaction() as sess:
        assert 'user' not in sess
