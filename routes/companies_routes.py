from flask import Blueprint , jsonify , request
from models import Company , db
import logging
import datetime
import uuid
from flask_cors import CORS

companies_bp = Blueprint('companies_bp' , __name__)

CORS(companies_bp)

def generate_uuid():
    return str(uuid.uuid4())

# --- POST create a new company ---
@companies_bp.route('/companies' , methods = ['POST'])
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
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    try:
        db.session.delete(company)
        db.session.commit()
        return jsonify({"message":"Company deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500
    
#---GET companies by name ---
@companies_bp.route('/companies/search' , methods = ['GET'])
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