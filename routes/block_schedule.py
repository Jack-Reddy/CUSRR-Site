from flask import Blueprint, jsonify, request
from models import db, BlockSchedule

block_schedule_bp = Blueprint('block_schedule', __name__)

# GET all blocks
@block_schedule_bp.route('/', methods=['GET'])
def get_schedules():
    schedules = BlockSchedule.query.all()
    return jsonify([s.to_dict() for s in schedules])

# GET one block by ID
@block_schedule_bp.route('/<int:id>', methods=['GET'])
def get_schedule(id):
    schedule = BlockSchedule.query.get_or_404(id)
    return jsonify(schedule.to_dict())

# POST create new block
@block_schedule_bp.route('/', methods=['POST'])
def create_schedule():
    data = request.get_json()

    new_schedule = BlockSchedule(
        day=data['day'],
        startTime=data['startTime'],
        endTime=data['endTime'],
        title=data['title'],
        description=data.get('description'),
        location=data.get('location')
    )

    db.session.add(new_schedule)
    db.session.commit()

    return jsonify(new_schedule.to_dict()), 201