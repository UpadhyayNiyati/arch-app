from flask import Flask , Blueprint , jsonify , request
from datetime import datetime
from models import db , User_Company_Role , User , Role , Company , UserRole , Permission , RolePermission
from auth.authhelpers import jwt_required
import datetime
import uuid


company_users_role_bp = Blueprint("user_company_role", __name__)

@company_users_role_bp.route('/companies/<int:company_id>/users', methods=['POST'])
@jwt_required
def add_user_to_company(company_id):
    data = request.get_json()

    user_id = data.get('user_id')
    role_id = data.get('role_id')

    ucr = User_Company_Role(
        user_id=user_id,
        company_id=company_id,
        role_id=role_id
    )

    db.session.add(ucr)
    db.session.commit()

    return jsonify({"message": "User added to company" ,
                    "user_id":user_id , 
                    "company_id":company_id ,
                    "role_id" : role_id
                    }), 201


@company_users_role_bp.route('/companies/<int:company_id>/users', methods=['POST'])
@jwt_required
def add_user_to_company(company_id):
    data = request.get_json()

    user_id = data.get('user_id')
    role_id = data.get('role_id')

    if not user_id or not role_id:
        return jsonify({"error": "user_id and role_id are required"}), 400

    ucr = User_Company_Role(
        user_id=user_id,
        company_id=company_id,
        role_id=role_id
    )

    db.session.add(ucr)
    db.session.commit()

    return jsonify({
        "message": "User added to company",
        "user_id": user_id,
        "company_id": company_id,
        "role_id": role_id
    }), 201


@company_users_role_bp.route('/companies/<int:company_id>/users', methods=['GET'])
@jwt_required
def list_company_users(company_id):
    users = (
        db.session.query(User, Role)
        .join(User_Company_Role, User.id == User_Company_Role.user_id)
        .join(Role, Role.id == User_Company_Role.role_id)
        .filter(User_Company_Role.company_id == company_id)
        .all()
    )

    result = []
    for user, role in users:
        result.append({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": role.name
        })

    return jsonify(result), 200



@company_users_role_bp.route('/users/<int:user_id>/companies', methods=['GET'])
@jwt_required
def list_user_companies(user_id):
    companies = (
        db.session.query(Company, Role)
        .join(User_Company_Role, Company.id == User_Company_Role.company_id)
        .join(Role, Role.id == User_Company_Role.role_id)
        .filter(User_Company_Role.user_id == user_id)
        .all()
    )

    result = []
    for company, role in companies:
        result.append({
            "company_id": company.id,
            "company_name": company.name,
            "role": role.name
        })

    return jsonify(result), 200

@company_users_role_bp.route(
    '/companies/<int:company_id>/users/<int:user_id>/role',
    methods=['PUT']
)
@jwt_required
def change_user_role(company_id, user_id):
    data = request.get_json()
    role_id = data.get('role_id')

    if not role_id:
        return jsonify({"error": "role_id is required"}), 400

    ucr = User_Company_Role.query.filter_by(
        company_id=company_id,
        user_id=user_id
    ).first()

    if not ucr:
        return jsonify({"error": "User not found in company"}), 404

    ucr.role_id = role_id
    db.session.commit()

    return jsonify({
        "message": "User role updated",
        "user_id": user_id,
        "company_id": company_id,
        "role_id": role_id
    }), 200


@company_users_role_bp.route(
    '/companies/<int:company_id>/users/<int:user_id>',
    methods=['DELETE']
)
@jwt_required
def remove_user_from_company(company_id, user_id):
    ucr = User_Company_Role.query.filter_by(
        company_id=company_id,
        user_id=user_id
    ).first()

    if not ucr:
        return jsonify({"error": "User not found in company"}), 404

    db.session.delete(ucr)
    db.session.commit()

    return jsonify({
        "message": "User removed from company",
        "user_id": user_id,
        "company_id": company_id
    }), 200

