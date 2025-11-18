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

# PUT update existing block
@block_schedule_bp.route('/<int:id>', methods=['PUT'])
def update_schedule(id):
    schedule = BlockSchedule.query.get_or_404(id)
    data = request.get_json()

    schedule.day = data.get('day', schedule.day)
    schedule.startTime = data.get('startTime', schedule.startTime)
    schedule.endTime = data.get('endTime', schedule.endTime)
    schedule.title = data.get('title', schedule.title)
    schedule.description = data.get('description', schedule.description)
    schedule.location = data.get('location', schedule.location)

    db.session.commit()
    return jsonify(schedule.to_dict())

# DELETE block
@block_schedule_bp.route('/<int:id>', methods=['DELETE'])
def delete_schedule(id):
    schedule = BlockSchedule.query.get_or_404(id)
    db.session.delete(schedule)
    db.session.commit()
    return jsonify({"message": "Schedule deleted"})

# GET schedules by day
@block_schedule_bp.route('/day/<string:day>', methods=['GET'])
def get_schedules_by_day(day):
    schedules = BlockSchedule.query.filter_by(day=day).all()
    return jsonify([s.to_dict() for s in schedules])

# GET Unique days
@block_schedule_bp.route('/days', methods=['GET'])
def get_unique_days():
    days = db.session.query(BlockSchedule.day).distinct().all()
    unique_days = [day[0] for day in days]
    return jsonify(unique_days)