'''
Gerades API routes for the grade data model in the Flask app.
Provides CRUD operations and average score calculations.
'''
import csv
import io

from sqlalchemy import func, desc
from flask import Blueprint, Response, current_app, jsonify, request, session
from website.models import AbstractGrade, Grade, Presentation, BlockSchedule, User
from website import db
from .utils import format_average_grades


grades_bp = Blueprint('grades', __name__)


def _total_score(grade):
    """Return the summed score for a grade row."""
    return (grade.criteria_1 or 0) + (grade.criteria_2 or 0) + (grade.criteria_3 or 0)


def _average_score(grades):
    """Return a rounded average total score, or None if there are no grades."""
    if not grades:
        return None
    return round(sum(_total_score(grade) for grade in grades) / len(grades), 2)


def _presenter_name(user):
    """Return a readable presenter name for a user."""
    first = (user.firstname or '').strip()
    last = (user.lastname or '').strip()
    return f"{first} {last}".strip() or user.email


def _grader_name(user):
    """Return a readable grader name for a user."""
    if not user:
        return '—'
    first = (user.firstname or '').strip()
    last = (user.lastname or '').strip()
    return f"{first} {last}".strip() or user.email or '—'


def _presentation_presenter_names(presentation):
    """Return comma-separated presenter names for a presentation."""
    if not presentation:
        return '—'
    names = [_presenter_name(user) for user in presentation.presenters]
    return ', '.join(names) if names else '—'


def _csv_grade_row(grade, grade_type):
    """Return a normalized CSV row for presentation or abstract grades."""
    return [
        grade_type,
        _grader_name(grade.grader),
        _presentation_presenter_names(grade.presentation),
        grade.presentation.title if grade.presentation else '—',
        _total_score(grade),
    ]


def _latest_grade_rows(grades):
    """Return only the latest row for each grader/presentation pair."""
    latest = {}
    for grade in grades:
        key = (grade.user_id, grade.presentation_id)
        latest[key] = grade
    return list(latest.values())


def _normalize_role(role):
    """Normalize role strings such as abstract grader, abstract-grader, and abstract_grader."""
    return str(role or '').strip().lower().replace('-', '_').replace(' ', '_')


def _roles_for(user):
    """Return normalized roles for a user."""
    roles = {
        _normalize_role(role)
        for role in str(user.auth or '').split(',')
        if str(role or '').strip()
    } if user else set()
    if 'admin' in roles:
        roles.add('organizer')
    return roles


def _can_submit_normal_grade(user):
    """Return whether a user may submit normal presentation grades."""
    roles = _roles_for(user)
    return 'organizer' in roles or 'abstract_grader' in roles


def _current_user():
    """Return the logged-in database user, if there is one."""
    user_info = session.get('user') or {}
    email = user_info.get('email')
    if not email:
        return None
    return User.query.filter_by(email=email).first()


def _normal_grade_actor_or_error():
    """Allow only organizers and abstract graders to create normal presentation grades."""
    if current_app.config.get('TESTING', False):
        return None, None

    actor = _current_user()
    if not actor:
        return None, (jsonify({'error': 'Authentication required'}), 401)

    if _can_submit_normal_grade(actor):
        return actor, None

    return None, (jsonify({'error': 'Only organizers and abstract graders can submit presentation grades'}), 403)


@grades_bp.route('/', methods=['GET'])
def get_grades():
    ''' GET all grades '''
    grades = Grade.query.all()
    return jsonify([g.to_dict() for g in grades])


@grades_bp.route('/can-submit', methods=['GET'])
def can_submit_grade():
    """Return whether the current user can use normal presentation grading controls."""
    actor = _current_user()
    roles = _roles_for(actor)
    return jsonify({
        'can_submit_grade': bool(actor and _can_submit_normal_grade(actor)),
        'roles': sorted(roles),
    })


@grades_bp.route('/dashboard-summary', methods=['GET'])
def get_grades_dashboard_summary():
    """Return presentation grade summary rows for the organizer grades dashboard."""
    presentations = Presentation.query.order_by(Presentation.id.asc()).all()
    rows = []

    for presentation in presentations:
        presenter_names = [_presenter_name(user) for user in presentation.presenters]
        presentation_grades = _latest_grade_rows(presentation.grades)
        abstract_grades = _latest_grade_rows(presentation.abstract_grades)
        rows.append({
            "presentation_id": presentation.id,
            "presentation_title": presentation.title,
            "presenters": [presenter.to_dict_basic() for presenter in presentation.presenters],
            "presenter_names": ', '.join(presenter_names) if presenter_names else '—',
            "average_score": _average_score(presentation_grades),
            "num_grades": len(presentation_grades),
            "average_abstract_score": _average_score(abstract_grades),
            "num_abstract_grades": len(abstract_grades),
        })

    return jsonify(rows)


@grades_bp.route('/export.csv', methods=['GET'])
def export_grades_csv():
    """Export individual presentation and abstract grades as a CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Grade type',
        'Grader',
        'People associated with presentation',
        'Presentation',
        'Grade given',
    ])

    grades = _latest_grade_rows(
        Grade.query
        .join(Grade.presentation)
        .outerjoin(Grade.grader)
        .order_by(Presentation.title.asc(), Grade.id.asc())
        .all()
    )

    abstract_grades = _latest_grade_rows(
        AbstractGrade.query
        .join(AbstractGrade.presentation)
        .outerjoin(AbstractGrade.grader)
        .order_by(Presentation.title.asc(), AbstractGrade.id.asc())
        .all()
    )

    for grade in grades:
        writer.writerow(_csv_grade_row(grade, 'Presentation'))

    for grade in abstract_grades:
        writer.writerow(_csv_grade_row(grade, 'Abstract'))

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=grades.csv'
    return response


@grades_bp.route('/mine/<int:presentation_id>', methods=['GET'])
def get_my_grade(presentation_id):
    """Return the logged-in grader's normal presentation grade for undo/status UI."""
    actor, permission_error = _normal_grade_actor_or_error()
    if permission_error:
        return permission_error
    if not actor:
        return jsonify({'grade': None})

    grade = (
        Grade.query
        .filter_by(user_id=actor.id, presentation_id=presentation_id)
        .order_by(Grade.id.desc())
        .first()
    )
    return jsonify({'grade': grade.to_dict() if grade else None})


@grades_bp.route('/mine/<int:presentation_id>', methods=['DELETE'])
def delete_my_grade(presentation_id):
    """Undo the logged-in grader's normal presentation grade."""
    actor, permission_error = _normal_grade_actor_or_error()
    if permission_error:
        return permission_error
    if not actor:
        return jsonify({'deleted': 0})

    grades = Grade.query.filter_by(user_id=actor.id, presentation_id=presentation_id).all()
    deleted_count = len(grades)
    for grade in grades:
        db.session.delete(grade)
    db.session.commit()
    return jsonify({'message': 'Grade undone', 'deleted': deleted_count})


@grades_bp.route('/<int:grade_id>', methods=['GET'])
def get_grade(grade_id):
    ''' GET one grade by ID '''
    grade = Grade.query.get_or_404(grade_id)
    return jsonify(grade.to_dict())


@grades_bp.route('/', methods=['POST'])
def create_grade():
    actor, permission_error = _normal_grade_actor_or_error()
    if permission_error:
        return permission_error

    data = request.get_json() or {}
    if actor:
        data['user_id'] = actor.id

    existing = Grade.query.filter_by(
        user_id=data["user_id"],
        presentation_id=data["presentation_id"]
    ).first()

    if existing:
        return jsonify({"error": "Grade already exists"}), 400

    new_grade = Grade(
        user_id=data["user_id"],
        presentation_id=data["presentation_id"],
        criteria_1=data["criteria_1"],
        criteria_2=data["criteria_2"],
        criteria_3=data["criteria_3"]
    )

    db.session.add(new_grade)
    db.session.commit()

    return jsonify(new_grade.to_dict()), 201


@grades_bp.route('/<int:grade_id>', methods=['PUT'])
def update_grade(grade_id):
    ''' PUT update existing grade '''
    actor, permission_error = _normal_grade_actor_or_error()
    if permission_error:
        return permission_error

    grade = Grade.query.get_or_404(grade_id)
    data = request.get_json() or {}

    if actor and grade.user_id != actor.id and 'organizer' not in _roles_for(actor):
        return jsonify({'error': 'You can only update your own grade'}), 403

    if current_app.config.get('TESTING', False):
        grade.user_id = data.get('user_id', grade.user_id)
    elif actor:
        grade.user_id = actor.id

    grade.presentation_id = data.get('presentation_id', grade.presentation_id)
    grade.criteria_1 = data.get('criteria_1', grade.criteria_1)
    grade.criteria_2 = data.get('criteria_2', grade.criteria_2)
    grade.criteria_3 = data.get('criteria_3', grade.criteria_3)

    db.session.commit()
    return jsonify(grade.to_dict())


@grades_bp.route('/<int:grade_id>', methods=['DELETE'])
def delete_grade(grade_id):
    ''' DELETE grade '''
    actor, permission_error = _normal_grade_actor_or_error()
    if permission_error:
        return permission_error

    grade = Grade.query.get_or_404(grade_id)
    if actor and grade.user_id != actor.id and 'organizer' not in _roles_for(actor):
        return jsonify({'error': 'You can only delete your own grade'}), 403

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
                Grade.id).label('num_grades'))
        .join(Grade.presentation)
        .join(Presentation.schedule)
        .filter(BlockSchedule.is_presentation.is_(True))
        .group_by(Grade.presentation_id)
        .order_by(desc('average_score'))
        .all())

    # Attach presentation info
    return format_average_grades(averages)
