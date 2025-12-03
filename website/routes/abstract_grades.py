'''
Abstract grades routes for the Flask app.
Provides CRUD operations and average score calculations.
'''

from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc
from website.models import AbstractGrade, Presentation
from website import db
from utils import format_average_grades

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
    ''' POST create new abstract grade '''
    data = request.get_json()

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
        .group_by(AbstractGrade.presentation_id)
        .order_by(desc('average_score'))
        .all()
    )



    return format_average_grades(averages)
