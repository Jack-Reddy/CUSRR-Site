"""Security helpers for API route authorization."""
from flask import jsonify, request, session


ROLE_ALIASES = {
    'admin': 'organizer',
}


def _roles_for(user):
    if not user or not user.auth:
        return set()
    roles = {role.strip().lower() for role in str(user.auth).split(',') if role.strip()}
    roles.update(ROLE_ALIASES[role] for role in list(roles) if role in ROLE_ALIASES)
    return roles


def _error(reason, status=403):
    return jsonify({"error": "forbidden", "reason": reason}), status


def _session_email():
    user_info = session.get('user') or {}
    return user_info.get('email')


def _current_user(User):
    email = _session_email()
    if not email:
        return None
    return User.query.filter_by(email=email).first()


def _has_any_role(user, *roles):
    allowed = {role.lower() for role in roles}
    return bool(_roles_for(user) & allowed)


def _require_db_user(User):
    if not _session_email():
        return None, _error("authentication_required", 401)
    user = _current_user(User)
    if not user:
        return None, _error("account_required", 403)
    return user, None


def _require_roles(User, *roles):
    user, response = _require_db_user(User)
    if response:
        return response
    if not _has_any_role(user, *roles):
        return _error("insufficient_role")
    return None


def _require_authenticated_user(User):
    _, response = _require_db_user(User)
    return response


def _path_int_after(path, marker):
    parts = path.strip('/').split('/')
    try:
        marker_index = parts.index(marker)
        return int(parts[marker_index + 1])
    except (ValueError, IndexError, TypeError):
        return None


def install_api_security(app, User):
    """Install centralized authorization checks for API routes."""
    if app.config.get('TESTING', False):
        return

    @app.before_request
    def enforce_api_permissions():
        if request.method == 'OPTIONS':
            return None

        path = request.path.rstrip('/') or '/'
        if not path.startswith('/api/v1/'):
            return None

        method = request.method

        if path.startswith('/api/v1/users'):
            return _check_users_api(User, path, method)

        if path.startswith('/api/v1/block-schedule') and method in ('POST', 'PUT', 'DELETE'):
            return _require_roles(User, 'organizer')

        if path.startswith('/api/v1/presentations'):
            return _check_presentations_api(User, path, method)

        if path.startswith('/api/v1/grades'):
            return _require_roles(User, 'organizer', 'judge')

        if path.startswith('/api/v1/abstractgrades'):
            return _check_abstract_grades_api(User, path, method)

        return None


def _check_users_api(User, path, method):
    if path == '/api/v1/users/roommate-preferences' and method in ('GET', 'PUT'):
        return _require_authenticated_user(User)

    if method == 'POST':
        if not _session_email():
            return _error("authentication_required", 401)
        return None

    if method == 'GET':
        user, response = _require_db_user(User)
        if response:
            return response
        if path == '/api/v1/users':
            if not _has_any_role(user, 'organizer'):
                return _error("organizer_required")
            return None
        requested_user_id = _path_int_after(path, 'users')
        if requested_user_id == user.id or _has_any_role(user, 'organizer'):
            return None
        return _error("organizer_or_self_required")

    if method == 'PUT':
        user, response = _require_db_user(User)
        if response:
            return response
        requested_user_id = _path_int_after(path, 'users')
        if requested_user_id == user.id or _has_any_role(user, 'organizer'):
            return None
        return _error("organizer_or_self_required")

    if method == 'DELETE':
        return _require_roles(User, 'organizer')

    return None


def _check_presentations_api(User, path, method):
    if method == 'GET':
        if path == '/api/v1/presentations/download-all':
            return _require_roles(User, 'organizer')
        return None

    if method == 'POST':
        if path == '/api/v1/presentations/order':
            return _require_roles(User, 'organizer')
        if path == '/api/v1/presentations/abstract-images':
            return _require_authenticated_user(User)
        if path.endswith('/upload'):
            return _check_presentation_upload(User, path)
        return _require_authenticated_user(User)

    if method in ('PUT', 'DELETE'):
        return _require_roles(User, 'organizer')

    return None


def _check_presentation_upload(User, path):
    user, response = _require_db_user(User)
    if response:
        return response
    if _has_any_role(user, 'organizer'):
        return None
    presentation_id = _path_int_after(path, 'presentations')
    if presentation_id and user.presentation_id == presentation_id:
        return None
    return _error("presentation_owner_required")


def _check_abstract_grades_api(User, path, method):
    if path.startswith('/api/v1/abstractgrades/completed/') and method == 'GET':
        user, response = _require_db_user(User)
        if response:
            return response
        requested_user_id = _path_int_after(path, 'completed')
        if requested_user_id == user.id or _has_any_role(user, 'organizer', 'abstract-grader'):
            return None
        return _error("grader_or_self_required")

    return _require_roles(User, 'organizer', 'abstract-grader')
