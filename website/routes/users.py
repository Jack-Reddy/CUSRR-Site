"""routes for user table in db"""
from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import IntegrityError
from website.models import Presentation, User
from website import db

users_bp = Blueprint('users', __name__)


def _roles_for(user):
    if not user or not user.auth:
        return set()
    return {role.strip().lower() for role in str(user.auth).split(',') if role.strip()}


def _session_email():
    user_info = session.get('user') or {}
    return user_info.get('email')


def _current_user():
    email = _session_email()
    if not email:
        return None
    return User.query.filter_by(email=email).first()


def _is_organizer(user):
    return 'organizer' in _roles_for(user)


def _can_assign_presentation(user, presentation_id):
    if presentation_id in (None, ''):
        user.presentation_id = None
        return None

    try:
        presentation_id = int(presentation_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid presentation_id"}), 400

    presentation = db.session.get(Presentation, presentation_id)
    if not presentation:
        return jsonify({"error": "Presentation not found"}), 404

    existing_owner = User.query.filter(
        User.presentation_id == presentation.id,
        User.id != user.id
    ).first()
    if existing_owner:
        return jsonify({"error": "Presentation is already assigned"}), 403

    user.presentation_id = presentation.id
    return None


@users_bp.route('/', methods=['GET'])
def get_users():
    """GET all users"""
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """GET a single user"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200


@users_bp.route('/', methods=['POST'])
def create_user():
    """POST create a new user with validation"""
    data = request.get_json() or {}
    required_fields = ['firstname', 'lastname', 'email']

    # Check for missing fields
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    session_email = _session_email()
    current_user = _current_user()
    organizer = _is_organizer(current_user)
    requested_email = data.get('email')

    if not organizer and requested_email != session_email:
        return jsonify({"error": "Cannot create an account for a different email"}), 403

    auth_value = data.get('auth') if organizer else 'presenter'
    presentation_id = data.get('presentation_id') if organizer else None

    # Create user safely
    try:
        new_user = User(
            firstname=data['firstname'],
            lastname=data['lastname'],
            email=requested_email,
            activity=data.get('activity'),
            student_year=data.get('student_year'),
            presentation_id=presentation_id,
            auth=auth_value
        )
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "User with this email already exists"}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Could not create user"}), 500

    return jsonify(new_user.to_dict()), 201


@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """PUT update user data"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    actor = _current_user()
    organizer = _is_organizer(actor)
    editing_self = actor and actor.id == user.id

    if not organizer and not editing_self:
        return jsonify({"error": "Cannot update this user"}), 403

    # Update fields if provided
    user.firstname = data.get('firstname', user.firstname)
    user.lastname = data.get('lastname', user.lastname)
    user.activity = data.get('activity', user.activity)
    user.student_year = data.get('student_year', user.student_year)

    if organizer:
        user.email = data.get('email', user.email)
        user.presentation_id = data.get('presentation_id', user.presentation_id)
        auth_val = data.get('auth', user.auth)
        if isinstance(auth_val, list):
            auth_val = ','.join(str(a) for a in auth_val)
        user.auth = auth_val
    elif 'presentation_id' in data:
        assign_error = _can_assign_presentation(user, data.get('presentation_id'))
        if assign_error:
            return assign_error

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "User with this email already exists"}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Could not update user"}), 500

    return jsonify(user.to_dict()), 200


@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """DELETE a user"""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Could not delete user"}), 500

    return jsonify({"message": "User deleted"}), 200
