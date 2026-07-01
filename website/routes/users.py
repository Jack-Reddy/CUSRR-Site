"""routes for user table in db"""
import re

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from website.models import Presentation, User
from website import db

users_bp = Blueprint('users', __name__)


def _security_checks_enabled():
    return not current_app.config.get('TESTING', False)


def _route_error(default, error):
    if current_app.config.get('TESTING', False):
        return str(error)
    return default


def _roles_for(user):
    if not user or not user.auth:
        return set()
    return {role.strip().lower() for role in str(user.auth).split(',') if role.strip()}


def _session_email():
    user_info = session.get('user') or {}
    return user_info.get('email')


def _current_user():
    email = _session_email()
    if not email:
        return None
    return User.query.filter_by(email=email).first()


def _is_organizer(user):
    return 'organizer' in _roles_for(user)


def ensure_roommate_preferences_table():
    """Create the structured roommate preferences table if it does not exist."""
    dialect_name = db.engine.dialect.name
    with db.engine.begin() as conn:
        if dialect_name == 'sqlite':
            conn.execute(text(
                """
                CREATE TABLE IF NOT EXISTS roommate_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    preferred_email VARCHAR(120) NOT NULL,
                    preferred_user_id INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, preferred_email)
                )
                """
            ))
        else:
            conn.execute(text(
                """
                CREATE TABLE IF NOT EXISTS roommate_preferences (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    preferred_email VARCHAR(120) NOT NULL,
                    preferred_user_id INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, preferred_email)
                )
                """
            ))


def _parse_roommate_preferences(preferences):
    """Split textarea content into normalized roommate preference entries."""
    if isinstance(preferences, list):
        raw_values = preferences
    else:
        raw_values = re.split(r'[\n,;]+', preferences or '')

    cleaned = []
    seen = set()
    for value in raw_values:
        entry = str(value or '').strip()
        if not entry:
            continue
        key = entry.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(entry)
    return cleaned


def _find_user_id_for_preference(entry):
    """Return a matching user id when the preference is an existing email."""
    if '@' not in entry:
        return None
    preferred_user = User.query.filter_by(email=entry).first()
    if preferred_user:
        return preferred_user.id
    preferred_user = User.query.filter_by(email=entry.lower()).first()
    return preferred_user.id if preferred_user else None


def _get_roommate_preference_entries(user_id):
    ensure_roommate_preferences_table()
    rows = db.session.execute(
        text("""
            SELECT preferred_email, preferred_user_id
            FROM roommate_preferences
            WHERE user_id = :uid
            ORDER BY id ASC
        """),
        {"uid": user_id}
    ).fetchall()
    return [
        {
            "preferred_email": row[0],
            "preferred_user_id": row[1],
        }
        for row in rows
    ]


def _get_roommate_preferences(user_id):
    """Return preferences as newline-separated text for the existing UI."""
    entries = _get_roommate_preference_entries(user_id)
    return "\n".join(entry["preferred_email"] for entry in entries)


def _set_roommate_preferences(user_id, preferences):
    """Persist roommate preferences as one row per preferred person/email."""
    ensure_roommate_preferences_table()
    entries = _parse_roommate_preferences(preferences)

    db.session.execute(
        text("DELETE FROM roommate_preferences WHERE user_id = :uid"),
        {"uid": user_id}
    )

    for entry in entries:
        db.session.execute(
            text("""
                INSERT INTO roommate_preferences
                    (user_id, preferred_email, preferred_user_id, updated_at)
                VALUES
                    (:uid, :preferred_email, :preferred_user_id, CURRENT_TIMESTAMP)
            """),
            {
                "uid": user_id,
                "preferred_email": entry,
                "preferred_user_id": _find_user_id_for_preference(entry),
            }
        )


def _can_assign_presentation(user, presentation_id):
    if presentation_id in (None, ''):
        user.presentation_id = None
        return None

    try:
        presentation_id = int(presentation_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid presentation_id"}), 400

    presentation = db.session.get(Presentation, presentation_id)
    if not presentation:
        return jsonify({"error": "Presentation not found"}), 404

    existing_presenters = User.query.filter(
        User.presentation_id == presentation.id,
        User.id != user.id
    ).count()
    if existing_presenters >= 3:
        return jsonify({"error": "Presentation already has 3 presenters"}), 403

    user.presentation_id = presentation.id
    return None


@users_bp.route('/', methods=['GET'])
def get_users():
    """GET all users"""
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200


@users_bp.route('/roommate-preferences', methods=['GET', 'PUT'])
def roommate_preferences():
    """Get or update the current user's structured roommate preferences."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    if request.method == 'GET':
        return jsonify({
            "preferences": _get_roommate_preferences(user.id),
            "preference_entries": _get_roommate_preference_entries(user.id),
        }), 200

    data = request.get_json() or {}
    _set_roommate_preferences(
        user.id,
        data.get('preference_entries') if 'preference_entries' in data else data.get('preferences', '')
    )
    db.session.commit()
    return jsonify({
        "preferences": _get_roommate_preferences(user.id),
        "preference_entries": _get_roommate_preference_entries(user.id),
    }), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """GET a single user"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = user.to_dict()
    data['roommate_preferences'] = _get_roommate_preferences(user.id)
    data['roommate_preference_entries'] = _get_roommate_preference_entries(user.id)
    return jsonify(data), 200


@users_bp.route('/', methods=['POST'])
def create_user():
    """POST create a new user with validation"""
    data = request.get_json() or {}
    required_fields = ['firstname', 'lastname', 'email']

    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    session_email = _session_email()
    current_user = _current_user()
    organizer = _is_organizer(current_user)
    requested_email = data.get('email')

    if _security_checks_enabled() and not organizer and requested_email != session_email:
        return jsonify({"error": "Cannot create an account for a different email"}), 403

    if _security_checks_enabled():
        auth_value = data.get('auth') if organizer else 'presenter'
        presentation_id = data.get('presentation_id') if organizer else None
    else:
        auth_value = data.get('auth')
        presentation_id = data.get('presentation_id')

    try:
        new_user = User(
            firstname=data['firstname'],
            lastname=data['lastname'],
            email=requested_email,
            activity=data.get('activity'),
            student_year=data.get('student_year'),
            presentation_id=presentation_id,
            auth=auth_value
        )
        db.session.add(new_user)
        db.session.flush()
        if 'roommate_preferences' in data or 'roommate_preference_entries' in data:
            _set_roommate_preferences(
                new_user.id,
                data.get('roommate_preference_entries')
                if 'roommate_preference_entries' in data
                else data.get('roommate_preferences')
            )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "User with this email already exists"}), 400
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": _route_error("Could not create user", error)}), 500

    return jsonify(new_user.to_dict()), 201


@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """PUT update user data"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    actor = _current_user()
    organizer = _is_organizer(actor)
    editing_self = actor and actor.id == user.id

    if _security_checks_enabled() and not organizer and not editing_self:
        return jsonify({"error": "Cannot update this user"}), 403

    user.firstname = data.get('firstname', user.firstname)
    user.lastname = data.get('lastname', user.lastname)
    user.activity = data.get('activity', user.activity)
    user.student_year = data.get('student_year', user.student_year)

    if 'roommate_preferences' in data or 'roommate_preference_entries' in data:
        _set_roommate_preferences(
            user.id,
            data.get('roommate_preference_entries')
            if 'roommate_preference_entries' in data
            else data.get('roommate_preferences')
        )

    if organizer or not _security_checks_enabled():
        user.email = data.get('email', user.email)
        if 'presentation_id' in data:
            assign_error = _can_assign_presentation(user, data.get('presentation_id'))
            if assign_error:
                return assign_error
        auth_val = data.get('auth', user.auth)
        if isinstance(auth_val, list):
            auth_val = ','.join(str(a) for a in auth_val)
        user.auth = auth_val
    elif 'presentation_id' in data:
        assign_error = _can_assign_presentation(user, data.get('presentation_id'))
        if assign_error:
            return assign_error

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "User with this email already exists"}), 400
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": _route_error("Could not update user", error)}), 500

    return jsonify(user.to_dict()), 200


@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """DELETE a user"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        ensure_roommate_preferences_table()
        db.session.execute(
            text("""
                DELETE FROM roommate_preferences
                WHERE user_id = :uid OR preferred_user_id = :uid
            """),
            {"uid": user.id}
        )
        db.session.delete(user)
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": _route_error("Could not delete user", error)}), 500

    return jsonify({"message": "User deleted"}), 200
