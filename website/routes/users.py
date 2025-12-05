from flask import Blueprint, jsonify, request
from website.models import User
from website import db

users_bp = Blueprint('users', __name__)


@users_bp.route('/', methods=['GET'])
def get_users():
    ''' GET all users '''
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    ''' GET one user '''
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@users_bp.route('/', methods=['POST'])
def create_user():
    ''' POST create user '''
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


@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    ''' PUT update user '''
    user = User.query.get_or_404(user_id)
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


@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    ''' DELETE user '''
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"})
