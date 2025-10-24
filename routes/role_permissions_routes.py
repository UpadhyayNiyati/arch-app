# role_permissions_bp.py
from flask import Blueprint, jsonify, request
from models import RolePermission, Role, Permission, db
import uuid
import datetime

role_permissions_bp = Blueprint('role_permissions', __name__)

# --- POST: Assign a permission to a role ---
@role_permissions_bp.route('/role_permissions', methods=['POST'])
def add_role_permission():
    data = request.json
    role_id = data.get('role_id')
    permission_id = data.get('permission_id')

    if not all([role_id, permission_id]):
        return jsonify({"error": "role_id and permission_id are required"}), 400

    try:
        # Check if the role and permission exist to prevent a foreign key error
        role = Role.query.get(role_id)
        if not role:
            return jsonify({"error": "Role not found"}), 404
        permission = Permission.query.get(permission_id)
        if not permission:
            return jsonify({"error": "Permission not found"}), 404

        # Prevent duplicate entries
        if RolePermission.query.filter_by(role_id=role_id, permission_id=permission_id).first():
            return jsonify({"message": "This permission is already assigned to this role"}), 409

        new_assignment = RolePermission(role_id=role.role_id, permission_id=permission.permission_id)
        db.session.add(new_assignment)
        db.session.commit()
        return jsonify({'message': 'Permission assigned to role successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- GET all role-permission assignments ---
@role_permissions_bp.route('/role_permissions', methods=['GET'])
def get_all_role_permissions():
    try:
        assignments = RolePermission.query.all()
        result = []
        for assignment in assignments:
            result.append({
                'role_permission_id': assignment.role_permission_id,
                'role_id': assignment.role_id,
                'permission_id': assignment.permission_id
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GET a single assignment by its unique ID ---
@role_permissions_bp.route('/role_permissions/<string:assignment_id>', methods=['GET'])
def get_one_role_permission(assignment_id):
    try:
        assignment = RolePermission.query.get_or_404(assignment_id)
        result = {
            'role_permission_id': assignment.role_permission_id,
            'role_id': assignment.role_id,
            'permission_id': assignment.permission_id
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🆕 --- PUT (Update) a role-permission assignment ---
@role_permissions_bp.route('/role_permissions/<string:assignment_id>', methods=['PUT'])
def update_role_permission(assignment_id):
    data = request.json
    new_role_id = data.get('role_id')
    new_permission_id = data.get('permission_id')
    
    # At least one of the IDs must be provided for the update
    if not (new_role_id or new_permission_id):
        return jsonify({"error": "At least one of 'role_id' or 'permission_id' is required"}), 400
    
    assignment = RolePermission.query.get_or_404(assignment_id)
    
    try:
        # Update role_id if provided
        if new_role_id:
            if not Role.query.get(new_role_id):
                return jsonify({"error": "New role not found"}), 404
            assignment.role_id = new_role_id
            
        # Update permission_id if provided
        if new_permission_id:
            if not Permission.query.get(new_permission_id):
                return jsonify({"error": "New permission not found"}), 404
            assignment.permission_id = new_permission_id

        db.session.commit()
        return jsonify({'message': 'Assignment updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE a role-permission assignment ---
@role_permissions_bp.route('/role_permissions/<string:assignment_id>', methods=['DELETE'])
def delete_role_permission(assignment_id):
    assignment = RolePermission.query.get_or_404(assignment_id)
    try:
        db.session.delete(assignment)
        db.session.commit()
        return jsonify({'message': 'Permission revoked from role successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- A useful GET route to get all permissions for a specific role ---
@role_permissions_bp.route('/role_permissions/role/<string:role_id>', methods=['GET'])
def get_permissions_for_role(role_id):
    try:
        role = Role.query.get(role_id)
        if not role:
            return jsonify({"error": "Role not found"}), 404

        # Using a join for better performance
        assignments = db.session.query(Permission).join(RolePermission).filter(RolePermission.role_id == role_id).all()
        
        permission_list = [{
            'permission_id': p.permission_id,
            'permission_name': p.permission_name
        } for p in assignments]

        return jsonify(permission_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500