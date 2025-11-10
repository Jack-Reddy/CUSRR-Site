from flask import Blueprint, jsonify, request
from models import db, User
from sqlalchemy.exc import IntegrityError

users_bp = Blueprint('users', __name__)

# GET all users
@users_bp.route('/', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

# GET one user
@users_bp.route('/<int:id>', methods=['GET'])
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_dict())

# POST create user
@users_bp.route('/', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    # Validate required fields
    required_fields = ['firstname', 'lastname', 'email']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Validate email format (basic check)
    email = data['email']
    if '@' not in email or '.' not in email:
        return jsonify({"error": "Invalid email format"}), 400
    
    # Check for duplicate email
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "User with this email already exists"}), 409
    
    try:
        new_user = User(
            firstname=data['firstname'],
            lastname=data['lastname'],
            email=email,
            activity=data.get('activity'),
            presentation_id=data.get('presentation_id')
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database integrity error"}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create user"}), 500

# PUT update user
@users_bp.route('/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    # Validate email format if provided
    if 'email' in data and data['email']:
        email = data['email']
        if '@' not in email or '.' not in email:
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check for duplicate email (excluding current user)
        existing_user = User.query.filter_by(email=email).filter(User.id != id).first()
        if existing_user:
            return jsonify({"error": "User with this email already exists"}), 409
    
    try:
        user.firstname = data.get('firstname', user.firstname)
        user.lastname = data.get('lastname', user.lastname)
        user.email = data.get('email', user.email)
        user.activity = data.get('activity', user.activity)
        user.presentation_id = data.get('presentation_id', user.presentation_id)
        db.session.commit()
        return jsonify(user.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database integrity error"}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update user"}), 500


# DELETE user
@users_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get_or_404(id)
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete user"}), 500
