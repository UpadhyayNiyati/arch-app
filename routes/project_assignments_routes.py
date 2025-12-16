from flask import Blueprint , jsonify , request
from models import ProjectAssignments , db , Projects
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
            assigned_at = data['assigned_at'],
            company_id = data.get('company_id' , None)
        )
        
        db.session.add(new_project_assignment)
        db.session.commit()
        return jsonify({'message':'Project Assignment added successfully',
                        "assignment_id": new_project_assignment.assignment_id,
                        "project_id": new_project_assignment.project_id,
                        "user_id": new_project_assignment.user_id,
                        "role": new_project_assignment.role,
                        "assigned_at": new_project_assignment.assigned_at,
                        "company_id": new_project_assignment.company_id
                        }), 201
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
    
    if 'is_assigned' in data:
        # 🚨 FIX: Convert the string "True" or "False" from JSON to Python boolean True/False
        is_assigned_value = data['is_assigned']
        
        # This conversion handles various common string representations of True
        if isinstance(is_assigned_value, str):
            # Convert string (e.g., 'True', 'true', '1') to boolean
            is_assigned_bool = is_assigned_value.lower() in ('true', '1', 't', 'y', 'yes')
        else:
            # Assume it's already a boolean (for safety)
            is_assigned_bool = bool(is_assigned_value)
            
        project_assignment.is_assigned = is_assigned_bool

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
        # 'architect_id' : project_assignment.architect_id , 
        'role' : project_assignment.role , 
        'assigned_at' : project_assignment.assigned_at,
        'is_assigned': project_assignment.is_assigned
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


# # get project_assignments by user_id
# @project_assignments_bp.route('/project_assignments/user/<string:user_id>', methods=['GET'])
# def get_project_assignments_by_user(user_id):
#     try:
#         # Query all ProjectAssignments where the user_id matches the provided ID
#         project_assignments = ProjectAssignments.query.filter_by(user_id=user_id).all()

#         if not project_assignments:
#             # Return a 404 if no assignments are found for the given user_id
#             return jsonify({"message": f"No project assignments found for user_id: {user_id}"}), 404

#         result = []
#         for pa in project_assignments:
#             result.append({
#                 'assignment_id': pa.assignment_id,
#                 'project_id': pa.project_id,
#                 'user_id': pa.user_id,
#                 'role': pa.role,
#                 'assigned_at': pa.assigned_at,

#                 # Add 'company_id' if you want it included in the GET response
#                 # 'company_id': pa.company_id
#             })
            
#         # Return the list of project assignments
#         return jsonify(result), 200

#     except Exception as e:
#         # Handle potential database or other exceptions
#         return jsonify({"error": str(e)}), 500


# get project_assignments by user_id
@project_assignments_bp.route('/project_assignments/user/<string:user_id>', methods=['GET'])
def get_project_assignments_by_user(user_id):
    try:
        # Query all ProjectAssignments where the user_id matches the provided ID
        project_assignments = ProjectAssignments.query.filter_by(user_id=user_id).all()

        if not project_assignments:
            # Return a 404 if no assignments are found for the given user_id
            return jsonify({"message": f"No project assignments found for user_id: {user_id}"}), 404

        result = []
        for pa in project_assignments:
            # 1. Fetch the corresponding Project details
            # Assuming 'Project' is an imported SQLAlchemy model and 'project_id' is the primary key
            project = Projects.query.get(pa.project_id)
            
            # Prepare the project details dictionary
            project_details = {}
            if project:
                client_name = project.client.client_name if project.client else None
                project_details = {
                    "client_name": client_name,
                    "due_date": project.due_date.strftime('%Y-%m-%d') if project.due_date else None, # Format date for JSON
                    "location": project.location,
                    "project_description": project.project_description,
                    "project_id": project.project_id,
                    "project_name": project.project_name,
                    "start_date": project.start_date.strftime('%Y-%m-%d') if project.start_date else None, # Format date
                    "status": project.status,
                    # Assuming updated_at is a datetime object, convert it to a string
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None 
                }

            # 2. Combine assignment and project details
            assignment_details = {
                'assignment_id': pa.assignment_id,
                'project_id': pa.project_id,
                'user_id': pa.user_id,
                'role': pa.role,
                # Assuming assigned_at is a datetime object, convert it to a string
                'assigned_at': pa.assigned_at.isoformat() if pa.assigned_at else None
                # Add 'company_id' if you want it included in the GET response
                # 'company_id': pa.company_id
            }
            
            # Combine the assignment details with the project details in a single item
            # You might want to structure the output differently, e.g., 'project': project_details
            # For this example, let's include the assignment details and nest the project under a 'project' key
            result.append({
                'assignment_info': assignment_details,
                'project': project_details
            })
            
        # Return the list of project assignments with project details
        return jsonify(result), 200

    except Exception as e:
        # Handle potential database or other exceptions
        return jsonify({"error": str(e)}), 500