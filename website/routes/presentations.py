'''
API endpoints for managing presentations.

'''
import base64
import io
import os
import uuid
import zipfile
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request, session, send_file
from sqlalchemy import text
from werkzeug.utils import secure_filename

from website.models import BlockSchedule, Presentation, User
from website import db

presentations_bp = Blueprint('presentations', __name__)

VALID_PRESENTATION_TYPES = {'Presentation', 'Blitz', 'Poster'}


def ensure_presentation_visibility_table():
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


def ensure_presentation_type_table():
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


def ensure_abstract_image_table():
    """Create the persistent abstract image table if it does not exist."""
    with db.engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS abstract_images (
                id VARCHAR(64) PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                mime_type VARCHAR(120) NOT NULL,
                data_base64 TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))


def ensure_presentation_upload_table():
    """Create table for persistent uploaded presentation metadata."""
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


def normalize_presentation_type(value):
    """Normalize a submitted presentation type."""
    if value is None:
        return None
    cleaned = str(value).strip()
    for valid_type in VALID_PRESENTATION_TYPES:
        if cleaned.lower() == valid_type.lower():
            return valid_type
    return None


def get_show_on_schedule(presentation_id):
    """Return whether a presentation should show on public schedule/program views."""
    ensure_presentation_visibility_table()
    row = db.session.execute(
        text("SELECT show_on_schedule FROM presentation_visibility WHERE presentation_id = :pid"),
        {"pid": presentation_id}
    ).fetchone()
    return bool(row[0]) if row else True


def set_show_on_schedule(presentation_id, value):
    """Persist per-presentation visibility."""
    ensure_presentation_visibility_table()
    result = db.session.execute(
        text("UPDATE presentation_visibility SET show_on_schedule = :value WHERE presentation_id = :pid"),
        {"pid": presentation_id, "value": bool(value)}
    )
    if result.rowcount == 0:
        db.session.execute(
            text("INSERT INTO presentation_visibility (presentation_id, show_on_schedule) VALUES (:pid, :value)"),
            {"pid": presentation_id, "value": bool(value)}
        )


def get_presentation_type(presentation):
    """Return the per-presentation type override, falling back to its schedule block type."""
    if not presentation or not presentation.id:
        return None

    ensure_presentation_type_table()
    row = db.session.execute(
        text("SELECT presentation_type FROM presentation_types WHERE presentation_id = :pid"),
        {"pid": presentation.id}
    ).fetchone()
    if row and row[0]:
        return normalize_presentation_type(row[0]) or row[0]

    if presentation.schedule and presentation.schedule.block_type:
        return normalize_presentation_type(presentation.schedule.block_type) or presentation.schedule.block_type

    return None


def set_presentation_type(presentation_id, value):
    """Persist per-presentation type. Empty/invalid values remove the override."""
    ensure_presentation_type_table()
    normalized = normalize_presentation_type(value)
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


def effective_presentation_time(presentation):
    """Return the presentation's display time, including block offset when available."""
    if presentation.schedule and presentation.schedule.start_time:
        num = presentation.num_in_block if presentation.num_in_block is not None else 0
        sub = presentation.schedule.sub_length if presentation.schedule.sub_length is not None else 0
        try:
            return presentation.schedule.start_time + timedelta(minutes=(int(num) * int(sub)))
        except (TypeError, ValueError):
            return presentation.schedule.start_time
    return presentation.time


def program_type_prefix(presentation):
    """Return the program identifier prefix for a presentation."""
    presentation_type = get_presentation_type(presentation) or ''
    value = presentation_type.strip().lower()
    if value == 'poster':
        return 'poster'
    if value == 'blitz':
        return 'blitz'
    return 'presentation'


def _program_sort_key(presentation):
    """Sort presentations consistently before assigning program identifiers."""
    display_time = effective_presentation_time(presentation) or datetime.max
    schedule_id = presentation.schedule_id if presentation.schedule_id is not None else 0
    num_in_block = presentation.num_in_block if presentation.num_in_block is not None else 10**9
    return (display_time, schedule_id, num_in_block, presentation.id or 0)


def _program_identifier_map(presentations):
    """Return continuous IDs by presentation type across all schedule blocks."""
    counters = {}
    identifiers = {}
    for presentation in sorted(presentations, key=_program_sort_key):
        prefix = program_type_prefix(presentation)
        counters[prefix] = counters.get(prefix, 0) + 1
        identifiers[presentation.id] = f"{prefix}-{counters[prefix]}"
    return identifiers


def program_identifier_for(presentation):
    """Return an identifier like poster-1, blitz-3, or presentation-7."""
    if not presentation or not presentation.id:
        return None

    presentations = Presentation.query.outerjoin(Presentation.schedule).all()
    visible_presentations = [p for p in presentations if get_show_on_schedule(p.id)]

    if presentation.id not in {p.id for p in visible_presentations}:
        visible_presentations.append(presentation)

    identifiers = _program_identifier_map(visible_presentations)
    return identifiers.get(presentation.id, f"{program_type_prefix(presentation)}-{presentation.id}")


def presentation_to_dict(presentation):
    """Serialize a presentation and include program metadata."""
    data = presentation.to_dict()
    calculated_time = effective_presentation_time(presentation)
    if calculated_time:
        data["time"] = calculated_time.strftime('%Y-%m-%dT%H:%M:%S')
    data["type"] = get_presentation_type(presentation)
    data["program_identifier"] = program_identifier_for(presentation)
    data["schedule_title"] = presentation.schedule.title if presentation.schedule else None
    data["show_on_schedule"] = get_show_on_schedule(presentation.id)

    ensure_presentation_upload_table()
    row = db.session.execute(
        text("SELECT filename FROM presentation_uploads WHERE presentation_id = :pid"),
        {"pid": presentation.id}
    ).fetchone()
    data["uploaded_presentation_filename"] = row[0] if row else None
    return data


def _user_full_name(user):
    """Return a display name for a user."""
    first = (user.firstname or '').strip()
    last = (user.lastname or '').strip()
    full_name = f"{first} {last}".strip()
    return full_name or user.email


def _format_program_time(value):
    """Format a datetime for the program quick-view table."""
    if not value:
        return '-'
    try:
        return value.strftime('%b %-d, %-I:%M %p')
    except ValueError:
        return value.strftime('%b %d, %I:%M %p')


def _meal_type_for_block(block):
    """Return lunch/dinner when a non-presentation block is a meal block."""
    marker = f"{block.title or ''} {block.block_type or ''}".lower()
    if 'lunch' in marker:
        return 'lunch'
    if 'dinner' in marker:
        return 'dinner'
    return None


def program_table_rows():
    """Return rows for the program quick-view table."""
    presentations = (
        Presentation.query
        .outerjoin(Presentation.schedule)
        .filter(
            (Presentation.schedule_id.is_(None)) | (Presentation.schedule.has(is_presentation=True))
        )
        .all()
    )
    presentations = [p for p in presentations if get_show_on_schedule(p.id)]
    identifiers = _program_identifier_map(presentations)

    rows = []
    for presentation in presentations:
        presenters = User.query.filter_by(presentation_id=presentation.id).all()
        authors = ', '.join(_user_full_name(presenter) for presenter in presenters) or '-'
        display_time = effective_presentation_time(presentation)
        rows.append({
            "sort_time": display_time or datetime.max,
            "time": _format_program_time(display_time),
            "id": identifiers.get(presentation.id, '-'),
            "authors": authors,
            "title": presentation.title or 'Untitled',
            "kind": "presentation",
            "event_type": None,
        })

    meal_blocks = BlockSchedule.query.filter(BlockSchedule.is_presentation.is_(False)).all()
    for block in meal_blocks:
        event_type = _meal_type_for_block(block)
        if not event_type:
            continue
        rows.append({
            "sort_time": block.start_time or datetime.max,
            "time": _format_program_time(block.start_time),
            "id": "",
            "authors": event_type,
            "title": block.title or event_type.title(),
            "kind": "event",
            "event_type": event_type,
        })

    rows.sort(key=lambda row: (row["sort_time"], row["id"], row["title"]))
    for row in rows:
        row.pop("sort_time", None)
    return rows


@presentations_bp.route('/', methods=['GET'])
def get_presentations():
    ''' GET all presentations '''
    presentations = Presentation.query.order_by(Presentation.id.asc()).all()
    return jsonify([presentation_to_dict(p) for p in presentations])


@presentations_bp.route('/program-table', methods=['GET'])
def get_program_table():
    """Return rows for the first-page program quick-view table."""
    return jsonify(program_table_rows())


@presentations_bp.route('/<int:presentation_id>', methods=['GET'])
def get_presentation(presentation_id):
    ''' GET one presentation '''
    presentation = Presentation.query.get_or_404(presentation_id)
    return jsonify(presentation_to_dict(presentation))


@presentations_bp.route('/', methods=['POST'])
def create_presentation():

    data = request.get_json() or {}
    schedule_id = data.get('schedule_id') or data.get('block_id')
    time_str = data.get('time')

    parsed_time = None
    if time_str:
        try:
            parsed_time = datetime.fromisoformat(time_str)
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use ISO 8601."}), 400

    new_presentation = Presentation(
        title=data['title'],
        abstract=data.get('abstract'),
        subject=data.get('subject'),
        time=parsed_time,
        schedule_id=schedule_id
    )

    db.session.add(new_presentation)
    db.session.flush()
    set_show_on_schedule(new_presentation.id, data.get('show_on_schedule', True))
    if 'type' in data:
        set_presentation_type(new_presentation.id, data.get('type'))

    partner_email = data.get("partner_email")
    if partner_email:
        partner_user = User.query.filter_by(email=partner_email).first()
        if not partner_user:
            db.session.rollback()
            return jsonify({"error": f"No user found with email {partner_email}"}), 400

        partner_user.presentation_id = new_presentation.id

    db.session.commit()
    return jsonify(presentation_to_dict(new_presentation)), 201


@presentations_bp.route('/<int:presentation_id>', methods=['PUT'])
def update_presentation(presentation_id):
    ''' PUT update presentation '''
    presentation = Presentation.query.get_or_404(presentation_id)
    data = request.get_json() or {}

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

    presentation.title = data.get('title', presentation.title)
    presentation.abstract = data.get('abstract', presentation.abstract)
    presentation.subject = data.get('subject', presentation.subject)
    presentation.presentation_file = data.get('presentation_file', presentation.presentation_file)

    if 'show_on_schedule' in data:
        set_show_on_schedule(presentation.id, data.get('show_on_schedule'))

    if 'type' in data:
        set_presentation_type(presentation.id, data.get('type'))

    db.session.commit()
    return jsonify(presentation_to_dict(presentation))


@presentations_bp.route('/<int:presentation_id>', methods=['DELETE'])
def delete_presentation(presentation_id):
    ''' DELETE presentation '''
    presentation = Presentation.query.get_or_404(presentation_id)
    db.session.delete(presentation)
    ensure_presentation_visibility_table()
    ensure_presentation_type_table()
    ensure_presentation_upload_table()
    db.session.execute(
        text("DELETE FROM presentation_visibility WHERE presentation_id = :pid"),
        {"pid": presentation_id}
    )
    db.session.execute(
        text("DELETE FROM presentation_types WHERE presentation_id = :pid"),
        {"pid": presentation_id}
    )
    db.session.execute(
        text("DELETE FROM presentation_uploads WHERE presentation_id = :pid"),
        {"pid": presentation_id}
    )
    db.session.commit()
    return jsonify({"message": "Presentation deleted"})


@presentations_bp.route('/recent', methods=['GET'])
def get_recent_presentations():
    """Return upcoming presentations sorted by effective presentation time."""
    now = datetime.now()

    candidates = (
        Presentation.query
        .join(Presentation.schedule)
        .filter(BlockSchedule.is_presentation.is_(True))
        .all()
    )
    candidates = [p for p in candidates if get_show_on_schedule(p.id)]
    candidates = [p for p in candidates if (effective_presentation_time(p) or datetime.max) >= now]
    candidates.sort(key=lambda p: effective_presentation_time(p) or datetime.max)

    return jsonify([presentation_to_dict(p) for p in candidates])


@presentations_bp.route('/type/<string:category>', methods=['GET'])
def get_presentations_by_type(category):
    """Return all presentations of a given type (Poster, Blitz, Presentation)."""
    requested_type = normalize_presentation_type(category)
    if not requested_type:
        return jsonify(
            {"error": f"Invalid type '{category}'. Must be one of {list(VALID_PRESENTATION_TYPES)}."}), 400

    results = (
        Presentation.query
        .outerjoin(Presentation.schedule)
        .filter(
            (Presentation.schedule_id.is_(None)) | (Presentation.schedule.has(is_presentation=True))
        )
        .all()
    )
    results = [p for p in results if get_show_on_schedule(p.id)]
    results = [p for p in results if (get_presentation_type(p) or '').lower() == requested_type.lower()]
    results.sort(key=lambda p: effective_presentation_time(p) or datetime.max)

    return jsonify([presentation_to_dict(p) for p in results])


@presentations_bp.route("/day/<string:day>")
def get_presentations_by_day(day):
    '''
    Get all presentations for a specific day, grouped by presentation blocks.
    Non-presentation schedule blocks (where is_presentation=False) are excluded.
    '''
    blocks = BlockSchedule.query.filter(
        BlockSchedule.day == day,
        BlockSchedule.is_presentation == True).all()
    result = []
    for block in blocks:
        presentations = (
            Presentation.query.filter_by(schedule_id=block.id)
            .order_by(
                Presentation.num_in_block.asc().nullsfirst(),
                Presentation.id.asc())
            .all())
        presentations = [p for p in presentations if get_show_on_schedule(p.id)]
        result.append({
            "block": block.to_dict(),
            "presentations": [presentation_to_dict(p) for p in presentations]
        })
    return jsonify(result)


@presentations_bp.route('/order', methods=['POST'])
def update_presentations_order():
    """Accepts JSON: { orders: [{ presentation_id, schedule_id, num_in_block }, ...] }"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({"error": "forbidden", "reason": "organizer_required"}), 403
    email = user_info.get('email')
    if not email:
        return jsonify({"error": "forbidden", "reason": "organizer_required"}), 403
    db_user = User.query.filter_by(email=email).first()
    if not db_user or db_user.auth != 'organizer':
        return jsonify({"error": "forbidden", "reason": "organizer_required"}), 403

    data = request.get_json() or {}
    orders = data.get('orders')
    if not orders or not isinstance(orders, list):
        return jsonify({"error": "Invalid payload; expected 'orders' list."}), 400

    updated = []
    for item in orders:
        pid = item.get('presentation_id')
        num = item.get('num_in_block')
        schedule_id = item.get('schedule_id')
        if pid is None or num is None or schedule_id is None:
            continue

        presentation = db.session.get(Presentation, pid)
        block = db.session.get(BlockSchedule, schedule_id)
        if not presentation or not block:
            continue

        presentation.schedule_id = block.id
        presentation.num_in_block = int(num)
        updated.append(presentation.id)

    try:
        db.session.commit()
    except (TypeError, ValueError) as e:
        db.session.rollback()
        return jsonify({"error": "Failed to save order", "details": str(e)}), 500

    return jsonify({"ok": True, "updated": updated})


@presentations_bp.route('/<int:presentation_id>/upload/latest', methods=['GET'])
def latest_presentation_upload(presentation_id):
    """Return the latest uploaded file name for a presentation."""
    Presentation.query.get_or_404(presentation_id)
    ensure_presentation_upload_table()
    row = db.session.execute(
        text("SELECT filename FROM presentation_uploads WHERE presentation_id = :pid"),
        {"pid": presentation_id}
    ).fetchone()
    return jsonify({"filename": row[0] if row else None})


@presentations_bp.route('/<int:presentation_id>/upload', methods=['POST'])
def upload_presentation_file(presentation_id):
    """Upload a PPT, PPTX, or PDF file for a presentation."""
    presentation = Presentation.query.get_or_404(presentation_id)

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    allowed = {'ppt', 'pptx', 'pdf'}
    if extension not in allowed:
        return jsonify({"error": "Invalid file type. Upload a PPT, PPTX, or PDF file."}), 400

    file_data = file.read()
    if len(file_data) > 20 * 1024 * 1024:
        return jsonify({"error": "File exceeds 20MB"}), 400

    presentation.presentation_file = file_data
    ensure_presentation_upload_table()
    updated = db.session.execute(
        text("UPDATE presentation_uploads SET filename = :filename, uploaded_at = CURRENT_TIMESTAMP WHERE presentation_id = :pid"),
        {"pid": presentation.id, "filename": filename}
    )
    if updated.rowcount == 0:
        db.session.execute(
            text("INSERT INTO presentation_uploads (presentation_id, filename) VALUES (:pid, :filename)"),
            {"pid": presentation.id, "filename": filename}
        )
    db.session.commit()

    return jsonify({"message": "File uploaded successfully", "filename": filename})


@presentations_bp.route('/abstract-images', methods=['POST'])
def upload_abstract_images():
    """Upload one or more abstract images and return stable public URLs."""
    user_info = session.get('user')
    if not user_info:
        return jsonify({"error": "Authentication required"}), 401

    email = user_info.get('email')
    if not email:
        return jsonify({"error": "Authentication required"}), 401

    db_user = User.query.filter_by(email=email).first()
    if not db_user:
        return jsonify({"error": "Authentication required"}), 401

    files = request.files.getlist('files') or request.files.getlist('files[]')
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    ensure_abstract_image_table()
    uploaded = []
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

    for file in files:
        if not file or file.filename == '':
            continue

        filename = secure_filename(file.filename)
        extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if extension not in allowed_extensions:
            return jsonify({"error": f"Unsupported image type: {file.filename}"}), 400

        raw_data = file.read()
        if len(raw_data) > 10 * 1024 * 1024:
            return jsonify({"error": f"Image is too large: {file.filename}"}), 400

        image_id = uuid.uuid4().hex
        mime_type = file.mimetype or f"image/{extension or 'png'}"
        db.session.execute(
            text("""
                INSERT INTO abstract_images (id, filename, mime_type, data_base64)
                VALUES (:id, :filename, :mime_type, :data_base64)
            """),
            {
                "id": image_id,
                "filename": filename,
                "mime_type": mime_type,
                "data_base64": base64.b64encode(raw_data).decode('ascii'),
            }
        )
        uploaded.append({
            "filename": filename,
            "url": f"/api/v1/presentations/abstract-images/{image_id}",
        })

    if not uploaded:
        return jsonify({"error": "No valid image files uploaded"}), 400

    db.session.commit()
    return jsonify({"uploaded": uploaded})


@presentations_bp.route('/abstract-images/<string:image_id>', methods=['GET'])
def get_abstract_image(image_id):
    """Serve a persisted abstract image by id."""
    ensure_abstract_image_table()
    row = db.session.execute(
        text("SELECT filename, mime_type, data_base64 FROM abstract_images WHERE id = :id"),
        {"id": image_id}
    ).fetchone()
    if not row:
        return jsonify({"error": "Image not found"}), 404

    filename, mime_type, data_base64 = row
    raw_data = base64.b64decode(data_base64)
    return send_file(
        io.BytesIO(raw_data),
        mimetype=mime_type,
        as_attachment=False,
        download_name=filename
    )


@presentations_bp.route('/download-all', methods=['GET'])
def download_all_presentations():
    """
    Download all presentations as a ZIP, ordered by Presentation.time.
    """
    ensure_presentation_upload_table()
    zip_buffer = io.BytesIO()
    presentations = Presentation.query.order_by(Presentation.time.asc()).all()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for pres in presentations:
            if not pres.presentation_file:
                continue

            upload_row = db.session.execute(
                text("SELECT filename FROM presentation_uploads WHERE presentation_id = :pid"),
                {"pid": pres.id}
            ).fetchone()
            safe_title = "".join(c for c in pres.title if c.isalnum() or c in (" ", "_", "-")).strip()
            timestamp = pres.time.strftime("%Y-%m-%d_%H%M") if pres.time else "no_time"
            uploaded_name = secure_filename(upload_row[0]) if upload_row and upload_row[0] else None
            extension = uploaded_name.rsplit('.', 1)[-1].lower() if uploaded_name and '.' in uploaded_name else 'pptx'
            filename = f"{timestamp} - {safe_title}.{extension}"

            zipf.writestr(filename, pres.presentation_file)

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="presentations.zip"
    )