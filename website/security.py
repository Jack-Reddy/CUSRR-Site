"""Security helpers for API route authorization."""
import io
import zipfile

from flask import jsonify, request, send_file, session
from sqlalchemy import text
from werkzeug.utils import secure_filename


ROLE_ALIASES = {
    'admin': 'organizer',
}


def _normalize_role(role):
    """Normalize role strings so abstract-grader and abstract grader match abstract_grader."""
    return str(role or '').strip().lower().replace('-', '_').replace(' ', '_')


def _roles_for(user):
    if not user or not user.auth:
        return set()
    roles = {_normalize_role(role) for role in str(user.auth).split(',') if role.strip()}
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
    allowed = {_normalize_role(role) for role in roles}
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


def _ensure_presentation_upload_table(db):
    """Make sure the upload metadata table exists before reading original filenames."""
    with db.engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS presentation_uploads (
                presentation_id INTEGER PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))


def _presentation_file_bytes(value):
    """Return real bytes from SQLAlchemy LargeBinary values across database drivers."""
    if value is None:
        return b''
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    try:
        return bytes(value)
    except TypeError:
        return b''


def _safe_zip_piece(value, fallback='untitled'):
    """Return a readable ZIP entry name part without path separators."""
    cleaned = str(value or fallback).strip() or fallback
    cleaned = cleaned.replace('/', '-').replace('\\', '-')
    cleaned = ''.join(char for char in cleaned if ord(char) >= 32)
    return cleaned or fallback


def _uploaded_filename(db, presentation_id):
    row = db.session.execute(
        text("SELECT filename FROM presentation_uploads WHERE presentation_id = :pid"),
        {"pid": presentation_id}
    ).fetchone()
    return row[0] if row and row[0] else None


def _extension_from_upload(uploaded_name, file_data):
    """Prefer the stored filename extension, then infer common upload formats from bytes."""
    if uploaded_name and '.' in uploaded_name:
        extension = uploaded_name.rsplit('.', 1)[-1].lower()
        if extension in {'pdf', 'ppt', 'pptx'}:
            return extension

    if file_data.startswith(b'%PDF'):
        return 'pdf'
    if file_data.startswith(b'PK\x03\x04'):
        return 'pptx'
    if file_data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        return 'ppt'
    return 'pptx'


def _unique_zip_name(filename, used_names):
    """Avoid duplicate names in the ZIP while preserving readable names."""
    count = used_names.get(filename, 0)
    used_names[filename] = count + 1
    if count == 0:
        return filename

    if '.' in filename:
        base, extension = filename.rsplit('.', 1)
        return f"{base} ({count + 1}).{extension}"
    return f"{filename} ({count + 1})"


def _presenter_names_for_zip(presentation):
    """Return presenter names for ZIP filenames."""
    names = []
    for presenter in presentation.presenters:
        first = (presenter.firstname or '').strip()
        last = (presenter.lastname or '').strip()
        full_name = f"{first} {last}".strip()
        names.append(full_name or presenter.email)
    return ', '.join(names) or f'presentation-{presentation.id}'


def _download_all_presentations_zip(User):
    """Return the presentation upload ZIP named as Presenter Names - Presentation Title.ext."""
    permission_response = _require_roles(User, 'organizer')
    if permission_response:
        return permission_response

    from website import db
    from website.models import Presentation

    _ensure_presentation_upload_table(db)
    zip_buffer = io.BytesIO()
    presentations = Presentation.query.order_by(Presentation.title.asc(), Presentation.id.asc()).all()
    used_names = {}

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for presentation in presentations:
            file_data = _presentation_file_bytes(presentation.presentation_file)
            if not file_data:
                continue

            uploaded_name = _uploaded_filename(db, presentation.id)
            safe_uploaded_name = secure_filename(uploaded_name) if uploaded_name else None
            extension = _extension_from_upload(safe_uploaded_name, file_data)
            presenter_part = _safe_zip_piece(_presenter_names_for_zip(presentation), f'presentation-{presentation.id}')
            title = _safe_zip_piece(presentation.title, fallback=f'presentation-{presentation.id}')
            filename = _unique_zip_name(f"{presenter_part} - {title}.{extension}", used_names)
            zipf.writestr(filename, file_data)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='presentations.zip'
    )


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
            return _require_roles(User, 'organizer', 'judge', 'abstract_grader')

        if path.startswith('/api/v1/abstractgrades'):
            return _check_abstract_grades_api(User, path, method)

        return None


def _check_users_api(User, path, method):
    if path == '/api/v1/users/roommate-preferences' and method in ('GET', 'PUT'):
        return _require_authenticated_user(User)

    if path == '/api/v1/users/roommate-preferences/export.csv' and method == 'GET':
        return _require_roles(User, 'organizer')

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
        if path in ('/api/v1/presentations/download-all', '/api/v1/presentations/download-all-named'):
            return _download_all_presentations_zip(User)
        return None

    if method == 'POST':
        if path == '/api/v1/presentations/order':
            return _require_roles(User, 'organizer')
        if path == '/api/v1/presentations/abstract-images':
            return _require_authenticated_user(User)
        if path.endswith('/upload'):
            return _require_roles(User, 'organizer')
        return _require_authenticated_user(User)

    if method == 'PUT':
        return _check_presentation_owner_or_organizer(User, path)

    if method == 'DELETE':
        return _require_roles(User, 'organizer')

    return None


def _check_presentation_owner_or_organizer(User, path):
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
        if requested_user_id == user.id or _has_any_role(user, 'organizer', 'abstract_grader'):
            return None
        return _error("grader_or_self_required")

    return _require_roles(User, 'organizer', 'abstract_grader')
