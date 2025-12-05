'''
Gerades API routes for the grade data model in the Flask app.
Provides CRUD operations and average score calculations.
'''
from sqlalchemy import func, desc
from flask import Blueprint, jsonify, request
from website.models import Grade, Presentation
from website import db
from .utils import format_average_grades


grades_bp = Blueprint('grades', __name__)


@grades_bp.route('/', methods=['GET'])
def get_grades():
    ''' GET all grades '''
    grades = Grade.query.all()
    return jsonify([g.to_dict() for g in grades])


@grades_bp.route('/<int:grade_id>', methods=['GET'])
def get_grade(grade_id):
    ''' GET one grade by ID '''
    grade = Grade.query.get_or_404(grade_id)
    return jsonify(grade.to_dict())


@grades_bp.route('/', methods=['POST'])
def create_grade():
    ''' POST create new grade '''
    data = request.get_json()

    new_grade = Grade(
        user_id=data['user_id'],
        presentation_id=data['presentation_id'],
        criteria_1=data['criteria_1'],
        criteria_2=data['criteria_2'],
        criteria_3=data['criteria_3']
    )

    db.session.add(new_grade)
    db.session.commit()

    return jsonify(new_grade.to_dict()), 201


@grades_bp.route('/<int:grade_id>', methods=['PUT'])
def update_grade(grade_id):
    ''' PUT update existing grade '''
    grade = Grade.query.get_or_404(grade_id)
    data = request.get_json()

    grade.user_id = data.get('user_id', grade.user_id)
    grade.presentation_id = data.get('presentation_id', grade.presentation_id)
    grade.criteria_1 = data.get('criteria_1', grade.criteria_1)
    grade.criteria_2 = data.get('criteria_2', grade.criteria_2)
    grade.criteria_3 = data.get('criteria_3', grade.criteria_3)

    db.session.commit()
    return jsonify(grade.to_dict())


@grades_bp.route('/<int:grade_id>', methods=['DELETE'])
def delete_grade(grade_id):
    ''' DELETE grade '''
    grade = Grade.query.get_or_404(grade_id)
    db.session.delete(grade)
    db.session.commit()
    return jsonify({"message": "Grade deleted"})


@grades_bp.route('/averages', methods=['GET'])
def get_average_grades_by_presentation():
    ''' GET average grades by presentation
    route that returns average score for each presentation, sorted high to low
       '''
    averages = (
        db.session.query(
            Grade.presentation_id,
            func.avg(
                Grade.criteria_1 +
                Grade.criteria_2 +
                Grade.criteria_3).label('average_score'),
            func.count(
                Grade.id).label('num_grades')) .group_by(
                    Grade.presentation_id) .order_by(
                        desc('average_score')) .all())

    # Attach presentation info
    return format_average_grades(averages)
