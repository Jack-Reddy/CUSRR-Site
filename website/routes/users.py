"""routes for user table in db"""
import re

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import IntegrityError
from website.models import Presentation, User
from website import db

users_bp = Blueprint('users', __name__)
ROLE_ALIASES = {
    'admin': 'organizer',
}


def _security_checks_enabled():
    return not current_app.config.get('TESTING', False)


def _route_error(default, error):
    if current_app.config.get('TESTING', False):
        return str(error)
    return default


def _roles_for(user):
    if not user or not user.auth:
        return set()
    roles = {role.strip().lower() for role in str(user.auth).split(',') if role.strip()}
    roles.update(ROLE_ALIASES[role] for role in list(roles) if role in ROLE_ALIASES)
    return roles


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


def _normalize_lookup(value):
    """Normalize names/emails for roommate preference matching."""
    return re.sub(r'\s+', ' ', str(value or '').strip().lower())


def _compact_lookup(value):
    """Normalize by dropping non-alphanumeric chars for fuzzy name/email matching."""
    return re.sub(r'[^a-z0-9@]+', '', _normalize_lookup(value))


def _display_name(user):
    if not user:
        return None
    return f"{user.firstname} {user.lastname}".strip()


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
        key = _normalize_lookup(entry)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(entry)
    return cleaned


def _roommate_preference_columns():
    """Return existing roommate preference table column names."""
    inspector = inspect(db.engine)
    if not inspector.has_table('roommate_preferences'):
        return set()
    return {column['name'] for column in inspector.get_columns('roommate_preferences')}


def _structured_roommate_table_sql(dialect_name):
    id_type = 'INTEGER PRIMARY KEY AUTOINCREMENT' if dialect_name == 'sqlite' else 'SERIAL PRIMARY KEY'
    return f"""
        CREATE TABLE IF NOT EXISTS roommate_preferences (
            id {id_type},
            user_id INTEGER NOT NULL,
            preferred_email VARCHAR(120) NOT NULL,
            preferred_user_id INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, preferred_email)
        )
    """


def _unmatched_roommate_table_sql(dialect_name):
    id_type = 'INTEGER PRIMARY KEY AUTOINCREMENT' if dialect_name == 'sqlite' else 'SERIAL PRIMARY KEY'
    return f"""
        CREATE TABLE IF NOT EXISTS roommate_preference_unmatched (
            id {id_type},
            user_id INTEGER NOT NULL,
            raw_preference VARCHAR(255) NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, raw_preference)
        )
    """


def _row_value(row, key):
    """Read a value from SQLAlchemy RowMapping/dict/tuple-like rows."""
    try:
        return row[key]
    except (KeyError, TypeError):
        return getattr(row, key, None)


def _user_row_matches_preference(user_row, entry):
    """Return True if a SQL row/dict user matches an email or full-name entry."""
    normalized = _normalize_lookup(entry)
    compact = _compact_lookup(entry)
    if not normalized:
        return False

    firstname = _row_value(user_row, 'firstname') or ''
    lastname = _row_value(user_row, 'lastname') or ''
    email = _row_value(user_row, 'email') or ''

    full_name = _normalize_lookup(f"{firstname} {lastname}")
    reverse_name = _normalize_lookup(f"{lastname} {firstname}")
    compact_full_name = _compact_lookup(full_name)
    compact_reverse_name = _compact_lookup(reverse_name)
    compact_email = _compact_lookup(email)
    compact_email_local = _compact_lookup(str(email).split('@')[0])

    if '@' in normalized:
        return compact == compact_email

    exact_name_match = normalized in (full_name, reverse_name)
    compact_name_match = compact in (compact_full_name, compact_reverse_name)
    compact_email_match = compact and compact == compact_email_local
    return exact_name_match or compact_name_match or compact_email_match


def _match_user_id_from_rows(entry, user_rows):
    """Return a unique user id match from raw user rows, or None."""
    matches = [
        _row_value(user_row, 'id')
        for user_row in user_rows
        if _user_row_matches_preference(user_row, entry)
    ]
    matches = [match for match in matches if match is not None]
    return matches[0] if len(matches) == 1 else None


def _migrate_legacy_roommate_preferences(conn, dialect_name):
    """Convert old one-row text preferences into structured/review rows."""
    legacy_rows = conn.execute(
        text("SELECT user_id, preferences FROM roommate_preferences")
    ).mappings().all()
    user_rows = conn.execute(
        text("SELECT id, firstname, lastname, email FROM users")
    ).mappings().all()

    conn.execute(text("DROP TABLE roommate_preferences"))
    conn.execute(text(_structured_roommate_table_sql(dialect_name)))
    conn.execute(text(_unmatched_roommate_table_sql(dialect_name)))

    for legacy_row in legacy_rows:
        user_id = legacy_row['user_id']
        for entry in _parse_roommate_preferences(legacy_row['preferences']):
            matched_user_id = _match_user_id_from_rows(entry, user_rows)
            if matched_user_id:
                conn.execute(
                    text("""
                        INSERT INTO roommate_preferences
                            (user_id, preferred_email, preferred_user_id, updated_at)
                        VALUES
                            (:uid, :preferred_email, :preferred_user_id, CURRENT_TIMESTAMP)
                    """),
                    {
                        "uid": user_id,
                        "preferred_email": entry,
                        "preferred_user_id": matched_user_id,
                    }
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO roommate_preference_unmatched
                            (user_id, raw_preference, updated_at)
                        VALUES
                            (:uid, :raw_preference, CURRENT_TIMESTAMP)
                    """),
                    {"uid": user_id, "raw_preference": entry}
                )


def ensure_roommate_preferences_table():
    """Create or migrate the structured roommate preference tables."""
    dialect_name = db.engine.dialect.name
    inspector = inspect(db.engine)

    if inspector.has_table('roommate_preferences'):
        columns = {column['name'] for column in inspector.get_columns('roommate_preferences')}
        if 'preferences' in columns and 'preferred_email' not in columns:
            with db.engine.begin() as conn:
                _migrate_legacy_roommate_preferences(conn, dialect_name)
            return

    with db.engine.begin() as conn:
        conn.execute(text(_structured_roommate_table_sql(dialect_name)))
        conn.execute(text(_unmatched_roommate_table_sql(dialect_name)))


def _find_user_for_preference(entry):
    """Return a unique matching user when the preference is an email or full name."""
    normalized = _normalize_lookup(entry)
    if not normalized:
        return None

    if '@' in normalized:
        return User.query.filter(func.lower(User.email) == normalized).first()

    users = User.query.all()
    matches = [user for user in users if _user_row_matches_preference(user, entry)]
    return matches[0] if len(matches) == 1 else None


def _roommate_entry_payload(entry, preferred_user_id=None, unmatched=False):
    """Build a roommate preference response entry with match metadata."""
    preferred_user = None
    if preferred_user_id:
        preferred_user = db.session.get(User, preferred_user_id)
    if not preferred_user and not unmatched:
        preferred_user = _find_user_for_preference(entry)

    return {
        "preferred_email": entry,
        "preferred_user_id": preferred_user.id if preferred_user else None,
        "preferred_name": _display_name(preferred_user) if preferred_user else None,
        "matched": bool(preferred_user),
        "needs_review": unmatched or not preferred_user,
    }


def _get_roommate_preference_entries(user_id):
    ensure_roommate_preferences_table()
    matched_rows = db.session.execute(
        text("""
            SELECT preferred_email, preferred_user_id
            FROM roommate_preferences
            WHERE user_id = :uid
            ORDER BY id ASC
        """),
        {"uid": user_id}
    ).fetchall()
    unmatched_rows = db.session.execute(
        text("""
            SELECT raw_preference
            FROM roommate_preference_unmatched
            WHERE user_id = :uid
            ORDER BY id ASC
        """),
        {"uid": user_id}
    ).fetchall()

    entries = [_roommate_entry_payload(row[0], row[1]) for row in matched_rows]
    entries.extend(_roommate_entry_payload(row[0], unmatched=True) for row in unmatched_rows)
    return entries


def _get_roommate_preferences(user_id):
    """Return preferences as newline-separated text for the existing UI."""
    entries = _get_roommate_preference_entries(user_id)
    return "\n".join(entry["preferred_email"] for entry in entries)


def _set_roommate_preferences(user_id, preferences):
    """Persist matched preferences by user id and unmatched raw input for review."""
    ensure_roommate_preferences_table()
    entries = _parse_roommate_preferences(preferences)

    db.session.execute(
        text("DELETE FROM roommate_preferences WHERE user_id = :uid"),
        {"uid": user_id}
    )
    db.session.execute(
        text("DELETE FROM roommate_preference_unmatched WHERE user_id = :uid"),
        {"uid": user_id}
    )

    for entry in entries:
        matched_user = _find_user_for_preference(entry)
        if matched_user:
            db.session.execute(
                text("""
                    INSERT INTO roommate_preferences
                        (user_id, preferred_email, preferred_user_id, updated_at)
                    VALUES
                        (:uid, :preferred_email, :preferred_user_id, CURRENT_TIMESTAMP)
                """),
                {
                    "uid": user_id,
                    "preferred_email": matched_user.email,
                    "preferred_user_id": matched_user.id,
                }
            )
        else:
            db.session.execute(
                text("""
                    INSERT INTO roommate_preference_unmatched
                        (user_id, raw_preference, updated_at)
                    VALUES
                        (:uid, :raw_preference, CURRENT_TIMESTAMP)
                """),
                {"uid": user_id, "raw_preference": entry}
            )


def _delete_roommate_preferences_for_user(user):
    """Delete roommate preference rows safely."""
    ensure_roommate_preferences_table()
    db.session.execute(
        text("""
            DELETE FROM roommate_preferences
            WHERE user_id = :uid OR preferred_user_id = :uid
        """),
        {"uid": user.id}
    )
    db.session.execute(
        text("DELETE FROM roommate_preference_unmatched WHERE user_id = :uid"),
        {"uid": user.id}
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
    try:
        _set_roommate_preferences(
            user.id,
            data.get('preference_entries') if 'preference_entries' in data else data.get('preferences', '')
        )
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": _route_error("Could not save roommate preferences", error)}), 500

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
        _delete_roommate_preferences_for_user(user)
        db.session.delete(user)
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": _route_error("Could not delete user", error)}), 500

    return jsonify({"message": "User deleted"}), 200
