from flask import Blueprint, jsonify, request
from website.models import User
from website import db

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
    return jsonify(new_user.to_dict()), 201


# PUT update user
@users_bp.route('/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    user.firstname = data.get('firstname', user.firstname)
    user.lastname = data.get('lastname', user.lastname)
    user.email = data.get('email', user.email)
    user.activity = data.get('activity', user.activity)
    user.presentation_id = data.get('presentation_id', user.presentation_id)

    auth_val = data.get('auth', user.auth)
    if isinstance(auth_val, list):
        auth_val = ','.join(str(a) for a in auth_val)

    user.auth = auth_val
    db.session.commit()
    return jsonify(user.to_dict())


# DELETE user
@users_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"})
