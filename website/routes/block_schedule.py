'''
Block Schedule API routes.
Provides CRUD operations and querying by day.
'''

from flask import Blueprint, jsonify, request
from datetime import datetime
from website.models import BlockSchedule
from website import db


def parse_local_datetime(val):
    """Parse a local datetime string (no timezone) into a naive datetime.
    Accepts 'YYYY-MM-DDTHH:MM:SS' or 'YYYY-MM-DDTHH:MM'."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None


block_schedule_bp = Blueprint('block_schedule', __name__)


@block_schedule_bp.route('/', methods=['GET'])
def get_schedules():
    # GET all blocks
    schedules = BlockSchedule.query.all()
    return jsonify([s.to_dict() for s in schedules])


@block_schedule_bp.route('/<int:id>', methods=['GET'])
def get_schedule(id):
    # GET one block by ID
    schedule = BlockSchedule.query.get_or_404(id)
    return jsonify(schedule.to_dict())


@block_schedule_bp.route('/', methods=['POST'])
def create_schedule():
    # POST create new block
    data = request.get_json()

    # Accept either camelCase or snake_case from client; parse into naive
    # local datetimes
    start_raw = data.get('start_time') or data.get('startTime')
    end_raw = data.get('end_time') or data.get('endTime')
    start_dt = parse_local_datetime(start_raw)
    end_dt = parse_local_datetime(end_raw)

    new_schedule = BlockSchedule(
        day=data['day'],
        start_time=start_dt,
        end_time=end_dt,
        title=data['title'],
        description=data.get('description'),
        location=data.get('location'),
        block_type=data.get('block_type') or data.get('type'),
        sub_length=data.get('sub_length')
    )

    db.session.add(new_schedule)
    db.session.commit()

    return jsonify(new_schedule.to_dict()), 201


@block_schedule_bp.route('/<int:id>', methods=['PUT'])
def update_schedule(id):
    # PUT update existing block
    schedule = BlockSchedule.query.get_or_404(id)
    data = request.get_json()

    schedule.day = data.get('day', schedule.day)

    # parse datetimes if provided (accept camelCase or snake_case)
    if 'start_time' in data or 'startTime' in data:
        start_raw = data.get('start_time') or data.get('startTime')
        parsed = parse_local_datetime(start_raw)
        if parsed:
            schedule.start_time = parsed

    if 'end_time' in data or 'endTime' in data:
        end_raw = data.get('end_time') or data.get('endTime')
        parsed = parse_local_datetime(end_raw)
        if parsed:
            schedule.end_time = parsed

    schedule.title = data.get('title', schedule.title)
    schedule.description = data.get('description', schedule.description)
    schedule.location = data.get('location', schedule.location)
    schedule.block_type = data.get(
        'block_type', data.get(
            'type', schedule.block_type))
    schedule.sub_length = data.get('sub_length', schedule.sub_length)

    db.session.commit()
    return jsonify(schedule.to_dict())


@block_schedule_bp.route('/<int:id>', methods=['DELETE'])
def delete_schedule(id):
    # DELETE block
    schedule = BlockSchedule.query.get_or_404(id)
    db.session.delete(schedule)
    db.session.commit()
    return jsonify({"message": "Schedule deleted"})


@block_schedule_bp.route('/day/<string:day>', methods=['GET'])
def get_schedules_by_day(day):
    # GET schedules by day
    schedules = BlockSchedule.query.filter_by(
        day=day).order_by(
        BlockSchedule.start_time).all()
    return jsonify([s.to_dict() for s in schedules])


@block_schedule_bp.route('/days', methods=['GET'])
def get_unique_days():
    # GET unique days
    days = db.session.query(BlockSchedule.day).distinct().all()
    unique_days = [day[0] for day in days]
    return jsonify(unique_days)
