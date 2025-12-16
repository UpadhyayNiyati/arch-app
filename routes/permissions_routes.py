from flask import Blueprint, jsonify, request
from models import Permission, db , RolePermission
import uuid
import datetime
from flask_cors import CORS

permissions_bp = Blueprint('permissions', __name__)

CORS(permissions_bp)

# --- GET all permissions ---
@permissions_bp.route('/permissions', methods=['GET'])
def get_all_permissions():
    try:
        permissions = Permission.query.all()
        result = []
        for permission in permissions:
            result.append({
                'permission_id': permission.permission_id,
                'permission_name': permission.permission_name
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GET a single permission by ID ---
@permissions_bp.route('/permissions/<string:permission_id>', methods=['GET'])
def get_one_permission(permission_id):
    try:
        permission = Permission.query.get_or_404(permission_id)
        result = {
            'permission_id': permission.permission_id,
            'permission_name': permission.permission_name
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new permission ---
@permissions_bp.route('/permissions', methods=['POST'])
def add_permission():
    data = request.json
    permission_name = data.get('permission_name')
    
    if not permission_name:
        return jsonify({"error": "Permission name is required"}), 400
        
    try:
        new_permission = Permission(permission_name=permission_name)
        db.session.add(new_permission)
        db.session.commit()
        return jsonify({'message': 'Permission added successfully', 'permission_id': new_permission.permission_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PUT (update) an existing permission ---
@permissions_bp.route('/permissions/<string:permission_id>', methods=['PUT'])
def update_permission(permission_id):
    data = request.json
    permission = Permission.query.get_or_404(permission_id)
    
    try:
        if 'permission_name' in data:
            permission.permission_name = data['permission_name']
            
        db.session.commit()
        return jsonify({'message': 'Permission updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE a permission ---
# @permissions_bp.route('/permissions/<string:permission_id>', methods=['DELETE'])
# def delete_permission(permission_id):
#     permission = Permission.query.get_or_404(permission_id)
#     try:
#         # Before deleting, check if this permission is still assigned to a role.
#         # This prevents a foreign key constraint error.
#         # This requires importing the RolePermission model.
#         # if RolePermission.query.filter_by(permission_id=permission_id).first():
#         #    return jsonify({"error": "Cannot delete permission; it is still assigned to a role."}), 409

#         db.session.delete(permission)
#         db.session.commit()
#         return jsonify({'message': 'Permission deleted successfully'}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500
    
# from models import Permission, RolePermission, db

@permissions_bp.route('/permissions/<string:permission_id>', methods=['DELETE'])
def delete_permission(permission_id):
    try:
        permission = Permission.query.get_or_404(permission_id)

        # 🔒 Safety check: prevent delete if assigned to any role
        assigned = RolePermission.query.filter_by(permission_id=permission_id).first()
        if assigned:
            return jsonify({
                "error": "Cannot delete permission. It is assigned to one or more roles."
            }), 409

        db.session.delete(permission)
        db.session.commit()

        return jsonify({
            "message": "Permission deleted successfully",
            "permission_id": permission_id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    

@permissions_bp.route('/permissions/seed', methods=['POST'])
def seed_permissions():
    permissions = [
        "project_read",
        "project_write",
        "invite_team_member",
        "invite_client",
        "invite_co_admin",
        "remove_user",
        "remove_co_admin"
    ]

    created = []
    for p in permissions:
        if not Permission.query.filter_by(permission_name=p).first():
            new_p = Permission(permission_name=p)
            db.session.add(new_p)
            created.append(p)

    db.session.commit()
    return jsonify({"created_permissions": created}), 201


@permissions_bp.route('/permissions', methods=['PATCH'])
def add_missing_permissions():
    data = request.get_json()

    if not data or "permissions" not in data:
        return jsonify({"error": "Please provide a 'permissions' list"}), 400

    permissions_list = data["permissions"]
    created = []
    skipped = []

    for permission_name in permissions_list:
        existing = Permission.query.filter_by(permission_name=permission_name).first()
        
        if existing:
            skipped.append(permission_name)
        else:
            new_permission = Permission(permission_name=permission_name)
            db.session.add(new_permission)
            created.append(permission_name)

    db.session.commit()

    return jsonify({
        "added_permissions": created,
        "already_exist": skipped
    }), 200
