# decorators.py
from functools import wraps
from flask import request, jsonify, g
from models import db, Permission, UserRole, RolePermission

def has_permission(permission_name):
    """
    A decorator to check if a user has a specific permission.
    It assumes the user's ID is available in the 'X-User-ID' header.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Get the user's ID from the request headers
            user_id = request.headers.get('X-User-ID')
            if not user_id:
                return jsonify({"error": "Unauthorized: User not identified"}), 401

            # 2. Get the roles associated with the user
            user_roles = db.session.query(UserRole.role_id).filter_by(user_id=user_id).all()
            if not user_roles:
                return jsonify({"error": "Forbidden: User has no roles"}), 403

            role_ids = [r[0] for r in user_roles]

            # 3. Find the required permission by name
            required_permission = Permission.query.filter_by(name=permission_name).first()
            if not required_permission:
                return jsonify({"error": f"Permission '{permission_name}' not found"}), 500

            # 4. Check if any of the user's roles have the required permission
            has_access = db.session.query(RolePermission).filter(
                RolePermission.role_id.in_(role_ids),
                RolePermission.permission_id == required_permission.id
            ).first()

            if not has_access:
                return jsonify({"error": f"Forbidden: You do not have the '{permission_name}' permission"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator