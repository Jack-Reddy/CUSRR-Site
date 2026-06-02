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
from sqlalchemy import func, text
from werkzeug.utils import secure_filename

from website.models import BlockSchedule, Presentation, User
from website import db

presentations_bp = Blueprint('presentations', __name__)


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


def presentation_to_dict(presentation):
    """Serialize a presentation and include its per-presentation visibility flag."""
    data = presentation.to_dict()
    data["show_on_schedule"] = get_show_on_schedule(presentation.id)
    return data


@presentations_bp.route('/', methods=['GET'])
def get_presentations():
    ''' GET all presentations '''
    presentations = Presentation.query.order_by(Presentation.id.asc()).all()
    return jsonify([presentation_to_dict(p) for p in presentations])


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

    if time_str:
        try:
            datetime.fromisoformat(time_str)
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use ISO 8601."}), 400

    new_presentation = Presentation(
        title=data['title'],
        abstract=data.get('abstract'),
        subject=data.get('subject'),
        schedule_id=schedule_id
    )

    db.session.add(new_presentation)
    db.session.flush()
    set_show_on_schedule(new_presentation.id, data.get('show_on_schedule', True))

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

    db.session.commit()
    return jsonify(presentation_to_dict(presentation))


@presentations_bp.route('/<int:presentation_id>', methods=['DELETE'])
def delete_presentation(presentation_id):
    ''' DELETE presentation '''
    presentation = Presentation.query.get_or_404(presentation_id)
    db.session.delete(presentation)
    ensure_presentation_visibility_table()
    db.session.execute(
        text("DELETE FROM presentation_visibility WHERE presentation_id = :pid"),
        {"pid": presentation_id}
    )
    db.session.commit()
    return jsonify({"message": "Presentation deleted"})


@presentations_bp.route('/recent', methods=['GET'])
def get_recent_presentations():
    """Return upcoming presentations sorted by Presentation.time first, then BlockSchedule.start_time."""
    now = datetime.now()

    candidates = (
        Presentation.query
        .join(Presentation.schedule)
        .filter(
            BlockSchedule.is_presentation.is_(True),
            func.coalesce(Presentation.time, BlockSchedule.start_time) >= now
        )
        .all()
    )
    candidates = [p for p in candidates if get_show_on_schedule(p.id)]

    def effective_time(pres):
        sched = pres.schedule
        if sched and sched.start_time:
            num = pres.num_in_block if pres.num_in_block is not None else 0
            sub = sched.sub_length if sched.sub_length is not None else 0
            try:
                return sched.start_time + timedelta(minutes=(int(num) * int(sub)))
            except (TypeError, ValueError):
                return sched.start_time
        return None

    decorated = [(pres, effective_time(pres) or datetime.max) for pres in candidates]
    decorated.sort(key=lambda t: t[1])
    ordered = [p for p, _ in decorated]

    return jsonify([presentation_to_dict(p) for p in ordered])


@presentations_bp.route('/type/<string:category>', methods=['GET'])
def get_presentations_by_type(category):
    """Return all presentations of a given type (Poster, Blitz, Presentation)."""
    valid_types = {"Poster", "Presentation", "Blitz"}

    category_lower = category.strip()
    if category_lower not in valid_types:
        return jsonify(
            {"error": f"Invalid type '{category}'. Must be one of {list(valid_types)}."}), 400

    results = (
        Presentation.query
        .join(Presentation.schedule)
        .filter(
            BlockSchedule.is_presentation.is_(True),
            BlockSchedule.block_type.ilike(category_lower)
        )
        .order_by(func.coalesce(Presentation.time, BlockSchedule.start_time).asc())
        .all()
    )
    results = [p for p in results if get_show_on_schedule(p.id)]

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


@presentations_bp.route('/<int:presentation_id>/upload', methods=['POST'])
def upload_presentation_file(presentation_id):
    """Upload a PPT or PPTX file for a presentation."""
    presentation = Presentation.query.get_or_404(presentation_id)

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    allowed = ['ppt', 'pptx']
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        return jsonify({"error": "Invalid file type"}), 400

    file_data = file.read()
    if len(file_data) > 20 * 1024 * 1024:
        return jsonify({"error": "File exceeds 20MB"}), 400

    presentation.presentation_file = file_data
    db.session.commit()

    return jsonify({"message": "File uploaded successfully"})


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
    zip_buffer = io.BytesIO()
    presentations = Presentation.query.order_by(Presentation.time.asc()).all()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for pres in presentations:
            if not pres.presentation_file:
                continue

            safe_title = "".join(c for c in pres.title if c.isalnum() or c in (" ", "_", "-")).strip()
            timestamp = pres.time.strftime("%Y-%m-%d_%H%M") if pres.time else "no_time"
            filename = f"{timestamp} - {safe_title}.pptx"

            zipf.writestr(filename, pres.presentation_file)

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="presentations.zip"
    )
