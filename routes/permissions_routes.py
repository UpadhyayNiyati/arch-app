from flask import Blueprint, jsonify, request
from models import Permission, db
import uuid
import datetime

permissions_bp = Blueprint('permissions', __name__)

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
@permissions_bp.route('/permissions/<string:permission_id>', methods=['DELETE'])
def delete_permission(permission_id):
    permission = Permission.query.get_or_404(permission_id)
    try:
        # Before deleting, check if this permission is still assigned to a role.
        # This prevents a foreign key constraint error.
        # This requires importing the RolePermission model.
        # if RolePermission.query.filter_by(permission_id=permission_id).first():
        #    return jsonify({"error": "Cannot delete permission; it is still assigned to a role."}), 409

        db.session.delete(permission)
        db.session.commit()
        return jsonify({'message': 'Permission deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500