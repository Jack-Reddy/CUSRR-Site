from flask import Blueprint, jsonify, request, render_template
from models import db, Presentation

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
    new_presentation = Presentation(
        title=data['title'],
        abstract=data.get('abstract'),
        subject=data.get('subject'),
        time=data.get('time'),
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
    presentation.title = data.get('title', presentation.title)
    presentation.abstract = data.get('abstract', presentation.abstract)
    presentation.subject = data.get('subject', presentation.subject)
    presentation.time = data.get('time', presentation.time)
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

# Presentations sorted by time
@presentations_bp.route('/recent', methods=['GET'])
def get_recent_presentations():
    presentations = Presentation.query.order_by(Presentation.time.desc()).all()
    return jsonify([p.to_dict() for p in presentations])
