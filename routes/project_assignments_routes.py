from flask import Blueprint , jsonify , request
from models import ProjectAssignments , db
import datetime
import uuid
from flask_cors import CORS

project_assignments_bp = Blueprint('project_assignments', __name__)
CORS(project_assignments_bp)

#get all project_assignments
@project_assignments_bp.route('/project_assignments' , methods = ['GET'])
def gett_all_project_assignments():
    try:
        project_assignments = ProjectAssignments.query.all()
        result = []
        for pa in project_assignments:
            result.append({
                'assignment_id' : pa.assignment_id , 
                'project_id' : pa.project_id , 
                'user_id' : pa.user_id , 
                'role' : pa.role , 
                'assigned_at' : pa.assigned_at
            })
        return jsonify(result) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    

#get single project_assignment by id
@project_assignments_bp.route('/project_assignments/<string:assignment_id>' , methods = ['GET'])
def get_project_assignment_by_id(assignment_id):
    project_assignment = ProjectAssignments.query.get_or_404(assignment_id)
    if not project_assignment:
        return jsonify({"message":"Project Assignment not found"}) , 404
    result = {
        'assignment_id' : project_assignment.assignment_id , 
        'project_id' : project_assignment.project_id , 
        'user_id' : project_assignment.user_id , 
        'role' : project_assignment.role , 
        'assigned_at' : project_assignment.assigned_at
    }
    return jsonify(result) , 200

#post project_assignment
@project_assignments_bp.route('/project_assignments' , methods = ['POST'])
def add_project_assignments():
    try:
        data = request.json
        # 'user_id' has been added back to the required_fields
        required_fields = ['project_id', 'user_id', 'role', 'assigned_at']
        
        # Check all required fields
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'All fields are required'}), 400
            
        new_project_assignment = ProjectAssignments(
            project_id = data['project_id'],
            user_id = data['user_id'],  # The user ID is now being used
            role = data['role'],
            assigned_at = data['assigned_at']
        )
        
        db.session.add(new_project_assignment)
        db.session.commit()
        return jsonify({'message':'Project Assignment added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}) , 500
    
#update project_assignment by id
@project_assignments_bp.route('/project_assignments/<string:assignment_id>' , methods = ['PUT'])
def update_project_assignment(assignment_id):
    data = request.json
    project_assignment = ProjectAssignments.query.get_or_404(assignment_id)
    if not project_assignment:
        return jsonify({"message":"Project Assignment not found"}) , 404
    if 'project_id' in data:
        project_assignment.project_id = data['project_id']
    if 'architect_id' in data:
        project_assignment.architect_id = data['architect_id']
    if 'role' in data:
        project_assignment.role = data['role']
    if 'assigned_date' in data:
        project_assignment.assigned_date = data['assigned_data']
    db.session.commit()
    result = {
        'assignment_id' : project_assignment.assignment_id , 
        'project_id' : project_assignment.project_id , 
        'architect_id' : project_assignment.architect_id , 
        'role' : project_assignment.role , 
        'assigned_date' : project_assignment.assigned_date
    }
    return jsonify(result) , 200

#delete project_assignment by id
@project_assignments_bp.route('/project_assignments/<string:assignment_id>' , methods = ['DELETE'])
def delete_project_assignment(assignment_id):
    project_assignment = ProjectAssignments.query.get_or_404(assignment_id)
    if not project_assignment:
        return jsonify({"message":"Project Assignment not found"}) , 404
    try:
        db.session.delete(project_assignment)
        db.session.commit()
        return jsonify({'message':'Project Assignment deleted successfully'}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
