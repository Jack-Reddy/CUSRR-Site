'''
Abstract grades routes for the Flask app.
Provides CRUD operations and average score calculations.
'''

from flask import Blueprint, jsonify, request, session
from sqlalchemy import func, desc, text
from website.models import AbstractGrade, BlockSchedule, Presentation, User
from website import db
from .utils import format_average_grades

abstract_grades_bp = Blueprint('abstract_grades', __name__)


def _abstract_grade_comments_table_sql():
    """Return SQL for the optional abstract grade comments side table."""
    return """
        CREATE TABLE IF NOT EXISTS abstract_grade_comments (
            abstract_grade_id INTEGER PRIMARY KEY,
            comment TEXT
        )
    """


def _ensure_abstract_grade_comments_table():
    """Create the side table used to store optional abstract grade comments."""
    with db.engine.begin() as conn:
        conn.execute(text(_abstract_grade_comments_table_sql()))


def _comment_from_payload(data):
    """Normalize submitted comment text."""
    comment = data.get('comment', data.get('comments', ''))
    return str(comment or '')


def _set_abstract_grade_comment(grade_id, comment):
    """Persist comment text without altering the core abstract_grades table."""
    _ensure_abstract_grade_comments_table()
    cleaned = str(comment or '')
    if not cleaned.strip():
        db.session.execute(
            text("DELETE FROM abstract_grade_comments WHERE abstract_grade_id = :grade_id"),
            {"grade_id": grade_id}
        )
        return

    updated = db.session.execute(
        text("""
            UPDATE abstract_grade_comments
            SET comment = :comment
            WHERE abstract_grade_id = :grade_id
        """),
        {"comment": cleaned, "grade_id": grade_id}
    )
    if updated.rowcount == 0:
        db.session.execute(
            text("""
                INSERT INTO abstract_grade_comments (abstract_grade_id, comment)
                VALUES (:grade_id, :comment)
            """),
            {"comment": cleaned, "grade_id": grade_id}
        )


def _abstract_grade_comment(grade_id):
    """Return saved comment text for an abstract grade."""
    _ensure_abstract_grade_comments_table()
    row = db.session.execute(
        text("SELECT comment FROM abstract_grade_comments WHERE abstract_grade_id = :grade_id"),
        {"grade_id": grade_id}
    ).fetchone()
    return row[0] if row and row[0] else ''


def _abstract_grade_to_dict(grade):
    """Serialize an abstract grade with optional comment text."""
    data = grade.to_dict()
    data['comment'] = _abstract_grade_comment(grade.id)
    return data


def _current_user_id():
    """Return the current session user's database id, if available."""
    user_info = session.get('user') or {}
    email = user_info.get('email')
    if not email:
        return None
    user = User.query.filter_by(email=email).first()
    return user.id if user else None


def _show_on_schedule(presentation_id):
    """Return whether a presentation should show in public/grading lists."""
    try:
        row = db.session.execute(
            text("SELECT show_on_schedule FROM presentation_visibility WHERE presentation_id = :pid"),
            {"pid": presentation_id}
        ).fetchone()
    except Exception:
        return True
    return bool(row[0]) if row else True


@abstract_grades_bp.route('/', methods=['GET'])
def get_abstract_grades():
    ''' GET all abstract grades '''
    grades = AbstractGrade.query.all()
    return jsonify([_abstract_grade_to_dict(g) for g in grades])


@abstract_grades_bp.route('/dashboard-list', methods=['GET'])
def get_abstract_grader_dashboard_list():
    """Return lightweight abstract-grader cards for the current grader."""
    user_id = request.args.get('user_id', type=int) or _current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    grades = (
        AbstractGrade.query
        .filter_by(user_id=user_id)
        .order_by(AbstractGrade.id.asc())
        .all()
    )
    latest_by_presentation = {}
    for grade in grades:
        latest_by_presentation[grade.presentation_id] = grade

    presentation_rows = (
        db.session.query(
            Presentation.id,
            Presentation.title,
            func.substr(Presentation.abstract, 1, 220).label('abstract_preview')
        )
        .order_by(Presentation.id.asc())
        .all()
    )

    rows = []
    for presentation in presentation_rows:
        if not _show_on_schedule(presentation.id):
            continue
        grade = latest_by_presentation.get(presentation.id)
        rows.append({
            "id": presentation.id,
            "title": presentation.title or 'Untitled',
            "abstract_preview": presentation.abstract_preview or '',
            "status": "done" if grade else "todo",
            "abstract_grade_id": grade.id if grade else None,
            "criteria_1": grade.criteria_1 if grade else None,
            "criteria_2": grade.criteria_2 if grade else None,
            "criteria_3": grade.criteria_3 if grade else None,
            "comment": _abstract_grade_comment(grade.id) if grade else '',
        })

    return jsonify(rows)


@abstract_grades_bp.route('/<int:abstract_grade_id>', methods=['GET'])
def get_abstract_grade(abstract_grade_id):
    '''GET one abstract grade by ID '''
    grade = AbstractGrade.query.get_or_404(abstract_grade_id)
    return jsonify(_abstract_grade_to_dict(grade))


@abstract_grades_bp.route('/', methods=['POST'])
def create_abstract_grade():
    ''' POST create new abstract grade, or update the existing grade for this grader/presentation. '''
    data = request.get_json() or {}
    comment = _comment_from_payload(data)

    existing = AbstractGrade.query.filter_by(
        user_id=data['user_id'],
        presentation_id=data['presentation_id']
    ).first()

    if existing:
        existing.criteria_1 = data['criteria_1']
        existing.criteria_2 = data['criteria_2']
        existing.criteria_3 = data['criteria_3']
        _set_abstract_grade_comment(existing.id, comment)
        db.session.commit()
        response_data = _abstract_grade_to_dict(existing)
        response_data['comment'] = comment
        return jsonify(response_data), 200

    new_grade = AbstractGrade(
        user_id=data['user_id'],
        presentation_id=data['presentation_id'],
        criteria_1=data['criteria_1'],
        criteria_2=data['criteria_2'],
        criteria_3=data['criteria_3']
    )

    db.session.add(new_grade)
    db.session.flush()
    _set_abstract_grade_comment(new_grade.id, comment)
    db.session.commit()

    response_data = _abstract_grade_to_dict(new_grade)
    response_data['comment'] = comment
    return jsonify(response_data), 201


@abstract_grades_bp.route('/<int:abstract_grade_id>', methods=['PUT'])
def update_abstract_grade(abstract_grade_id):
    ''' PUT update existing abstract grade '''
    grade = AbstractGrade.query.get_or_404(abstract_grade_id)
    data = request.get_json() or {}

    grade.user_id = data.get('user_id', grade.user_id)
    grade.presentation_id = data.get('presentation_id', grade.presentation_id)
    grade.criteria_1 = data.get('criteria_1', grade.criteria_1)
    grade.criteria_2 = data.get('criteria_2', grade.criteria_2)
    grade.criteria_3 = data.get('criteria_3', grade.criteria_3)
    if 'comment' in data or 'comments' in data:
        _set_abstract_grade_comment(grade.id, _comment_from_payload(data))

    db.session.commit()
    return jsonify(_abstract_grade_to_dict(grade))


@abstract_grades_bp.route('/<int:abstract_grade_id>', methods=['DELETE'])
def delete_abstract_grade(abstract_grade_id):
    ''' DELETE abstract grade '''
    grade = AbstractGrade.query.get_or_404(abstract_grade_id)
    _set_abstract_grade_comment(grade.id, '')
    db.session.delete(grade)
    db.session.commit()
    return jsonify({"message": "Abstract grade deleted"})


@abstract_grades_bp.route('/averages', methods=['GET'])
def get_average_abstract_grades_by_presentation():
    """
    Returns the average total score (criteria_1 + criteria_2 + criteria_3)
    for each presentation, sorted from highest to lowest average.
    """
    averages = (
        db.session.query(
            AbstractGrade.presentation_id,
            func.avg(
                AbstractGrade.criteria_1 +
                AbstractGrade.criteria_2 +
                AbstractGrade.criteria_3
            ).label('average_score'),
            func.count(AbstractGrade.id).label('num_grades')
        )
        .join(AbstractGrade.presentation)
        .join(Presentation.schedule)
        .filter(BlockSchedule.is_presentation.is_(True))
        .group_by(AbstractGrade.presentation_id)
        .order_by(desc('average_score'))
        .all()
    )

    return format_average_grades(averages)


@abstract_grades_bp.route('/completed/<int:user_id>', methods=['GET'])
def get_completed_presentations_for_user(user_id):
    """
    Return all presentation_ids that have grades from this user.
    """
    results = (
        db.session.query(AbstractGrade.presentation_id)
        .filter_by(user_id=user_id)
        .distinct()
        .all()
    )

    completed = [r[0] for r in results]

    return jsonify({"completed": completed})


@abstract_grades_bp.route('/completed/<int:user_id>/details', methods=['GET'])
def get_completed_abstract_grade_details_for_user(user_id):
    """
    Return completed presentation IDs plus one abstract grade ID per presentation.
    """
    grades = (
        AbstractGrade.query
        .filter_by(user_id=user_id)
        .order_by(AbstractGrade.id.asc())
        .all()
    )

    latest_by_presentation = {}
    for grade in grades:
        latest_by_presentation[grade.presentation_id] = grade

    completed = list(latest_by_presentation.keys())
    grade_rows = [
        {
            "id": grade.id,
            "presentation_id": grade.presentation_id,
            "criteria_1": grade.criteria_1,
            "criteria_2": grade.criteria_2,
            "criteria_3": grade.criteria_3,
            "comment": _abstract_grade_comment(grade.id),
        }
        for grade in latest_by_presentation.values()
    ]

    return jsonify({"completed": completed, "grades": grade_rows})
