from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from website.models import User
from website import db

users_bp = Blueprint('users', __name__)


@users_bp.route('/', methods=['GET'])
def get_users():
    """GET all users"""
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """GET a single user"""
    user = User.query.get(user_id)
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

    # Create user safely
    try:
        new_user = User(
            firstname=data['firstname'],
            lastname=data['lastname'],
            email=data['email'],
            activity=data.get('activity'),
            presentation_id=data.get('presentation_id'),
            auth=data.get('auth')
        )
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "User with this email already exists"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify(new_user.to_dict()), 201


@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """PUT update user data"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}

    # Update fields if provided
    user.firstname = data.get('firstname', user.firstname)
    user.lastname = data.get('lastname', user.lastname)
    user.email = data.get('email', user.email)
    user.activity = data.get('activity', user.activity)
    user.presentation_id = data.get('presentation_id', user.presentation_id)

    auth_val = data.get('auth', user.auth)
    if isinstance(auth_val, list):
        auth_val = ','.join(str(a) for a in auth_val)
    user.auth = auth_val

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "User with this email already exists"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify(user.to_dict()), 200


@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """DELETE a user"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "User deleted"}), 200
