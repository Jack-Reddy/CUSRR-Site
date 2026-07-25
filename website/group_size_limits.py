"""Group-size limits shared by presentation creation and attendee assignment."""
import io
import zipfile
from datetime import datetime

from flask import current_app, jsonify, request, send_file, session
from sqlalchemy import text

from website import db
from website.models import BlockSchedule, Presentation, User
from website.routes import presentations as presentations_module
from website.routes import users as users_module

MAX_PRESENTERS_PER_GROUP = 5


def _current_user():
    """Return the authenticated database user for presentation creation."""
    user_info = session.get('user') or {}
    email = user_info.get('email')
    if not email:
        return None
    return User.query.filter_by(email=email).first()


def ensure_long_presentation_title_column():
    """Make existing production databases accept long presentation titles."""
    if current_app.config.get('TESTING', False):
        return

    dialect_name = db.engine.dialect.name

    try:
        with db.engine.begin() as conn:
            if dialect_name == 'postgresql':
                conn.execute(text("ALTER TABLE presentations ALTER COLUMN title TYPE TEXT"))
            elif dialect_name in ('mysql', 'mariadb'):
                conn.execute(text("ALTER TABLE presentations MODIFY title TEXT NOT NULL"))
    except Exception as error:  # keep updates from crashing if the migration already ran or is unsupported
        current_app.logger.warning("Could not widen presentation title column: %s", error)


def _can_assign_presentation_with_five_person_limit(user, presentation_id):
    """Assign a user to a presentation while allowing five presenters total."""
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
    if existing_presenters >= MAX_PRESENTERS_PER_GROUP:
        return jsonify({"error": f"Presentation already has {MAX_PRESENTERS_PER_GROUP} presenters"}), 403

    user.presentation_id = presentation.id
    return None


def _presentation_update_response(presentation):
    """Return a small response after updates without running the heavy serializer."""
    calculated_time = presentations_module.effective_presentation_time(presentation)
    return {
        "id": presentation.id,
        "title": presentation.title,
        "abstract": presentation.abstract,
        "department": getattr(presentation, "department", None),
        "mentor": getattr(presentation, "mentor", None),
        "keywords": getattr(presentation, "keywords", None),
        "schedule_id": presentation.schedule_id,
        "time": calculated_time.strftime('%Y-%m-%dT%H:%M:%S') if calculated_time else None,
        "type": presentations_module.get_presentation_type(presentation),
        "show_on_schedule": presentations_module.get_show_on_schedule(presentation.id),
    }


def update_presentation_with_lightweight_response(presentation_id):
    """Update a presentation and avoid a slow/error-prone full serializer response."""
    ensure_long_presentation_title_column()

    presentation = Presentation.query.get_or_404(presentation_id)
    data = request.get_json() or {}

    permission_error = presentations_module._validate_update_permission(presentation, data)
    if permission_error:
        return permission_error

    schedule_id_raw = data.get('schedule_id') or data.get('scheduleId')
    if schedule_id_raw is not None:
        if schedule_id_raw == "":
            presentation.schedule_id = None
            presentation.num_in_block = None
        else:
            try:
                schedule_id_int = int(schedule_id_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid schedule_id"}), 400

            block = BlockSchedule.query.get(schedule_id_int)
            if not block:
                return jsonify({"error": "Schedule block not found"}), 404
            presentation.schedule_id = block.id

    if 'time' in data:
        time_raw = data.get('time')
        if time_raw:
            try:
                presentation.time = datetime.fromisoformat(time_raw)
            except ValueError:
                return jsonify({"error": "Invalid datetime format. Use ISO 8601."}), 400
        else:
            presentation.time = None

    if 'title' in data:
        presentation.title = data.get('title') or ''
    if 'abstract' in data:
        presentation.abstract = data.get('abstract')
    if 'presentation_file' in data:
        presentation.presentation_file = data.get('presentation_file')

    if 'department' in data:
        presentation.department = presentations_module._clean_text(data.get('department'))
    if 'mentor' in data:
        presentation.mentor = presentations_module._clean_text(data.get('mentor'))
    if 'keywords' in data:
        presentation.keywords = presentations_module._clean_text(data.get('keywords'))

    if 'show_on_schedule' in data:
        presentations_module.set_show_on_schedule(presentation.id, data.get('show_on_schedule'))

    if 'type' in data:
        presentations_module.set_presentation_type(presentation.id, data.get('type'))

    db.session.commit()
    return jsonify(_presentation_update_response(presentation))


def create_presentation_with_five_person_limit():
    """Create a presentation while allowing up to five presenters total."""
    ensure_long_presentation_title_column()

    data = request.get_json() or {}
    schedule_id = data.get('schedule_id') or data.get('block_id')
    time_str = data.get('time')

    security_checks_enabled = not current_app.config.get('TESTING', False)
    creator = _current_user()
    if security_checks_enabled and not creator:
        return jsonify({"error": "Authentication required"}), 401
    if creator and creator.presentation_id:
        return jsonify({"error": "You already have an assigned presentation"}), 400

    parsed_time = None
    if time_str:
        try:
            parsed_time = datetime.fromisoformat(time_str)
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use ISO 8601."}), 400

    partner_emails = data.get('partner_emails') or []
    legacy_partner_email = data.get('partner_email')
    if legacy_partner_email and legacy_partner_email not in partner_emails:
        partner_emails.append(legacy_partner_email)
    partner_emails = [email.strip() for email in partner_emails if email and email.strip()]
    partner_emails = list(dict.fromkeys(partner_emails))

    if len(partner_emails) > MAX_PRESENTERS_PER_GROUP - 1:
        return jsonify({"error": f"Groups can have at most {MAX_PRESENTERS_PER_GROUP} presenters total"}), 400

    normalized_creator_email = str(getattr(creator, 'email', '') or '').strip().lower()
    if normalized_creator_email and any(email.lower() == normalized_creator_email for email in partner_emails):
        return jsonify({"error": "Do not include your own email as a partner email"}), 400

    new_presentation = Presentation(
        title=data['title'],
        abstract=data.get('abstract'),
        department=presentations_module._clean_text(data.get('department')),
        mentor=presentations_module._clean_text(data.get('mentor')),
        keywords=presentations_module._clean_text(data.get('keywords')),
        time=parsed_time,
        schedule_id=schedule_id
    )

    db.session.add(new_presentation)
    db.session.flush()
    presentations_module.set_show_on_schedule(new_presentation.id, data.get('show_on_schedule', True))
    if 'type' in data:
        presentations_module.set_presentation_type(new_presentation.id, data.get('type'))

    if creator:
        creator.presentation_id = new_presentation.id

    for partner_email in partner_emails:
        partner_user = User.query.filter_by(email=partner_email).first()
        if not partner_user:
            db.session.rollback()
            return jsonify({"error": f"No user found with email {partner_email}"}), 400
        if partner_user.presentation_id:
            db.session.rollback()
            return jsonify({"error": f"{partner_email} is already assigned to a presentation"}), 400
        partner_user.presentation_id = new_presentation.id

    db.session.commit()
    return jsonify(presentations_module.presentation_to_dict(new_presentation)), 201


def _zip_safe_name(value, fallback):
    """Return a readable ZIP entry name part without path separators."""
    cleaned = str(value or fallback).strip() or fallback
    cleaned = cleaned.replace('/', '-').replace('\\', '-')
    cleaned = ''.join(ch for ch in cleaned if ord(ch) >= 32)
    return cleaned or fallback


def _presenter_names_for_zip(presentation):
    """Return presenter names for ZIP filenames."""
    presenters = (
        User.query
        .filter_by(presentation_id=presentation.id)
        .order_by(User.id.asc())
        .all()
    )
    names = []
    for presenter in presenters:
        first = (presenter.firstname or '').strip()
        last = (presenter.lastname or '').strip()
        full_name = f"{first} {last}".strip()
        names.append(full_name or presenter.email)
    return ', '.join(names) or 'Unknown Presenter'


def _extension_for_uploaded_file(uploaded_name, file_data):
    """Return the best file extension for a stored presentation file."""
    uploaded_name = str(uploaded_name or '').strip()
    if '.' in uploaded_name:
        extension = uploaded_name.rsplit('.', 1)[-1].strip().lower()
        if extension:
            return extension

    if file_data.startswith(b'%PDF'):
        return 'pdf'
    if file_data.startswith(b'PK\x03\x04'):
        return 'pptx'
    return 'pptx'


def download_all_presentations_by_title():
    """Download uploaded presentation files using presenter and presentation-title filenames."""
    presentations_module.ensure_presentation_upload_table()
    zip_buffer = io.BytesIO()
    presentations = Presentation.query.order_by(Presentation.title.asc(), Presentation.id.asc()).all()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for presentation in presentations:
            file_data = presentation.presentation_file
            if not file_data:
                continue

            upload_row = db.session.execute(
                text("SELECT filename FROM presentation_uploads WHERE presentation_id = :pid"),
                {"pid": presentation.id}
            ).fetchone()
            uploaded_name = upload_row[0] if upload_row and upload_row[0] else None
            extension = _extension_for_uploaded_file(uploaded_name, file_data)
            presenter_names = _zip_safe_name(_presenter_names_for_zip(presentation), 'Unknown Presenter')
            presentation_title = _zip_safe_name(presentation.title, 'Untitled')
            filename = f"{presenter_names} - {presentation_title}.{extension}"

            zipf.writestr(filename, file_data)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="presentations.zip"
    )


def install_group_size_limit_overrides(app):
    """Install five-person group-size behavior after the API blueprints are registered."""
    if app.config.get('TESTING', False):
        return

    users_module._can_assign_presentation = _can_assign_presentation_with_five_person_limit
    app.view_functions['presentations.create_presentation'] = create_presentation_with_five_person_limit
    app.view_functions['presentations.update_presentation'] = update_presentation_with_lightweight_response
    app.view_functions['presentations.download_all_presentations'] = download_all_presentations_by_title
    app.add_url_rule(
        '/api/v1/presentations/download-all-named',
        'download_all_presentations_named',
        download_all_presentations_by_title,
        methods=['GET']
    )
