"""Lightweight API endpoints for organizer dashboard tables."""
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload, load_only

from website import db
from website.models import BlockSchedule, Presentation, User

users_table_bp = Blueprint('users_table', __name__)
presentations_table_bp = Blueprint('presentations_table', __name__)
VALID_PRESENTATION_TYPES = {'Presentation', 'Blitz', 'Poster'}


def _clean_text(value):
    """Normalize optional text fields for storage."""
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _error_payload(context, error):
    """Return a detailed JSON error while debugging organizer table saves."""
    return jsonify({
        'error': context,
        'exception_type': type(error).__name__,
        'message': str(error),
        'details': repr(error),
    }), 500


def _ensure_long_presentation_title_column():
    """Make existing production databases accept long presentation titles."""
    if current_app.config.get('TESTING', False):
        return

    dialect_name = db.engine.dialect.name
    if dialect_name not in ('postgresql', 'mysql', 'mariadb'):
        return

    try:
        with db.engine.begin() as conn:
            if dialect_name == 'postgresql':
                conn.execute(text("ALTER TABLE presentations ALTER COLUMN title TYPE TEXT"))
            else:
                conn.execute(text("ALTER TABLE presentations MODIFY title TEXT NOT NULL"))
    except Exception as error:  # keep unsupported/duplicate migrations from hiding the real save error
        current_app.logger.warning("Could not widen presentation title column: %s", error)


def _normalize_presentation_type(value):
    """Normalize a presentation type for table display."""
    if value is None:
        return None
    cleaned = str(value).strip()
    for valid_type in VALID_PRESENTATION_TYPES:
        if cleaned.lower() == valid_type.lower():
            return valid_type
    return cleaned or None


def _ensure_presentation_type_table():
    """Create the per-presentation type override table if it does not exist."""
    with db.engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS presentation_types (
                presentation_id INTEGER PRIMARY KEY,
                presentation_type VARCHAR(50) NOT NULL
            )
            """
        ))


def _ensure_presentation_visibility_table():
    """Create the per-presentation visibility table if it does not exist."""
    with db.engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS presentation_visibility (
                presentation_id INTEGER PRIMARY KEY,
                show_on_schedule BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        ))


def _presentation_type_overrides():
    """Return a map of presentation_id to explicit presentation type overrides."""
    _ensure_presentation_type_table()
    rows = db.session.execute(
        text("SELECT presentation_id, presentation_type FROM presentation_types")
    ).fetchall()
    return {row[0]: _normalize_presentation_type(row[1]) for row in rows if row[1]}


def _set_presentation_type(presentation_id, value):
    """Persist per-presentation type. Empty/invalid values remove the override."""
    _ensure_presentation_type_table()
    normalized = _normalize_presentation_type(value)
    if not normalized:
        db.session.execute(
            text("DELETE FROM presentation_types WHERE presentation_id = :pid"),
            {"pid": presentation_id}
        )
        return

    result = db.session.execute(
        text("UPDATE presentation_types SET presentation_type = :ptype WHERE presentation_id = :pid"),
        {"pid": presentation_id, "ptype": normalized}
    )
    if result.rowcount == 0:
        db.session.execute(
            text("INSERT INTO presentation_types (presentation_id, presentation_type) VALUES (:pid, :ptype)"),
            {"pid": presentation_id, "ptype": normalized}
        )


def _set_show_on_schedule(presentation_id, value):
    """Persist whether a presentation should show on schedule/program pages."""
    _ensure_presentation_visibility_table()
    result = db.session.execute(
        text("UPDATE presentation_visibility SET show_on_schedule = :value WHERE presentation_id = :pid"),
        {"pid": presentation_id, "value": bool(value)}
    )
    if result.rowcount == 0:
        db.session.execute(
            text("INSERT INTO presentation_visibility (presentation_id, show_on_schedule) VALUES (:pid, :value)"),
            {"pid": presentation_id, "value": bool(value)}
        )


def _format_datetime(value):
    """Format datetimes the same way the existing presentation API does."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%dT%H:%M:%S')
    return str(value)


def _effective_time(presentation):
    """Return the presentation's display time without loading heavy fields."""
    schedule = presentation.schedule
    if schedule and schedule.start_time:
        num = presentation.num_in_block if presentation.num_in_block is not None else 0
        sub = schedule.sub_length if schedule.sub_length is not None else 0
        try:
            return schedule.start_time + timedelta(minutes=(int(num) * int(sub)))
        except (TypeError, ValueError):
            return schedule.start_time
    return presentation.time


def _program_prefix(presentation, type_by_id):
    """Return the program identifier prefix for a presentation."""
    presentation_type = type_by_id.get(presentation.id)
    if not presentation_type and presentation.schedule:
        presentation_type = presentation.schedule.block_type

    value = str(presentation_type or '').strip().lower()
    if value == 'poster':
        return 'poster'
    if value == 'blitz':
        return 'blitz'
    return 'presentation'


def _program_sort_key(presentation):
    """Sort presentations consistently before assigning program identifiers."""
    display_time = _effective_time(presentation) or datetime.max
    schedule_id = presentation.schedule_id if presentation.schedule_id is not None else 0
    num_in_block = presentation.num_in_block if presentation.num_in_block is not None else 10**9
    return (display_time, schedule_id, num_in_block, presentation.id or 0)


def _program_identifier_map(presentations, type_by_id):
    """Return continuous IDs by presentation type across the table rows."""
    counters = {}
    identifiers = {}
    for presentation in sorted(presentations, key=_program_sort_key):
        prefix = _program_prefix(presentation, type_by_id)
        counters[prefix] = counters.get(prefix, 0) + 1
        identifiers[presentation.id] = f"{prefix}-{counters[prefix]}"
    return identifiers


def _user_full_name(user):
    """Return a display name for a user."""
    first = (user.firstname or '').strip()
    last = (user.lastname or '').strip()
    full_name = f"{first} {last}".strip()
    return full_name or user.email


def _quick_presentation_response(presentation):
    """Return a small response for modal updates without expensive serialization."""
    return {
        'id': presentation.id,
        'title': presentation.title,
        'abstract': presentation.abstract,
        'department': presentation.department,
        'mentor': presentation.mentor,
        'keywords': presentation.keywords,
        'schedule_id': presentation.schedule_id,
        'time': _format_datetime(presentation.time),
    }


@users_table_bp.route('/table', methods=['GET'])
def get_users_table():
    """Return lightweight attendee table rows without loading abstracts/files."""
    type_by_id = _presentation_type_overrides()

    rows = (
        db.session.query(
            User.id.label('id'),
            User.firstname.label('firstname'),
            User.lastname.label('lastname'),
            User.email.label('email'),
            User.activity.label('activity'),
            User.auth.label('auth'),
            User.student_year.label('student_year'),
            User.presentation_id.label('presentation_id'),
            Presentation.title.label('presentation_title'),
            (func.length(func.trim(func.coalesce(Presentation.abstract, ''))) > 0).label('abstract_submitted'),
            Presentation.presentation_file.isnot(None).label('presentation_uploaded'),
            BlockSchedule.block_type.label('schedule_block_type'),
        )
        .outerjoin(Presentation, User.presentation_id == Presentation.id)
        .outerjoin(BlockSchedule, Presentation.schedule_id == BlockSchedule.id)
        .order_by(User.email.asc())
        .all()
    )

    data = []
    for row in rows:
        has_presentation = bool(row.presentation_id)
        abstract_submitted = bool(row.abstract_submitted)
        presentation_uploaded = bool(row.presentation_uploaded)
        presentation_type = type_by_id.get(row.presentation_id) or _normalize_presentation_type(row.schedule_block_type)
        name = f"{row.firstname} {row.lastname}".strip()

        data.append({
            'id': row.id,
            'firstname': row.firstname,
            'lastname': row.lastname,
            'name': name,
            'email': row.email,
            'activity': row.activity,
            'student_year': row.student_year,
            'presentation': row.presentation_title,
            'presentation_id': row.presentation_id,
            'presentation_type': presentation_type,
            'status': 'complete' if has_presentation else 'incomplete',
            'abstract_submitted': abstract_submitted,
            'abstract_status': 'complete' if abstract_submitted else 'incomplete',
            'presentation_uploaded': presentation_uploaded,
            'presentation_upload_status': 'complete' if presentation_uploaded else 'incomplete',
            'submission_incomplete': has_presentation and (
                not abstract_submitted or not presentation_uploaded
            ),
            'auth': row.auth,
        })

    return jsonify(data), 200


@presentations_table_bp.route('/table', methods=['GET'])
def get_presentations_table():
    """Return lightweight presentation table rows without full abstracts/files."""
    type_by_id = _presentation_type_overrides()
    presentations = (
        Presentation.query
        .options(
            load_only(
                Presentation.id,
                Presentation.title,
                Presentation.department,
                Presentation.mentor,
                Presentation.keywords,
                Presentation.time,
                Presentation.num_in_block,
                Presentation.schedule_id,
            ),
            joinedload(Presentation.schedule).load_only(
                BlockSchedule.id,
                BlockSchedule.title,
                BlockSchedule.block_type,
                BlockSchedule.start_time,
                BlockSchedule.sub_length,
            ),
            joinedload(Presentation.presenters).load_only(
                User.id,
                User.firstname,
                User.lastname,
                User.email,
            ),
        )
        .order_by(Presentation.id.asc())
        .all()
    )
    identifiers = _program_identifier_map(presentations, type_by_id)

    data = []
    for presentation in presentations:
        schedule = presentation.schedule
        presentation_type = type_by_id.get(presentation.id)
        if not presentation_type and schedule:
            presentation_type = _normalize_presentation_type(schedule.block_type)

        data.append({
            'id': presentation.id,
            'program_identifier': identifiers.get(presentation.id),
            'title': presentation.title,
            'department': presentation.department,
            'mentor': presentation.mentor,
            'keywords': presentation.keywords,
            'type': presentation_type,
            'schedule_title': schedule.title if schedule else None,
            'schedule_id': presentation.schedule_id,
            'time': _format_datetime(_effective_time(presentation)),
            'presenters': [
                {
                    'id': presenter.id,
                    'firstname': presenter.firstname,
                    'lastname': presenter.lastname,
                    'email': presenter.email,
                    'name': _user_full_name(presenter),
                }
                for presenter in presentation.presenters
            ],
        })

    return jsonify(data), 200


@presentations_table_bp.route('/<int:presentation_id>/quick-update', methods=['PUT'])
def quick_update_presentation(presentation_id):
    """Update organizer-editable fields and return a small response."""
    try:
        _ensure_long_presentation_title_column()
        presentation = Presentation.query.get_or_404(presentation_id)
        data = request.get_json() or {}

        if 'title' in data:
            presentation.title = data.get('title') or ''
        if 'abstract' in data:
            presentation.abstract = data.get('abstract')
        if 'department' in data:
            presentation.department = _clean_text(data.get('department'))
        if 'mentor' in data:
            presentation.mentor = _clean_text(data.get('mentor'))
        if 'keywords' in data:
            presentation.keywords = _clean_text(data.get('keywords'))
        if 'show_on_schedule' in data:
            _set_show_on_schedule(presentation.id, data.get('show_on_schedule'))
        if 'type' in data:
            _set_presentation_type(presentation.id, data.get('type'))

        db.session.commit()
        return jsonify(_quick_presentation_response(presentation)), 200
    except Exception as error:
        db.session.rollback()
        return _error_payload('presentation_quick_update_failed', error)
