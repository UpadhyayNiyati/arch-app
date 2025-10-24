# user_roles_bp.py
from flask import Blueprint, jsonify, request
from models import User, Role, UserRole, db

user_roles_bp = Blueprint('user_roles', __name__)

# --- POST: Assign a role to a user ---
@user_roles_bp.route('/users/<string:user_id>/roles/<string:role_id>', methods=['POST'])
def assign_role_to_user(user_id, role_id):
    user = User.query.get_or_404(user_id)
    role = Role.query.get_or_404(role_id)
    
    try:
        # Check if the relationship already exists
        existing_link = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first()
        if existing_link:
            return jsonify({"error": "Role already assigned to this user"}), 409
        
        new_link = UserRole(user_id=user.user_id, role_id=role.role_id)
        db.session.add(new_link)
        db.session.commit()
        return jsonify({"message": "Role assigned to user successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE: Remove a role from a user ---
@user_roles_bp.route('/users/<string:user_id>/roles/<string:role_id>', methods=['DELETE'])
def remove_role_from_user(user_id, role_id):
    link = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first_or_404()
    
    try:
        db.session.delete(link)
        db.session.commit()
        return jsonify({"message": "Role removed from user successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500