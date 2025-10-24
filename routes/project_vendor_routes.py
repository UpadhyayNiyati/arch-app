from flask import Blueprint , jsonify , request
from models import  Projectvendor, db
import datetime
import uuid
project_vendor_bp = Blueprint('project_vendor', __name__)

#get all project_vendors
@project_vendor_bp.route('/project_vendors' , methods = ['GET'])
def get_all_project_vendors():
    try:
        project_vendors = Projectvendor.query.all()
        result = []
        for pv in project_vendors:
            result.append({
                'project_vendor_id' : pv.project_vendor_id , 
                'project_id' : pv.project_id , 
                'vendor_id' : pv.vendor_id , 
                'role' : pv.role , 
                'assigned_date' : pv.assigned_date
            })
        return jsonify(result) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#get single project_vendor by id
@project_vendor_bp.route('/project_vendors/<string:project_vendor_id>' , methods = ['GET'])
def get_project_vendor_by_id(project_vendor_id):
    project_vendor = Projectvendor.query.get_or_404(project_vendor_id)
    if not project_vendor:
        return jsonify({"message":"Project Vendor not found"}) , 404
    result = {
        'project_vendor_id' : project_vendor.project_vendor_id , 
        'project_id' : project_vendor.project_id , 
        'vendor_id' : project_vendor.vendor_id , 
        'role' : project_vendor.role , 
        'assigned_date' : project_vendor.assigned_date
    }
    return jsonify(result) , 200

#post project_vendor
@project_vendor_bp.route('/project_vendors' , methods = ['POST'])
def add_project_vendors():
    try:
        data = request.json
        required_fields = ['project_id' , 'vendor_id' , 'role' , 'assigned_date']
        for fields in required_fields:
            if fields not in data:
                return jsonify({'error' : f"'{fields}' is required"}), 400
        new_project_vendor = Projectvendor(
            project_id = data['project_id'] ,
            vendor_id = data['vendor_id'] , 
            role = data['role'] , 
            assigned_date = data['assigned_date']
        )
        db.session.add(new_project_vendor)
        db.session.commit()
        return jsonify({'message':'Project Vendor added successfully'}) , 201
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#update project_vendor by id
@project_vendor_bp.route('/project_vendors/<string:project_vendor_id>' , methods = ['PUT'])
def update_project_vendor(project_vendor_id):
    data = request.json
    project_vendor = Projectvendor.query.get_or_404(project_vendor_id)
    if not project_vendor:
        return jsonify({"message":"Project Vendor not found"}) , 404
    if 'project_id' in data:
        project_vendor.project_id = data['project_id']
    if 'vendor_id' in data:
        project_vendor.vendor_id = data['vendor_id']
    if 'role' in data:
        project_vendor.role = data['role']
    if 'assigned_date' in data:
        project_vendor.assigned_date = data['assigned_date']
    try:
        db.session.commit()
        return jsonify({'message':'Project Vendor updated successfully'}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#delete project_vendor by id
@project_vendor_bp.route('/project_vendors/<string:project_vendor_id>' , methods = ['DELETE'])
def delete_project_vendor(project_vendor_id):
    project_vendor = Projectvendor.query.get_or_404(project_vendor_id)
    if not project_vendor:
        return jsonify({"message":"Project Vendor not found"}) , 404
    try:
        db.session.delete(project_vendor)
        db.session.commit()
        return jsonify({'message':'Project Vendor deleted successfully'}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500