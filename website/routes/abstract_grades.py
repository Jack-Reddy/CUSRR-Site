from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc
from website.models import AbstractGrade, Presentation
from website import db

abstract_grades_bp = Blueprint('abstract_grades', __name__)


# GET all abstract grades
@abstract_grades_bp.route('/', methods=['GET'])
def get_abstract_grades():
    grades = AbstractGrade.query.all()
    return jsonify([g.to_dict() for g in grades])


# GET one abstract grade by ID
@abstract_grades_bp.route('/<int:id>', methods=['GET'])
def get_abstract_grade(id):
    grade = AbstractGrade.query.get_or_404(id)
    return jsonify(grade.to_dict())


# POST create new abstract grade
@abstract_grades_bp.route('/', methods=['POST'])
def create_abstract_grade():
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


# PUT update existing abstract grade
@abstract_grades_bp.route('/<int:id>', methods=['PUT'])
def update_abstract_grade(id):
    grade = AbstractGrade.query.get_or_404(id)
    data = request.get_json()

    grade.user_id = data.get('user_id', grade.user_id)
    grade.presentation_id = data.get('presentation_id', grade.presentation_id)
    grade.criteria_1 = data.get('criteria_1', grade.criteria_1)
    grade.criteria_2 = data.get('criteria_2', grade.criteria_2)
    grade.criteria_3 = data.get('criteria_3', grade.criteria_3)

    db.session.commit()
    return jsonify(grade.to_dict())


# DELETE abstract grade
@abstract_grades_bp.route('/<int:id>', methods=['DELETE'])
def delete_abstract_grade(id):
    grade = AbstractGrade.query.get_or_404(id)
    db.session.delete(grade)
    db.session.commit()
    return jsonify({"message": "Abstract grade deleted"})


# route that returns average score for each presentation, sorted high to low
@abstract_grades_bp.route('/averages', methods=['GET'])
def get_average_abstract_grades_by_presentation():
    """
    Returns the average total score (criteria_1 + criteria_2 + criteria_3)
    for each presentation, sorted from highest to lowest average.
    """

    averages = (
        db.session.query(
            AbstractGrade.presentation_id,
            func.avg(AbstractGrade.criteria_1 + AbstractGrade.criteria_2 + AbstractGrade.criteria_3).label('average_score'),
            func.count(AbstractGrade.id).label('num_grades')
        )
        .group_by(AbstractGrade.presentation_id)
        .order_by(desc('average_score'))
        .all()
    )

    results = []
    for avg in averages:
        presentation = Presentation.query.get(avg.presentation_id)
        results.append({
            "presentation_id": avg.presentation_id,
            "presentation_title": presentation.title if presentation else None,
            "average_score": round(avg.average_score, 2),
            "num_grades": avg.num_grades
        })

    return jsonify(results)
