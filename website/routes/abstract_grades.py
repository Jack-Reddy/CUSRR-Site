'''
Abstract grades routes for the Flask app.
Provides CRUD operations and average score calculations.
'''

from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc
from website.models import AbstractGrade, Presentation, BlockSchedule
from website import db
from .utils import format_average_grades

abstract_grades_bp = Blueprint('abstract_grades', __name__)


@abstract_grades_bp.route('/', methods=['GET'])
def get_abstract_grades():
    ''' GET all abstract grades '''
    grades = AbstractGrade.query.all()
    return jsonify([g.to_dict() for g in grades])


@abstract_grades_bp.route('/<int:abstract_grade_id>', methods=['GET'])
def get_abstract_grade(abstract_grade_id):
    '''GET one abstract grade by ID '''
    grade = AbstractGrade.query.get_or_404(abstract_grade_id)
    return jsonify(grade.to_dict())


@abstract_grades_bp.route('/', methods=['POST'])
def create_abstract_grade():
    ''' POST create new abstract grade, or update the existing grade for this grader/presentation. '''
    data = request.get_json() or {}

    existing = AbstractGrade.query.filter_by(
        user_id=data['user_id'],
        presentation_id=data['presentation_id']
    ).first()

    if existing:
        existing.criteria_1 = data['criteria_1']
        existing.criteria_2 = data['criteria_2']
        existing.criteria_3 = data['criteria_3']
        db.session.commit()
        return jsonify(existing.to_dict()), 200

    new_grade = AbstractGrade(
        user_id=data['user_id'],
        presentation_id=data['presentation_id'],
        criteria_1=data['criteria_1'],
        criteria_2=data['criteria_2'],
        criteria_3=data['criteria_3']
    )

    db.session.add(new_grade)
    db.session.commit()

    return jsonify(new_grade.to_dict()), 201


@abstract_grades_bp.route('/<int:abstract_grade_id>', methods=['PUT'])
def update_abstract_grade(abstract_grade_id):
    ''' PUT update existing abstract grade '''
    grade = AbstractGrade.query.get_or_404(abstract_grade_id)
    data = request.get_json()

    grade.user_id = data.get('user_id', grade.user_id)
    grade.presentation_id = data.get('presentation_id', grade.presentation_id)
    grade.criteria_1 = data.get('criteria_1', grade.criteria_1)
    grade.criteria_2 = data.get('criteria_2', grade.criteria_2)
    grade.criteria_3 = data.get('criteria_3', grade.criteria_3)

    db.session.commit()
    return jsonify(grade.to_dict())


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
    Return completed presentation IDs plus one abstract grade ID per presentation for undo actions.
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
        }
        for grade in latest_by_presentation.values()
    ]

    return jsonify({"completed": completed, "grades": grade_rows})