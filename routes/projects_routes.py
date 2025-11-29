from flask import Blueprint , jsonify , request
from models import  Projects, db , Clients , Spaces , Tasks
import datetime
import uuid
from datetime import datetime, date # Import date for correct data type
from flask_cors import CORS
from flask_jwt_extended import  get_jwt_identity , create_access_token , create_refresh_token
from auth.authhelpers import jwt_required

projects_bp = Blueprint('projects', __name__)

CORS(projects_bp)

# --- GET all projects ---
@projects_bp.route('/projects', methods=['GET'])
@jwt_required
def get_all_projects():
    try:
        # Fetch all projects from the database
        projects = Projects.query.all()
        
        result = []
        for project in projects:
            result.append({
                'project_id': project.project_id,
                'project_name': project.project_name,
                'client_name': project.client.client_name if project.client else None,  # Fetch related client's name
                'project_description': project.project_description,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                # 'site_area': project.site_area,
                'location': project.location,
                'due_date': project.due_date.isoformat() if project.due_date else None,
                'status': project.status or 'Not Started',
                'updated_at': project.updated_at.isoformat() if project.updated_at else None
                # 'budget': project.budget,
                # 'created_at': project.created_at.isoformat() if project.created_at else None
            })

        # Return the full list of projects (no IDs)
        return jsonify({
            'projects': result,
            'total_projects': len(result)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def _serilalize_datetime(dt):
    if isinstance(dt ,(datetime , date)):
        return dt.isoformat()
    return None

# --- GET single project by id ---
@projects_bp.route('/projects/<string:project_id>', methods=['GET'])
@jwt_required
def get_project_by_id(project_id):
    try:
        # Fetch the project by ID (404 if not found)
        project = Projects.query.get_or_404(project_id)

        spaces_count = Spaces.query.filter_by(project_id=project_id).count()

        tasks_performed_count = Tasks.query.filter_by(
            project_id=project_id,
            # is_completed=True 
           ).count()

        total_actions = tasks_performed_count + spaces_count

        # Prepare the response (exclude IDs)
        result = {
            'project_id': project.project_id,
            'project_name': project.project_name,
            'client_name': project.client.client_name if project.client else None,
            'project_description': project.project_description,
            # 'start_date': project.start_date.isoformat() if project.start_date else None,
            # 'site_area': project.site_area,
            'location': project.location,
            'due_date': project.due_date.isoformat() if project.due_date else None,
            'status': project.status or 'Not Started',
            'budget': project.budget,
            'updated_at': project.updated_at.isoformat() if project.updated_at else None,
            'total_actions_count': total_actions
        }
            # 'created_at': project.created_at.isoformat() if project.created_at else None
        

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new project ---
@projects_bp.route('/projects', methods=['POST'])
@jwt_required
def add_projects():
    data = request.json
    # The required_fields list has been updated to include 'client_id'
    required_fields = ['project_name' ,'location', 'due_date', 'status', 'project_description', 'client_name']
    
    # 1. Check if all required fields are present
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'All fields are required'}), 400
    
    try:

        client_name = data['client_name']

        # 1. Verify that the client exists
        client = Clients.query.filter_by(client_name=client_name).first()

        if client is None:
            new_client = Clients(client_name = client_name)
            db.session.add(new_client)
            db.session.commit()
            client_id = new_client.client_id
        else:
            client_id = client.client_id

        # 2. Instantiate the Projects model with proper date conversion
        new_project = Projects(
            project_name=data['project_name'],
            # site_area=data['site_area'],
            location=data['location'],
            # budget=data['budget'],
            # start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date(),
            status=data['status'],
            project_description=data['project_description'],
            # client_name=data['client_name']
            client_id = client_id
        )
        
        # 3. Add and commit the new project to the database
        db.session.add(new_project)
        db.session.commit()
        return jsonify({'message': 'Project added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
        
# --- PUT (update) an existing project ---
@projects_bp.route('/projects/<string:project_id>', methods=['PUT'])
@jwt_required
def update_project(project_id):
    data = request.json
    project = Projects.query.get_or_404(project_id)
    
    try:
        if 'project_name' in data:
            project.project_name = data['project_name']
        if 'site_area' in data:
            project.site_area = data['site_area']
        if 'location' in data:
            project.location = data['location']
        if 'budget' in data:
            project.budget = data['budget']
        if 'start_date' in data:
            project.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'due_date' in data:
            project.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        if 'status' in data:
            project.status = data['status']
        if 'project_description' in data:
            project.project_description = data['project_description']
        if 'client_id' in data:
            project.client_id = data['client_id']
        
        db.session.commit()
        return jsonify({"message": "Project updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
        
# --- DELETE a project ---
@projects_bp.route('/projects/<string:project_id>', methods=['DELETE'])
@jwt_required
def delete_project(project_id):
    project = Projects.query.get_or_404(project_id)
    try:
        db.session.delete(project)
        db.session.commit()
        return jsonify({"message": "Project deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
# Assuming all other imports and code from your prompt are present

@projects_bp.route('/projects/<string:project_id>', methods=['PATCH'])
# @jwt_required
def update_project_client(project_id):
    data = request.json
    
    # 1. Find the project by its ID
    project = Projects.query.get_or_404(project_id)

    # 2. Check if 'client_id' is provided in the request body
    if 'client_id' not in data:
        return jsonify({"error": "client_id is required to update"}), 400
    
    new_client_id = data.get('client_id')

    try:
        # 3. Update the client_id field
        project.client_id = new_client_id
        
        # 4. Commit the changes to the database
        db.session.commit()
        
        return jsonify({"message": "Project client updated successfully"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

# --- GET all projects for a specific company by company_id ---
@projects_bp.route('/companies/<string:company_id>/projects', methods=['GET'])
# @jwt_required_now
def get_projects_by_company(company_id):
    try:
        # 1. Query the Projects model, filtering by the provided company_id
        # We assume the 'Companies' model exists and the ID is valid for simplicity.
        projects = Projects.query.filter_by(company_id=company_id).all()

        if not projects:
            # You might return 404 if no projects are found for this ID, or 200 with an empty list
            # A 200 with an empty list is often preferred for collection endpoints.
            return jsonify({
                'company_id': company_id,
                'projects': [],
                'total_projects': 0,
                'message': 'No projects found for this company.'
            }), 200

        # 2. Serialize the projects
        result = []
        for project in projects:
            result.append({
                'project_id': project.project_id,
                'project_name': project.project_name,
                # Fetch related client's name (assuming the Client model is linked)
                'client_name': project.client.client_name if project.client else None,
                'location': project.location,
                'due_date': project.due_date.isoformat() if project.due_date else None,
                'status': project.status or 'Not Started',
                'updated_at': project.updated_at.isoformat() if project.updated_at else None,
                'company_id': project.company_id # Include the company_id for verification
            })

        # 3. Return the list of projects
        return jsonify({
            'company_id': company_id,
            'projects': result,
            'total_projects': len(result)
        }), 200

    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching projects by company ID: {e}") 
        return jsonify({"error": str(e)}), 500