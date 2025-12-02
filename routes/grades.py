from flask import Blueprint, jsonify, request
from models import db, Grade

grades_bp = Blueprint('grades', __name__)

# GET all grades
@grades_bp.route('/', methods=['GET'])
def get_grades():
    grades = Grade.query.all()
    return jsonify([g.to_dict() for g in grades])

# GET one grade by ID
@grades_bp.route('/<int:id>', methods=['GET'])
def get_grade(id):
    grade = Grade.query.get_or_404(id)
    return jsonify(grade.to_dict())

# POST create new grade
@grades_bp.route('/', methods=['POST'])
def create_grade():
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

# PUT update existing grade
@grades_bp.route('/<int:id>', methods=['PUT'])
def update_grade(id):
    grade = Grade.query.get_or_404(id)
    data = request.get_json()

    grade.user_id = data.get('user_id', grade.user_id)
    grade.presentation_id = data.get('presentation_id', grade.presentation_id)
    grade.criteria_1 = data.get('criteria_1', grade.criteria_1)
    grade.criteria_2 = data.get('criteria_2', grade.criteria_2)
    grade.criteria_3 = data.get('criteria_3', grade.criteria_3)

    db.session.commit()
    return jsonify(grade.to_dict())

# DELETE grade
@grades_bp.route('/<int:id>', methods=['DELETE'])
def delete_grade(id):
    grade = Grade.query.get_or_404(id)
    db.session.delete(grade)
    db.session.commit()
    return jsonify({"message": "Grade deleted"})


from sqlalchemy import func, desc
from models import db, Grade, Presentation

#route that returns average score for each presentation, sorted high to low
@grades_bp.route('/averages', methods=['GET'])
def get_average_grades_by_presentation():
    # Aggregate average grade per presentation, sorted descending
    averages = (
        db.session.query(
            Grade.presentation_id,
            func.avg(Grade.criteria_1 + Grade.criteria_2 + Grade.criteria_3).label('average_score'),
            func.count(Grade.id).label('num_grades')
        )
        .group_by(Grade.presentation_id)
        .order_by(desc('average_score'))
        .all()
    )

    # Attach presentation info
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
