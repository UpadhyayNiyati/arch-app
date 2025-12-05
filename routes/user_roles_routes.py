# user_roles_bp.py
from flask import Blueprint, jsonify, request
from models import User, Role, UserRole, db
from flask_cors import CORS
from auth.auth import jwt_required

user_roles_bp = Blueprint('user_roles', __name__)
CORS(user_roles_bp)

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
    

@user_roles_bp.route(
    '/companies/<string:company_id>/users/<string:user_id>/roles/<string:role_id>',
    methods=['POST'])
@jwt_required # Keep commented as per original, or uncomment if needed for request.current_user_id
def grant_role(company_id, user_id, role_id):
    # Retrieve current user ID from the request object, assuming it's populated by auth middleware
    current_user_id = request.current_user_id

    # 1. Check if the current user is an 'Admin' of this company
    admin_role = Role.query.filter_by(
        company_id=company_id,
        name="Administrator"
    ).first()
    
    # If the 'Admin' role doesn't exist for the company, we can't check permissions
    if not admin_role:
        return jsonify({"error": "Admin role not defined for this company"}), 403

    is_admin = UserRole.query.filter_by(
        user_id=user_id,
        role_id=admin_role.id
    ).first()

    if not is_admin:
        return jsonify({"error": "Only company admins can assign roles"}), 403

    # 2. Check if the target user exists
    user = User.query.get_or_404(user_id) # Using get_or_404 as in assign_role_to_user

    # 3. Check if the role exists within the specified company
    role = Role.query.filter_by(id=role_id, company_id=company_id).first()
    if not role:
        return jsonify({"error": "Role not found in this company"}), 404

    # 4. Check if the role is already assigned
    existing_link = UserRole.query.filter_by(
        user_id=user_id,
        role_id=role_id
    ).first()

    if existing_link:
        # Consistent with assign_role_to_user which returns 409 for existing link
        # However, the original grant_role returned 200, so let's stick to the original's logic here for consistency
        return jsonify({"message": "User already has this role"}), 200

    # 5. Assign the role and handle transaction
    try:
        user_role = UserRole(user_id=user_id, role_id=role_id)
        db.session.add(user_role)
        db.session.commit()

        return jsonify({"message": "Role granted successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500