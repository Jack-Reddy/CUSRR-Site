'''
Block Schedule API routes.
Provides CRUD operations and querying by day.
'''
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func
from sqlalchemy.orm import joinedload, load_only
from website.models import BlockSchedule, Presentation, User
from website import db


DEFAULT_SCHEDULE_BLOCKS = [
    {
        "title": "Opening Remarks",
        "start_time": "2026-11-06T08:30",
        "end_time": "2026-11-06T09:00",
        "location": "Main Hall",
        "day": "Day 1",
        "block_type": "Keynote",
        "description": None,
        "sub_length": None,
        "is_presentation": True,
    },
    {
        "title": "Keynote Address",
        "start_time": "2026-11-06T09:00",
        "end_time": "2026-11-06T10:00",
        "location": "Auditorium",
        "day": "Day 1",
        "block_type": "Keynote",
        "description": None,
        "sub_length": None,
        "is_presentation": True,
    },
    {
        "title": "Poster Session I",
        "start_time": "2026-11-06T10:15",
        "end_time": "2026-11-06T11:00",
        "location": "Exhibition Hall",
        "day": "Day 1",
        "block_type": "Poster",
        "description": None,
        "sub_length": 15,
        "is_presentation": True,
    },
    {
        "title": "Lunch Break",
        "start_time": "2026-11-06T12:00",
        "end_time": "2026-11-06T13:00",
        "location": "Courtyard",
        "day": "Day 1",
        "block_type": "Break",
        "description": None,
        "sub_length": None,
        "is_presentation": False,
    },
]


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


def _default_schedule_objects():
    """Create default schedule block model instances without committing."""
    blocks = []
    for item in DEFAULT_SCHEDULE_BLOCKS:
        blocks.append(BlockSchedule(
            day=item["day"],
            start_time=parse_local_datetime(item["start_time"]),
            end_time=parse_local_datetime(item["end_time"]),
            title=item["title"],
            description=item.get("description"),
            location=item.get("location"),
            block_type=item.get("block_type"),
            sub_length=item.get("sub_length"),
            is_presentation=item.get("is_presentation", True),
        ))
    return blocks


def _format_datetime(value):
    """Format datetimes as naive local ISO strings for schedule JSON."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%dT%H:%M:%S')
    return str(value)


def _presenter_to_schedule_dict(user):
    """Return the presenter fields needed by the schedule cards/modal."""
    return {
        "id": user.id,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "email": user.email,
        "activity": user.activity,
        "name": f"{user.firstname or ''} {user.lastname or ''}".strip() or user.email,
    }


def _presentation_to_schedule_dict(presentation, program_ids):
    """Return a lightweight presentation payload for the schedule page."""
    from website.routes.presentations import effective_presentation_time, get_presentation_type

    schedule = presentation.schedule
    display_time = effective_presentation_time(presentation)
    return {
        "id": presentation.id,
        "title": presentation.title,
        "abstract": presentation.abstract,
        "time": _format_datetime(display_time),
        "room": schedule.location if schedule else None,
        "type": get_presentation_type(presentation),
        "program_identifier": program_ids.get(presentation.id),
        "show_on_schedule": True,
        "schedule_id": presentation.schedule_id,
        "num_in_block": presentation.num_in_block,
        "presenters": [
            _presenter_to_schedule_dict(presenter)
            for presenter in presentation.presenters
        ],
    }


def _schedule_payload_for_day(day):
    """Return blocks plus lightweight presentation rows for one schedule day."""
    from website.routes.presentations import get_show_on_schedule, _program_identifier_map

    blocks = (
        BlockSchedule.query
        .filter_by(day=day)
        .order_by(BlockSchedule.start_time, BlockSchedule.id)
        .all()
    )
    block_ids = [block.id for block in blocks]

    if not block_ids:
        return {
            "blocks": [],
            "presentations": [],
        }

    identifier_presentations = (
        Presentation.query
        .options(
            load_only(
                Presentation.id,
                Presentation.time,
                Presentation.num_in_block,
                Presentation.schedule_id,
            ),
            joinedload(Presentation.schedule).load_only(
                BlockSchedule.id,
                BlockSchedule.block_type,
                BlockSchedule.start_time,
                BlockSchedule.sub_length,
            ),
        )
        .all()
    )
    visible_identifier_presentations = [
        presentation
        for presentation in identifier_presentations
        if get_show_on_schedule(presentation.id)
    ]
    program_ids = _program_identifier_map(visible_identifier_presentations)
    visible_ids = {presentation.id for presentation in visible_identifier_presentations}

    presentations = (
        Presentation.query
        .options(
            load_only(
                Presentation.id,
                Presentation.title,
                Presentation.abstract,
                Presentation.time,
                Presentation.num_in_block,
                Presentation.schedule_id,
            ),
            joinedload(Presentation.schedule).load_only(
                BlockSchedule.id,
                BlockSchedule.location,
                BlockSchedule.block_type,
                BlockSchedule.start_time,
                BlockSchedule.sub_length,
            ),
            joinedload(Presentation.presenters).load_only(
                User.id,
                User.firstname,
                User.lastname,
                User.email,
                User.activity,
            ),
        )
        .filter(Presentation.schedule_id.in_(block_ids))
        .order_by(
            Presentation.schedule_id.asc(),
            Presentation.num_in_block.asc().nullsfirst(),
            Presentation.id.asc(),
        )
        .all()
    )

    presentations_by_block = {block.id: [] for block in blocks}
    for presentation in presentations:
        if presentation.id not in visible_ids:
            continue
        presentations_by_block.setdefault(presentation.schedule_id, []).append(
            _presentation_to_schedule_dict(presentation, program_ids)
        )

    return {
        "blocks": [block.to_dict() for block in blocks],
        "presentations": [
            {
                "block": block.to_dict(),
                "presentations": presentations_by_block.get(block.id, []),
            }
            for block in blocks
        ],
    }


block_schedule_bp = Blueprint('block_schedule', __name__)


@block_schedule_bp.route('/', methods=['GET'])
def get_schedules():
    ''' GET all blocks '''
    types_param = request.args.get('types') or request.args.get('type')
    query = BlockSchedule.query

    if types_param:
        # Accept comma-separated list; case-insensitive match on block_type
        type_list = [t.strip().lower() for t in types_param.split(',') if t.strip()]
        if type_list:
            query = query.filter(
                BlockSchedule.block_type.isnot(None),
                func.lower(BlockSchedule.block_type).in_(type_list)
            )

    schedules = query.all()
    return jsonify([s.to_dict() for s in schedules])


@block_schedule_bp.route('/restore-defaults', methods=['POST'])
def restore_default_schedules():
    ''' POST restore default schedule blocks if the schedule was emptied. '''
    if BlockSchedule.query.count() > 0:
        return jsonify({
            "message": "Schedule blocks already exist; restore skipped.",
            "created": 0,
        })

    blocks = _default_schedule_objects()
    db.session.add_all(blocks)
    db.session.commit()

    return jsonify({
        "message": "Default schedule blocks restored.",
        "created": len(blocks),
        "blocks": [block.to_dict() for block in blocks],
    }), 201


@block_schedule_bp.route('/<int:block_id>', methods=['GET'])
def get_schedule(block_id):
    ''' GET one block by ID '''
    schedule = BlockSchedule.query.get_or_404(block_id)
    return jsonify(schedule.to_dict())


@block_schedule_bp.route('/', methods=['POST'])
def create_schedule():
    ''' POST create new block '''
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
        sub_length=data.get('sub_length'),
        is_presentation=data.get('is_presentation', True)
    )

    db.session.add(new_schedule)
    db.session.commit()

    return jsonify(new_schedule.to_dict()), 201


@block_schedule_bp.route('/<int:block_id>', methods=['PUT'])
def update_schedule(block_id):
    ''' PUT update existing block '''
    schedule = BlockSchedule.query.get_or_404(block_id)
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

    # Update is_presentation if provided
    if 'is_presentation' in data:
        schedule.is_presentation = data.get('is_presentation', True)

    db.session.commit()
    return jsonify(schedule.to_dict())


@block_schedule_bp.route('/<int:block_id>', methods=['DELETE'])
def delete_schedule(block_id):
    ''' DELETE block '''
    schedule = BlockSchedule.query.get_or_404(block_id)

    if (
        not current_app.config.get('TESTING', False)
        and BlockSchedule.query.count() <= 1
    ):
        return jsonify({
            "error": "Cannot delete the final schedule block.",
            "message": "Create another block first or use restore defaults after clearing the schedule.",
        }), 400

    db.session.delete(schedule)
    db.session.commit()
    return jsonify({"message": "Schedule deleted"})


@block_schedule_bp.route('/day/<string:day>', methods=['GET'])
def get_schedules_by_day(day):
    ''' GET schedules by day '''
    schedules = BlockSchedule.query.filter_by(
        day=day).order_by(
        BlockSchedule.start_time).all()
    return jsonify([s.to_dict() for s in schedules])


@block_schedule_bp.route('/day/<string:day>/full', methods=['GET'])
def get_schedule_page_by_day(day):
    ''' GET blocks and lightweight presentation rows for the schedule page. '''
    return jsonify(_schedule_payload_for_day(day))


@block_schedule_bp.route('/days', methods=['GET'])
def get_unique_days():
    ''' GET unique days - do not return "Unassigned" day '''
    days = db.session.query(BlockSchedule.day).distinct().filter(BlockSchedule.day != "Unassigned").all()
    unique_days = [day[0] for day in days]
    return jsonify(unique_days)
