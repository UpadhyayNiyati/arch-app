# role_permissions_bp.py
from flask import Blueprint, jsonify, request
from models import RolePermission, Role, Permission, db
import uuid
import datetime
from flask_cors import CORS

role_permissions_bp = Blueprint('role_permissions', __name__)
CORS(role_permissions_bp)

# --- POST: Assign a permission to a role ---
@role_permissions_bp.route('/role_permissions', methods=['POST' ])
def add_role_permission():
    data = request.json
    role_id = data.get('role_id')
    permission_id = data.get('permission_id')
    is_read = data.get('is_read', False)
    is_write = data.get('is_write', False)


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

        new_assignment = RolePermission(role_id=role.role_id, permission_id=permission.permission_id,
                                        is_read=is_read,
            is_write=is_write
                                        )
        db.session.add(new_assignment)
        db.session.commit()
        return jsonify({'message': 'Permission assigned to role successfully',
                        "role_id":role_id,
                        "permission_id":permission_id ,
                        "is_read": is_read,
                        "is_write": is_write
                        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- GET all role-permission assignments ---
# @role_permissions_bp.route('/role_permissions', methods=['GET'])
# def get_all_role_permissions():
#     try:
#         assignments = RolePermission.query.all()
#         result = []
#         for assignment in assignments:
#             result.append({
#                 'role_permission_id': assignment.role_permission_id,
#                 'role_id': assignment.role_id,
#                 'permission_id': assignment.permission_id
#             })
#         return jsonify(result), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@role_permissions_bp.route('/role_permissions', methods=['GET'])
def get_all_role_permissions():
    try:
        assignments = RolePermission.query.all()

        result = []
        for assignment in assignments:
            result.append({
                "role_permission_id": assignment.role_permission_id,
                "role": {
                    "role_id": assignment.role.role_id,
                    "role_name": assignment.role.role_name
                },
                "permission": {
                    "permission_id": assignment.permission.permission_id,
                    "permission_name": assignment.permission.permission_name
                }
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- GET a single assignment by its unique ID ---
@role_permissions_bp.route('/role_permissions/<string:role_permission_id>', methods=['GET'])
def get_one_role_permission(role_permission_id):
    try:
        assignment = RolePermission.query.get_or_404(role_permission_id)
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
@role_permissions_bp.route('/role_permissions/<string:role_permission_id>', methods=['DELETE'])
def delete_role_permission(role_permission_id):
    assignment = RolePermission.query.get_or_404(role_permission_id)
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
    

# --- A useful GET route to get all permissions for a specific role ---
@role_permissions_bp.route('/role_permissions/role/<string:role_id>', methods=['GET'])
def get_permissions_for_role_with_role_id(role_id):
    try:
        role = Role.query.get(role_id)
        if not role:
            return jsonify({"error": "Role not found"}), 404

        # Query joins Permission and RolePermission tables to find permissions
        # associated with the given role_id.
        assignments = db.session.query(Permission).join(RolePermission).filter(RolePermission.role_id == role_id).all()
        
        permission_list = [{
            'permission_id': p.permission_id,
            'permission_name': p.permission_name
        } for p in assignments]

        return jsonify(permission_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@role_permissions_bp.route('/role_permissions/details', methods=['GET'])
def get_role_permission_details():
    try:
        assignments = RolePermission.query.all()

        result = []
        for assignment in assignments:
            result.append({
                "role_permission_id": assignment.role_permission_id,
                "role_id": assignment.role_id,
                "permission_id": assignment.permission_id,
                "is_read": bool(assignment.is_read),
                "is_write": bool(assignment.is_write)
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
