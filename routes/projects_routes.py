from flask import Blueprint , jsonify , request
from models import  Projects, db
import datetime
import uuid
from datetime import datetime, date # Import date for correct data type


projects_bp = Blueprint('projects', __name__)

# --- GET all projects ---
@projects_bp.route('/projects', methods=['GET'])
def get_all_projects():
    try:
        
        # projects = Projects.query.all()
        # result = []
        # for project in projects:
        #     result.append({
        #         'project_id': project.project_id,
        #         'project_name': project.project_name,
        #         'project_description': project.project_description,
        #         'start_date': project.start_date.isoformat() if project.start_date else None,
        #         'end_date': project.end_date.isoformat() if project.end_date else None,
        #         'status': project.status,
        #         'budget': project.budget,
        #         'created_at': project.created_at.isoformat() if project.created_at else None,
        #         'client_id': project.client_id
        #     })
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Use SQLAlchemy's paginate() method to get a paginated result
        paginated_projects = Projects.query.paginate(page=page, per_page=per_page, error_out=False)

        result = []
        for project in paginated_projects.items:
            result.append({
                'project_id': project.project_id,
                'project_name': project.project_name,
                'project_description': project.project_description,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'due_date': project.due_date.isoformat() if project.due_date else None,
                'status': project.status,
                'budget': project.budget,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'client_id': project.client_id
            })
        return jsonify({
            'projects': result,
            'total_projects': paginated_projects.total,
            'current_page': paginated_projects.page,
            'pages': paginated_projects.pages
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# --- GET single project by id ---
@projects_bp.route('/projects/<string:project_id>', methods=['GET'])
def get_project_by_id(project_id):
    try:
        project = Projects.query.get_or_404(project_id)
        result = {
            'project_id': project.project_id,
            'project_name': project.project_name,
            'project_description': project.project_description,
            'start_date': project.start_date.isoformat() if project.start_date else None,
            'due_date': project.due_date.isoformat() if project.due_date else None,
            'status': project.status,
            'budget': project.budget,
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'client_id': project.client_id
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new project ---
@projects_bp.route('/projects', methods=['POST'])
def add_projects():
    data = request.json
    # The required_fields list has been updated to include 'client_id'
    required_fields = ['project_name', 'site_area', 'location', 'budget', 'start_date', 'due_date', 'status', 'project_description', 'client_id']
    
    # 1. Check if all required fields are present
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'All fields are required'}), 400
    
    try:
        # 2. Instantiate the Projects model with proper date conversion
        new_project = Projects(
            project_name=data['project_name'],
            site_area=data['site_area'],
            location=data['location'],
            budget=data['budget'],
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date(),
            status=data['status'],
            project_description=data['project_description'],
            client_id=data['client_id']
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
        
