from flask import Blueprint , jsonify , request
from flask_jwt_extended import jwt_required , get_jwt_identity , create_access_token , create_refresh_token
from models import Company , db , User , Projects , ProjectAssignments
import logging
import datetime
import uuid
from utils.email_utils import send_email
from auth.auth import jwt_required
from flask_cors import CORS

companies_bp = Blueprint('companies_bp' , __name__)

CORS(companies_bp)

def generate_uuid():
    return str(uuid.uuid4())

# --- POST create a new company ---
@companies_bp.route('/companies' , methods = ['POST'])
# @jwt_required
def create_company():
    data = request.json
    try:
        new_company = Company(
            company_name = data.get('company_name'),
            company_address = data.get('company_address'),
            company_email = data.get('company_email'),
            company_phone = data.get('company_phone')
        )
        db.session.add(new_company)
        db.session.commit()
        return jsonify({'message':'Company created successfully',
                        "company" : {
                            "company_id":new_company.company_id , 
                            "company_name":new_company.company_name,
                            "company_address":new_company.company_address,
                            "company_email":new_company.company_email,
                            "company_phone":new_company.company_phone,
                            "created_at": new_company.created_at.isoformat() if hasattr(new_company, "created_at") else None

                        }
                    }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create company", "error": str(e)}), 400
    
# --- GET all companies ---
@companies_bp.route('/companies' , methods = ['GET'])
@jwt_required
def get_all_companies():
    try:
        companies = Company.query.all()
        result = []
        for company in companies:
            company_dict = {
                'company_id' : company.company_id,
                'company_name' : company.company_name,
                'company_address' : company.company_address,
                'company_email' : company.company_email,
                'company_phone' : company.company_phone,
                'created_at' : company.created_at
            }
            result.append(company_dict)
        return jsonify(result) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
# --- GET single company by id ---
@companies_bp.route('/companies/<string:company_id>' , methods = ['GET'])
@jwt_required
def get_company_by_id(company_id):
    try:
        company = Company.query.get_or_404(company_id)
        company_dict = {
            'company_id' : company.company_id,
            'company_name' : company.company_name,
            'company_address' : company.company_address,
            'company_email' : company.company_email,
            'company_phone' : company.company_phone,
            'created_at' : company.created_at
        }
        return jsonify(company_dict) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
# --- PUT (update) an existing company ---
@companies_bp.route('/companies/<string:company_id>' , methods = ['PUT'])
@jwt_required
def update_company(company_id):
    data = request.json
    company = Company.query.get_or_404(company_id)
    
    try:
        if 'company_name' in data:
            company.company_name = data['company_name']
        if 'company_address' in data:
            company.company_address = data['company_address']
        if 'company_email' in data:
            company.company_email = data['company_email']
        if 'company_phone' in data:
            company.company_phone = data['company_phone']
        
        db.session.commit()
        updated_company_dict = {
            'company_id' : company.company_id,
            'company_name' : company.company_name,
            'company_address' : company.company_address,
            'company_email' : company.company_email,
            'company_phone' : company.company_phone,
            'created_at' : company.created_at
        }
        return jsonify(updated_company_dict), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
# --- DELETE a company ---
@companies_bp.route('/companies/<string:company_id>' , methods = ['DELETE'])
@jwt_required
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    
    try:
        User.query.filter_by(company_id=company_id).delete()
        db.session.delete(company)
        db.session.commit()
        return jsonify({"message":"Company deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500
    
#---GET companies by name ---
@companies_bp.route('/companies/search' , methods = ['GET'])
@jwt_required
def get_companies_by_name():
    name_query = request.args.get('name' , '')
    try:
        companies = Company.query.filter(Company.company_name.ilike(f'%{name_query}%')).all()
        result = []
        for company in companies:
            company_dict = {
                'company_id' : company.company_id , 
                'company_name' : company.company_name ,
                'company_address' : company.company_address ,
                'company_email' : company.company_email ,
                'company_phone' : company.company_phone ,
                'created_at' : company.created_at
            }
            result.append(company_dict)
        return jsonify(result) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    

@companies_bp.route('/company/<string:company_id>/members', methods=['GET'])
@jwt_required   # optional, remove if not using JWT
def get_company_members(company_id):
    try:
        company = Company.query.get(company_id)
        if not company:
            return jsonify({"error": "Company not found"}), 404

        members = User.query.filter_by(company_id=company_id).all()

        members_list = [
            {
                "user_id": member.user_id,
                "user_name": member.user_name,
                "user_email": member.user_email
            }
            for member in members
        ]

        return jsonify({
            "company_id": company.company_id,
            "company_name": company.company_name,
            "total_members": len(members_list),
            "members": members_list
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@companies_bp.route('/projects/<string:project_id>/members', methods=['POST'])
@jwt_required
def add_project_members(project_id):
    try:
        data = request.json
        user_ids = data.get('user_ids', [])
        role = data.get('role', 'member')

        if not user_ids:
            return jsonify({"error": "No user_ids provided"}), 400

        # Verify project exists
        project = Projects.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        
        company_id = project.company_id
        
        added_members = []
        skipped_members = []

        for uid in user_ids:

            # Check if user exists
            user = User.query.get(uid)
            if not user:
                skipped_members.append({"user_id": uid, "reason": "User not found"})
                continue

            # Prevent duplicate assignment
            existing = ProjectAssignments.query.filter_by(
                user_id=uid,
                project_id=project_id
            ).first()

            if existing:
                if existing.is_assigned == True:
                    skipped_members.append({"user_id": uid, "reason": "Already assigned"})
                else:
                    existing.is_assigned = True
                    existing.role = role # Optional: Update role upon re-assignment
                    db.session.add(existing)
                    added_members.append({"user_id": uid, "user_name": user.user_name, "status": "re-assigned"})
            
            else:
            # Create assignment entry
                assignment = ProjectAssignments(
                    user_id=uid,
                    project_id=project_id,
                    role=role,
                    company_id=company_id,
                    is_assigned=True,
                    assigned_at=datetime.datetime.utcnow()
                )

                db.session.add(assignment)
                added_members.append({"user_id": uid, "user_name": user.user_name})

            db.session.commit()

            return jsonify({
                "message": "Assignments processed",
                "project_id": project_id,
                "added_members": added_members,
                "skipped": skipped_members,
                "company_id": company_id
            }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@companies_bp.route('/projects/<string:project_id>/members/<string:user_id>', methods=['DELETE'])
@jwt_required
def remove_project_member(project_id, user_id):
    try:
        assignment = ProjectAssignments.query.filter_by(
            project_id=project_id,
            user_id=user_id,
            is_assigned = True
        ).first()

        if not assignment:
            return jsonify({"error": "User not assigned to project"}), 404
        
        assignment.is_assigned = False
        db.session.add(assignment)
        # db.session.delete(assignment)
        db.session.commit()

        return jsonify({
            "message": "User removed from project",
            "user_id": user_id,
            "project_id": project_id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@companies_bp.route('/projects/<string:project_id>/members', methods=['GET'])
@jwt_required
def get_project_members(project_id):
    try:
        project = Projects.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        company_id = project.company_id
        users = User.query.filter_by(company_id=company_id).all()
        assignments = ProjectAssignments.query.filter_by(project_id=project_id).all()
        assignment_map = {a.user_id: a for a in assignments}

        
        members = []
        for a in assignments:
            user = User.query.get(a.user_id)
            if user:
                members.append({
                    "user_id": user.user_id,
                    "user_name": user.user_name,
                    "user_email": user.user_email,
                    "role": a.role,
                    "assigned_at": a.assigned_at
                })

        return jsonify({
            "project_id": project_id,
            "total_members": len(members),
            "members": members
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500