'''
API endpoints for managing presentations.

'''
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session, send_file
from sqlalchemy import func
import io
import zipfile

from website.models import BlockSchedule, Presentation, User
from website import db

import io
import zipfile

presentations_bp = Blueprint('presentations', __name__)


@presentations_bp.route('/', methods=['GET'])
def get_presentations():
    ''' GET all presentations '''
    presentations = Presentation.query.all()
    return jsonify([p.to_dict() for p in presentations])




@presentations_bp.route('/<int:presentation_id>', methods=['GET'])
def get_presentation(presentation_id):
    ''' GET one presentation '''
    presentation = Presentation.query.get_or_404(presentation_id)
    return jsonify(presentation.to_dict())


@presentations_bp.route('/', methods=['POST'])
def create_presentation():
    ''' POST create presentation '''
    data = request.get_json()
    time_str = data.get('time')
    try:
        presentation_time = datetime.fromisoformat(time_str)
    except ValueError:
        return jsonify(
            {"error": "Invalid datetime format. Use ISO 8601."}), 400
    new_presentation = Presentation(
        title=data['title'],
        abstract=data.get('abstract'),
        subject=data.get('subject'),
        time=presentation_time
    )

    db.session.add(new_presentation)
    db.session.commit()
    return jsonify(new_presentation.to_dict()), 201


@presentations_bp.route('/<int:presentation_id>', methods=['PUT'])
def update_presentation(presentation_id):
    ''' PUT update presentation '''
    presentation = Presentation.query.get_or_404(presentation_id)
    data = request.get_json()

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
    db.session.commit()
    return jsonify(presentation.to_dict())



@presentations_bp.route('/<int:presentation_id>', methods=['DELETE'])
def delete_presentation(presentation_id):
    ''' DELETE presentation '''
    presentation = Presentation.query.get_or_404(presentation_id)
    db.session.delete(presentation)
    db.session.commit()
    return jsonify({"message": "Presentation deleted"})


@presentations_bp.route('/recent', methods=['GET'])
def get_recent_presentations():
    """Return upcoming presentations sorted by Presentation.time first, 
    then BlockSchedule.start_time.
    Fetch candidates where either the explicit time or the block start time
    is in the future
    """
    now = datetime.now()

    candidates = (
        Presentation.query .join(
            Presentation.schedule) .filter(
            func.coalesce(
                Presentation.time,
                BlockSchedule.start_time) >= now) .all())

    def effective_time(pres):
        '''If presentation has explicit time, use it'''
        if pres.time:
            return pres.time
        # Otherwise, attempt to compute from schedule start + num_in_block *
        # sub_length (in minutes)
        sched = pres.schedule
        if sched and sched.start_time:
            num = pres.num_in_block if pres.num_in_block is not None else 0
            sub = sched.sub_length if sched.sub_length is not None else 0
            try:
                return sched.start_time + \
                    timedelta(minutes=(int(num) * int(sub)))
            except (TypeError, ValueError):
                return sched.start_time
        return None

    # Attach effective times and sort in Python to ensure correct ordering
    # even when computed
    decorated = [(pres, effective_time(pres) or datetime.max)
                 for pres in candidates]
    decorated.sort(key=lambda t: t[1])
    ordered = [p for p, _ in decorated]

    return jsonify([p.to_dict() for p in ordered])


@presentations_bp.route('/type/<string:category>', methods=['GET'])
def get_presentations_by_type(category):
    """Return all presentations of a given type (Poster, Blitz, Presentation)."""
    valid_types = {"poster", "presentation", "blitz"}

    # normalize input
    category_lower = category.strip().lower()
    if category_lower not in valid_types:
        return jsonify(
            {"error": f"Invalid type '{category}'. Must be one of {list(valid_types)}."}), 400

    # use the block_type field on BlockSchedule (may be stored lowercase)
    formatted_type = category_lower

    # join the schedule table and filter by its block_type column
    # order by the effective time: explicit Presentation.time or the
    # BlockSchedule.start_time
    results = (
        Presentation.query .join(
            Presentation.schedule) .filter(
            BlockSchedule.block_type.ilike(formatted_type)) .order_by(
                func.coalesce(
                    Presentation.time,
                    BlockSchedule.start_time).asc()) .all())

    return jsonify([p.to_dict() for p in results])


@presentations_bp.route("/day/<string:day>")
def get_presentations_by_day(day):
    '''
    Get all presentations for a specific day, grouped by poster blocks.
    :param day: The day to filter presentations by (e.g., "Day 1")
    '''
    blocks = BlockSchedule.query.filter_by(day=day, block_type='poster').all()
    result = []
    for block in blocks:
        # Order presentations by `num_in_block` if set, otherwise fallback to
        # id
        presentations = (
            Presentation.query .filter_by(
                schedule_id=block.id) .order_by(
                Presentation.num_in_block.asc().nullsfirst(),
                Presentation.id.asc()) .all())
        result.append({
            "block": block.to_dict(),
            "presentations": [p.to_dict() for p in presentations]
        })
    return jsonify(result)


@presentations_bp.route('/order', methods=['POST'])
def update_presentations_order():
    """Accepts JSON: { orders: [{ presentation_id, schedule_id, num_in_block }, ...] }
    Updates Presentation.num_in_block for each provided presentation.
    """
    # Organizer-only check (inline to avoid circular imports)
    user_info = session.get('user')
    if not user_info:
        return jsonify(
            {"error": "forbidden", "reason": "organizer_required"}), 403
    email = user_info.get('email')
    if not email:
        return jsonify(
            {"error": "forbidden", "reason": "organizer_required"}), 403
    db_user = User.query.filter_by(email=email).first()
    if not db_user or db_user.auth != 'organizer':
        return jsonify(
            {"error": "forbidden", "reason": "organizer_required"}), 403

    data = request.get_json() or {}
    orders = data.get('orders')
    if not orders or not isinstance(orders, list):
        return jsonify(
            {"error": "Invalid payload; expected 'orders' list."}), 400

    updated = []
    for item in orders:
        pid = item.get('presentation_id')
        num = item.get('num_in_block')
        if pid is None or num is None:
            continue
        presentation = db.session.get(Presentation, pid)
        if not presentation:
            continue
        presentation.num_in_block = int(num)
        updated.append(presentation.id)

    try:
        db.session.commit()
    except (TypeError, ValueError) as e:
        db.session.rollback()
        return jsonify(
            {"error": "Failed to save order", "details": str(e)}), 500

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

    # Validate extension
    allowed = ['ppt', 'pptx']
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        return jsonify({"error": "Invalid file type"}), 400

    # Read binary content
    file_data = file.read()
    if len(file_data) > 20 * 1024 * 1024:  # 20MB
        return jsonify({"error": "File exceeds 20MB"}), 400

    # Store in DB
    presentation.presentation_file = file_data
    db.session.commit()

    return jsonify({"message": "File uploaded successfully"})


@presentations_bp.route('/download-all', methods=['GET'])
def download_all_presentations():
    """
    Download all presentations as a ZIP, ordered by Presentation.time.
    """
    # In-memory buffer for ZIP
    zip_buffer = io.BytesIO()

    # Fetch presentations ordered by time
    presentations = Presentation.query.order_by(Presentation.time.asc()).all()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for pres in presentations:
            if not pres.presentation_file:
                continue  # skip presentations with no uploaded file

            # Sanitize filename
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
