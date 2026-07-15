'''
Abstract grades routes for the Flask app.
Provides CRUD operations and average score calculations.
'''

from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc, inspect, text
from website.models import AbstractGrade, Presentation, BlockSchedule
from website import db
from .utils import format_average_grades

abstract_grades_bp = Blueprint('abstract_grades', __name__)


def _abstract_grade_columns():
    """Return the existing abstract grade table columns."""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('abstract_grades'):
            return set()
        return {column['name'] for column in inspector.get_columns('abstract_grades')}
    except Exception:
        return set()


def ensure_abstract_grade_comment_column():
    """Add a persistent comments column for existing databases."""
    columns = _abstract_grade_columns()
    if not columns or 'comment_text' in columns:
        return

    try:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE abstract_grades ADD COLUMN comment_text TEXT"))
    except Exception:
        # The column may already have been added by a concurrent request.
        return


@abstract_grades_bp.before_request
def ensure_abstract_grade_schema_before_request():
    """Keep older deployments compatible after adding abstract grade comments."""
    ensure_abstract_grade_comment_column()


def _comment_from_payload(data):
    """Normalize submitted comment text."""
    comment = data.get('comment', data.get('comments', ''))
    return str(comment or '')


def _set_abstract_grade_comment(grade_id, comment):
    """Persist comment text for an abstract grade."""
    ensure_abstract_grade_comment_column()
    if 'comment_text' not in _abstract_grade_columns():
        return

    db.session.execute(
        text("UPDATE abstract_grades SET comment_text = :comment WHERE id = :grade_id"),
        {"comment": comment, "grade_id": grade_id}
    )


def _abstract_grade_comment(grade_id):
    """Return saved comment text for an abstract grade."""
    ensure_abstract_grade_comment_column()
    if 'comment_text' not in _abstract_grade_columns():
        return ''

    row = db.session.execute(
        text("SELECT comment_text FROM abstract_grades WHERE id = :grade_id"),
        {"grade_id": grade_id}
    ).fetchone()
    return row[0] if row and row[0] else ''


@abstract_grades_bp.route('/', methods=['GET'])
def get_abstract_grades():
    ''' GET all abstract grades '''
    grades = AbstractGrade.query.all()
    data = []
    for grade in grades:
        grade_data = grade.to_dict()
        grade_data['comment'] = _abstract_grade_comment(grade.id)
        data.append(grade_data)
    return jsonify(data)


@abstract_grades_bp.route('/<int:abstract_grade_id>', methods=['GET'])
def get_abstract_grade(abstract_grade_id):
    '''GET one abstract grade by ID '''
    grade = AbstractGrade.query.get_or_404(abstract_grade_id)
    data = grade.to_dict()
    data['comment'] = _abstract_grade_comment(grade.id)
    return jsonify(data)


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
        response_data = existing.to_dict()
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

    response_data = new_grade.to_dict()
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
    response_data = grade.to_dict()
    response_data['comment'] = _abstract_grade_comment(grade.id)
    return jsonify(response_data)


@abstract_grades_bp.route('/<int:abstract_grade_id>', methods=['DELETE'])
def delete_abstract_grade(abstract_grade_id):
    ''' DELETE abstract grade '''
    grade = AbstractGrade.query.get_or_404(abstract_grade_id)
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
    Return completed presentation IDs plus one abstract grade ID per presentation for undo/review actions.
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
