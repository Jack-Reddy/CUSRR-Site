from flask import Blueprint, jsonify, request, render_template
from models import BlockSchedule, db, Presentation
from datetime import datetime
from sqlalchemy import func

presentations_bp = Blueprint('presentations', __name__)

# GET all presentations
@presentations_bp.route('/', methods=['GET'])
def get_presentations():
    presentations = Presentation.query.all()
    return jsonify([p.to_dict() for p in presentations])

# GET one presentation
@presentations_bp.route('/<int:id>', methods=['GET'])
def get_presentation(id):
    presentation = Presentation.query.get_or_404(id)
    return jsonify(presentation.to_dict())

# POST create presentation
@presentations_bp.route('/', methods=['POST'])
def create_presentation():
    data = request.get_json()
    time_str = data.get('time')
    try:
        presentation_time = datetime.fromisoformat(time_str)
    except ValueError:
        return jsonify({"error": "Invalid datetime format. Use ISO 8601."}), 400
    new_presentation = Presentation(
        title=data['title'],
        abstract=data.get('abstract'),
        subject=data.get('subject'),
        time=presentation_time,
        room=data.get('room'),
        type=data.get('type')
    )
    db.session.add(new_presentation)
    db.session.commit()
    return jsonify(new_presentation.to_dict()), 201

# PUT update presentation
@presentations_bp.route('/<int:id>', methods=['PUT'])
def update_presentation(id):
    presentation = Presentation.query.get_or_404(id)
    data = request.get_json()
    time_str = data.get('time')
    if time_str:
        try:
            presentation_time = datetime.fromisoformat(time_str)
        except ValueError:
            return jsonify({"error": "Invalid datetime format. Use ISO 8601."}), 400
    presentation.title = data.get('title', presentation.title)
    presentation.abstract = data.get('abstract', presentation.abstract)
    presentation.subject = data.get('subject', presentation.subject)
    presentation.room = data.get('room', presentation.room)
    presentation.type = data.get('type', presentation.type)
    db.session.commit()
    return jsonify(presentation.to_dict())

# DELETE presentation
@presentations_bp.route('/<int:id>', methods=['DELETE'])
def delete_presentation(id):
    presentation = Presentation.query.get_or_404(id)
    db.session.delete(presentation)
    db.session.commit()
    return jsonify({"message": "Presentation deleted"})

@presentations_bp.route('/recent', methods=['GET'])
def get_recent_presentations():
    """Return upcoming presentations sorted by Presentation.time first, then BlockSchedule.start_time."""
    now = datetime.now()

    presentations = (
        Presentation.query
        .join(Presentation.schedule)  # assuming one-to-one or many-to-one relationship
        .filter(
            func.coalesce(Presentation.time, BlockSchedule.start_time) >= now
        )
        .order_by(
            func.coalesce(Presentation.time, BlockSchedule.start_time).asc()
        )
        .all()
    )

    return jsonify([p.to_dict() for p in presentations])

@presentations_bp.route('/type/<string:category>', methods=['GET'])
def get_presentations_by_type(category):
    """Return all presentations of a given type (Poster, Blitz, Presentation)."""
    valid_types = {"poster", "presentation", "blitz"}

    # normalize input
    category_lower = category.strip().lower()
    if category_lower not in valid_types:
        return jsonify({"error": f"Invalid type '{category}'. Must be one of {list(valid_types)}."}), 400

    # fix capitalization
    formatted_type = category_lower.capitalize()

    # get the presentations
    results = (
        Presentation.query
        .filter(Presentation.type.ilike(formatted_type))
        .order_by(Presentation.time.asc())
        .all()
    )

    return jsonify([p.to_dict() for p in results])
