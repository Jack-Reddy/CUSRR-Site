from flask import Blueprint, jsonify, request
from models import db, Presentation
from datetime import datetime
from sqlalchemy.exc import IntegrityError

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
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    # Validate required field
    if 'title' not in data or not data['title']:
        return jsonify({"error": "Missing required field: title"}), 400
    
    # Parse time if provided
    time_obj = None
    if data.get('time'):
        try:
            # Try parsing ISO format datetime string
            time_obj = datetime.fromisoformat(data['time'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return jsonify({"error": "Invalid time format. Use ISO 8601 format"}), 400
    
    try:
        new_presentation = Presentation(
            title=data['title'],
            abstract=data.get('abstract'),
            subject=data.get('subject'),
            time=time_obj,
            room=data.get('room'),
            type=data.get('type')
        )
        db.session.add(new_presentation)
        db.session.commit()
        return jsonify(new_presentation.to_dict()), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create presentation"}), 500

# PUT update presentation
@presentations_bp.route('/<int:id>', methods=['PUT'])
def update_presentation(id):
    presentation = Presentation.query.get_or_404(id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    # Parse time if provided
    if 'time' in data and data['time']:
        try:
            time_obj = datetime.fromisoformat(data['time'].replace('Z', '+00:00'))
            presentation.time = time_obj
        except (ValueError, AttributeError):
            return jsonify({"error": "Invalid time format. Use ISO 8601 format"}), 400
    
    try:
        presentation.title = data.get('title', presentation.title)
        presentation.abstract = data.get('abstract', presentation.abstract)
        presentation.subject = data.get('subject', presentation.subject)
        presentation.room = data.get('room', presentation.room)
        presentation.type = data.get('type', presentation.type)
        db.session.commit()
        return jsonify(presentation.to_dict())
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update presentation"}), 500

# DELETE presentation
@presentations_bp.route('/<int:id>', methods=['DELETE'])
def delete_presentation(id):
    presentation = Presentation.query.get_or_404(id)
    try:
        db.session.delete(presentation)
        db.session.commit()
        return jsonify({"message": "Presentation deleted"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete presentation"}), 500

@presentations_bp.route('/recent', methods=['GET'])
def get_recent_presentations():
    """Return upcoming presentations sorted by soonest first."""
    now = datetime.now()

    presentations = (
        Presentation.query
        .filter(Presentation.time >= now)
        .order_by(Presentation.time.asc())
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
