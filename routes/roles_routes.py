from flask import Blueprint, jsonify, request
from models import Role, db
import uuid
from datetime import datetime

roles_bp = Blueprint('roles', __name__)

# --- GET all roles ---
@roles_bp.route('/roles', methods=['GET'])
def get_all_roles():
    try:
        roles = Role.query.all()
        result = []
        for role in roles:
            result.append({
                'role_id': role.role_id,
                'role_name': role.role_name
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GET a single role by ID ---
@roles_bp.route('/roles/<string:role_id>', methods=['GET'])
def get_one_role(role_id):
    try:
        role = Role.query.get_or_404(role_id)
        result = {
            'role_id': role.role_id,
            'role_name': role.role_name
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new role ---
@roles_bp.route('/roles', methods=['POST'])
def add_role():
    data = request.json
    role_name = data.get('role_name')
    
    if not role_name:
        return jsonify({"error": "Role name is required"}), 400
    
    try:
        new_role = Role(role_name=role_name)
        db.session.add(new_role)
        db.session.commit()
        return jsonify({'message': 'Role added successfully', 'role_id': new_role.role_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PUT (update) an existing role ---
@roles_bp.route('/roles/<string:role_id>', methods=['PUT'])
def update_role(role_id):
    data = request.json
    role = Role.query.get_or_404(role_id)
    
    try:
        if 'role_name' in data:
            role.role_name = data['role_name']
        
        db.session.commit()
        return jsonify({'message': 'Role updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE a role ---
@roles_bp.route('/roles/<string:role_id>', methods=['DELETE'])
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    try:
        # Before deleting, you should check if this role is assigned to any user
        # or has any permissions linked to it, to prevent a foreign key error.
        db.session.delete(role)
        db.session.commit()
        return jsonify({'message': 'Role deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500