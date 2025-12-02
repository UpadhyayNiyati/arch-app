from flask import Blueprint , jsonify , request , current_app
from models import Tasks , db , Vendors , Upload_Files , Clients, Projects , User
import datetime
from  .upload_files_routes import upload_task_files , update_task_files
import uuid
import logging
import json
from utils.email_utils import send_email
from flask_cors import CORS
from auth.auth import jwt_required
import datetime
import time
from datetime import datetime , timedelta , time
tasks_bp = Blueprint('tasks', __name__)
CORS(tasks_bp)

# Setup basic logging (Should typically be done in __init__.py or app.py)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 
def serialize_task(task):
    """
    Converts a Tasks object to a dictionary, resolving foreign keys to names
    and including associated file metadata.
    """
    
    # Resolve Assigned User Name
    assigned_user_name = None
    if task.assigned_to:
        user = User.query.get(task.assigned_to) 
        assigned_user_name = user.user_name if user and hasattr(user, 'user_name') else task.assigned_to 

    # Resolve Assigned Vendor Name
    assigned_vendor_name = None
    if getattr(task, 'assigned_vendor', None): # Use getattr for safety if column might be missing
        vendor = Vendors.query.get(task.assigned_vendor)
        assigned_vendor_name = vendor.vendor_name if vendor and hasattr(vendor, 'vendor_name') else task.assigned_vendor
        
    # Resolve Project Name
    project_name = task.project_id
    if task.project_id:
        project = Projects.query.get(task.project_id)
        project_name = project.project_name if project and hasattr(project, 'project_name') else task.project_id
        
    # Handle completion status field (if it exists)
    completed_at_iso = task.completed_at.isoformat() if getattr(task, 'completed_at', None) else None

    # Base Task Dictionary
    task_dict = {
        'task_id': task.task_id, 
        'project_id': project_name, 
        'task_name': task.task_name, 
        'description': task.description, 
        'assigned_to': assigned_user_name, 
        'status': task.status, 
        'task_type': task.task_type,
        # 'date': task.date.isoformat() if isinstance(task.date, datetime.date) else str(task.date),
        'date': task.date.isoformat() if task.date else None,
        'due_date': task.due_date.isoformat()  if task.due_date else None,
        'space_id': getattr(task, 'space_id', None),
        'assigned_vendor': assigned_vendor_name,
        'completed_at': completed_at_iso, # Added for completeness
        'files': []
    }
    
    # Get associated files (retained original logic)
    find_uploads = Upload_Files.query.filter_by(task_id=task.task_id).all()
    for file in find_uploads:
        file_dict = {
            'file_id': file.file_id, 
            'filename': file.filename, 
            'file_size': file.file_size, 
            'file_path': file.file_path
        }
        task_dict['files'].append(file_dict)
        
    return task_dict
#get all tasks
@tasks_bp.route('/tasks' , methods = ['GET'])
@jwt_required
def get_all_tasks():
    """
    Retrieves all tasks along with their associated file metadata.
    ---
    tags:
      - Tasks
    responses:
      200:
        description: A list of tasks retrieved successfully.
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  task_id: {type: string, description: Unique ID of the task}
                  project_id: {type: string}
                  task_name: {type: string}
                  description: {type: string}
                  status: {type: string, example: pending}
                  task_type: {type: string}
                  date: {type: string, format: date-time}
                  location: {type: string}
                  assigned_to: {type: string}
                  files:
                    type: array
                    items:
                      type: object
                      properties:
                        file_id: {type: string}
                        filename: {type: string}
                        file_size: {type: number}
                        file_path: {type: string}
      500:
        description: Internal server error.
    """

    try:
        tasks = Tasks.query.all()
        # Use the utility function to serialize all tasks consistently
        all_tasks = [serialize_task(task) for task in tasks] 
        return jsonify(all_tasks) , 200
    except Exception as e:
        logger.error(f"Error retrieving all tasks: {e}", exc_info=True)
        return jsonify({"error": str(e)}) , 500
    
    # try:
    #     all_tasks = []
    #     tasks = Tasks.query.all()
        
    #     for task in tasks:
    #         task_dict = ({
    #             'task_id' : task.task_id , 
    #             'project_id' : task.project_id , 
    #             'task_name' : task.task_name , 
    #             'description' : task.description , 
    #             'assigned_to' : task.assigned_user_name  , 
    #             # 'due_date' : task.due_date , 
    #             'status' : task.status , 
    #             # 'created_at' : task.created_at , 
    #             # 'updated_at' : task.updated_at ,
    #             # 'completed_at' : task.completed_at ,
    #             # 'priority' : task.priority ,
    #             # 'estimated_hours' : task.estimated_hours ,
    #             # 'actual_hours' : task.actual_hours ,
    #             # 'logged_hours' : task.logged_hours,
    #             # 'assigned_vendor':task.assigned_vendor,
    #             'location':task.location , 
    #             # 'assigned_team':task.assigned_team , 
    #             'task_type':task.task_type,
    #             'date':task.date,
    #             # 'sapce_id':task.space_id,
    #             # 'files':[]
    #         })
    #         find_uploads = db.session.query(Upload_Files).filter(Upload_Files == task.task_id).all()
    #         for file in find_uploads:
    #             file_dict = {
    #                 'file_id':file.file_id , 
    #                 'filename':file.filename , 
    #                 'file_size':file.files_size , 
    #                 'file_path' : file.file_path
    #             }
    #             task_dict['files'].append(file_dict)
    #         all_tasks.append(task_dict)

    #     return jsonify(all_tasks) , 200
    # except Exception as e:
    #     return jsonify({"error" : str(e)}) , 500
    
#get single task by id
@tasks_bp.route('/tasks/<string:task_id>' , methods = ['GET'])
@jwt_required
def get_task_by_id(task_id):
    """
    Retrieve a single task by its unique ID.
    ---
    tags:
      - Tasks
    parameters:
      - in: path
        name: task_id
        schema:
          type: string
        required: true
        description: The unique ID of the task to retrieve.
    responses:
      200:
        description: Task retrieved successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                task_id: {type: string}
                project_id: {type: string}
                task_name: {type: string}
                assigned_to: {type: string}
                # ... (other task fields)
                files:
                  type: array
                  items:
                    type: object
                    properties:
                      file_id: {type: string}
                      filename: {type: string}
                      file_path: {type: string}
                      file_size: {type: number}
      404:
        description: Task not found.
    """
    task = Tasks.query.filter_by(task_id = task_id).first_or_404(
        description = f'Task with ID {task_id} not found'
    )
    task_dict = serialize_task(task)
    return jsonify(task_dict) , 200
    
  


#Get tasks by project_id and space_id
@tasks_bp.route('/tasks/project/<string:project_id>' , methods = ['GET'])
@jwt_required
def get_tasks_by_project_id(project_id):
    """
    Retrieve all tasks associated with a specific project ID.
    ---
    tags:
      - Tasks
    parameters:
      - in: path
        name: project_id
        schema:
          type: string
        required: true
        description: The ID of the project whose tasks are to be retrieved.
    responses:
      200:
        description: List of tasks for the given project.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/TaskWithFiles' # Assuming you define this schema
      404:
        description: No tasks found for the project ID (though it returns 200/empty list in current code).
    """
    tasks = Tasks.query.filter_by(project_id = project_id).all()
    all_tasks = [serialize_task(task) for task in tasks]
    return jsonify(all_tasks) , 200


@tasks_bp.route('/tasks/space/<string:space_id>' , methods = ['GET'])
@jwt_required
def get_tasks_by_space_id(space_id):
    """
    Retrieve all tasks associated with a specific space ID.
    ---
    tags:
      - Tasks
    parameters:
      - in: path
        name: space_id
        schema:
          type: string
        required: true
        description: The ID of the space whose tasks are to be retrieved.
    responses:
      200:
        description: List of tasks for the given space.
      404:
        description: No tasks found for the space ID.
    """
    tasks = Tasks.query.filter_by(space_id = space_id).all()
    all_tasks = [serialize_task(task) for task in tasks]
    return jsonify(all_tasks) , 200

#post task

# Setup basic logging (You should configure this once in your app.py)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 
@tasks_bp.route('/tasks' , methods = ['POST'])
@jwt_required
def add_tasks():
    """
    Create a new task, optionally including file attachments.
    ---
    tags:
      - Tasks
    requestBody:
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              task_name: {type: string, description: Name of the task}
              description: {type: string}
              task_type: {type: string, enum: [general, maintenance, other]}
              project_id: {type: string, description: ID of the associated project}
              status: {type: string, default: pending}
              date: {type: string, format: date-time, description: Date of the task}
              location: {type: string}
              assigned_to: {type: string , description: Username or ID of the user to assign the task to}              
              uploads: {type: array, items: {type: string, format: binary}, description: List of files to upload}
            required:
              - task_name
              - description
              - task_type
              - project_id
    responses:
      201:
        description: Task created successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                message: {type: string}
                task_id: {type: string}
                file_location: {type: string}
                task_name: {type: string}
      400:
        description: Missing required field.
      404:
        description: Project not found.
      500:
        description: Internal server error.
    """
    data = request.form
    logger.info("Received POST request data: %s", data)
    required_fields = ['task_name', 'task_type']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f"'{field}' is required"}), 400
        
    task_date_str = data.get('date')
    task_date_to_save = None # Initialize to None

    task_date_str = data.get('date')
    task_date_to_save = None

    if task_date_str:
      try:
        # **Case 1: Full Date-Time** (If input is like: 2025-12-12T15:30:00)
        # We handle the 'T' and assume no timezone for simple cases
        if 'T' in task_date_str:
             # Strip off any timezone info (+HH:MM or Z) if not needed for the database
             if '+' in task_date_str:
                 task_date_str = task_date_str.split('+')[0]
             elif task_date_str.endswith('Z'):
                 task_date_str = task_date_str[:-1]

             task_date_to_save = datetime.strptime(task_date_str, '%Y-%m-%dT%H:%M:%S')

        # **Case 2: Date Only** (If input is like: 2025-12-12)
        else:
             task_date_to_save = datetime.strptime(task_date_str, '%Y-%m-%d')
            
      except ValueError as e:
        logger.error("Error parsing date '%s': %s", task_date_str, str(e))
        return jsonify({'error': "Invalid date format. Please use ISO 8601 format (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')."}), 400
            
    # Validate project exists
    assigned_user_id_to_save = None

    assigned_user_id = data.get('assigned_to')
    user = None
    if assigned_user_id: 
        # Note: Replace 'User' with your actual User model name if different
        user = User.query.filter_by(user_name=assigned_user_id).first()
        
        if not user and assigned_user_id.isalnum(): # Simple check if it looks like an ID/string without spaces
             user = User.query.get(assigned_user_id)
        if not user:
            return jsonify({
                'error': f"Assigned user ID '{assigned_user_id}' not found in the database. Please select a valid architect."
            }), 404
        
        assigned_user_id_to_save = user.user_id if user else None

    # project = Projects.query.get(data.get('project_id'))
    # if not project:
        # return jsonify({'error': f"Project with ID {data.get('project_id')} not found"}), 404
        
    # assigned_vendor = data.get('assigned_vendor')
    # assigned_team = data.get('assigned_team')

    # Condition: Must have AT LEAST ONE and NOT BOTH (Exclusive OR / XOR)
    # has_vendor = bool(assigned_vendor)
    # has_team = bool(assigned_team)
    
    # Check for XOR (Either one, but not both, is true)
    # if has_vendor == has_team: # This is true if (True and True) or (False and False)
        # if has_vendor and has_team:
            # return jsonify({'error': "Task cannot be assigned to both a vendor and a team. Choose one."}), 400
        # else:
            # return jsonify({'error': "Task must be assigned to either an 'assigned_vendor' or an 'assigned_team'."}), 400
        
    attachments = request.files.getlist("uploads")
    logger.info("Detected %d file attachment(s).", len(attachments))
    try:
        new_task = Tasks(
            project_id = data.get('project_id'),
            task_name = data.get('task_name'),
            description = data.get('description'),
            status = data.get('status', 'pending'),
            task_type = data.get('task_type'),
            date = task_date_to_save, 
            # task_date_to_save = None , 
            assigned_to = assigned_user_id_to_save,
            space_id = data.get('space_id'),
            location = data.get('location'),
            assigned_vendor = None,  # We'll handle assignment separately
            assigned_team = None     # We'll handle assignment separately
        )
        db.session.add(new_task)
        db.session.flush()
        logger.info("Task created successfully in session with ID: %s", new_task.task_id)
        upload_task_files(attachments , new_task.task_id)
        db.session.commit()
        return jsonify({'message':'Task added successfully',
                        'task_id':new_task.task_id , 
                        'file_location' : f"Processed {len(attachments)} file(s)",
                        'task_name':new_task.task_name ,
                        'task_type':new_task.task_type , 
                        'space_id':new_task.space_id , 
                        'location' : new_task.location , 
                        'status':new_task.status , 
                        'description':new_task.description,
                        'project_id':new_task.project_id , 
                        'date' : task_date_to_save,
                        }) , 201
    except Exception as e:
        db.session.rollback()
        logger.error("Error creating task: %s", str(e), exc_info=True) # Log the traceback
        return jsonify({"error" : str(e)}) , 500
    
  # The original imports and utility function resolve_assigned_to_id are assumed to be present above this block.

# --- Utility Function to Resolve Username to User ID (Re-displaying for context) ---

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Utility Function to Resolve Username/ID to User ID ---
def resolve_assigned_to_id(assigned_user_identifier):
    """
    Attempts to resolve an input string (either user_name or user_id) 
    to the internal User ID.
    Returns: user_id (string) or None
    Raises: ValueError if user is not found.
    """
    if not assigned_user_identifier:
        return None
        
    # 1. Try resolving by user_name
    # Assuming 'user_name' is the field for the display name/login name
    user = User.query.filter_by(user_name=assigned_user_identifier).first()
    
    # 2. Fallback: Try resolving by user_id
    if not user:
        # Simple check if the identifier looks like an ID (e.g., alphanumeric)
        # Assuming user_id is the primary key and accepts direct get
        if assigned_user_identifier.isalnum(): 
             user = User.query.get(assigned_user_identifier)
    
    if not user:
        raise ValueError(f"Assigned user identifier '{assigned_user_identifier}' not found.")
        
    return user.user_id

@tasks_bp.route('/tasks/<string:task_id>', methods=['PUT'])
@jwt_required
def update_task(task_id):
    """
    Update an existing task's metadata by its ID (using form-data) and handle files.
    Resolves 'assigned_to' (which can be user_name or user_id) to the internal user_id.
    ---
    tags:
      - Tasks
    responses:
      200:
        description: Task updated successfully.
      400:
        description: Invalid request format or JSON in files_to_delete.
      404:
        description: Task or assigned user/vendor not found.
      500:
        description: Internal server error.
    """
    if 'multipart/form-data' not in request.mimetype:
        return jsonify({'error': 'Request must be multipart/form-data.'}), 400

    data = request.form
    attachments = request.files.getlist("uploads")
    
    # Load files_to_delete list
    try:
        files_to_delete = json.loads(data.get("files_to_delete", "[]"))
        if not isinstance(files_to_delete, list):
             raise TypeError()
    except (json.JSONDecodeError, TypeError):
        return jsonify({'error': "Invalid JSON format for 'files_to_delete'. Must be a JSON array."}), 400

    task = Tasks.query.get_or_404(
        task_id, 
        description=f"Task with ID {task_id} not found"
    )

    fields_updated = False
    
    # --- 1. Define Fields to Update ---
    # Include 'assigned_vendor' which was missing from the PUT update logic
    updatable_fields = [
        'task_name', 'description', 'status', 'priority', 'due_date', 'location', 
        'estimated_hours', 'actual_hours', 'logged_hours', 'task_type', 
        'date', 'space_id', 'assigned_vendor' 
    ]
    
    # --- 2. Update Generic Fields (excluding 'assigned_to' and 'status' initial handling) ---
    for field in updatable_fields:
        if field in data:
            # Skip 'status' to handle it explicitly later for completed_at logic
            if field == 'status': 
                continue 
            
            # CRITICAL FIX: Set the attribute on the task object
            setattr(task, field, data[field])
            fields_updated = True

    # --- 3. Handle 'assigned_to' (Resolves identifier to ID) ---
    if 'assigned_to' in data:
        assigned_user_identifier = data['assigned_to']
        try:
            # Use the utility function to resolve identifier to the internal user_id
            assigned_user_id_to_save = resolve_assigned_to_id(assigned_user_identifier)
            task.assigned_to = assigned_user_id_to_save
            fields_updated = True
        except ValueError as e:
            # If the user is not found, return an error
            return jsonify({'error': str(e)}), 404
            
    # --- 4. Handle 'status' and 'completed_at' Timestamp Logic ---
    if 'status' in data:
        new_status = data['status']
        new_status_lower = new_status.lower()
        
        # 4a. Update the status field
        task.status = new_status 
        fields_updated = True
        
        # 4b. Update completed_at based on new status
        if hasattr(task, 'completed_at'):
            if new_status_lower == 'completed':
                # Set timestamp only if it wasn't already set (optional check)
                if task.completed_at is None:
                    task.completed_at = datetime.now()
            elif task.completed_at is not None:
                # Clear timestamp if status changes to non-completed
                task.completed_at = None

    try:
        # Check if any update action was requested
        if not fields_updated and not attachments and not files_to_delete:
            return jsonify({"message": "No valid fields, attachments, or files for deletion provided."}), 200

        # --- 5. Handle file changes (uploads and deletions) ---
        if attachments or files_to_delete:
            # Increment revision number (assuming it exists)
            task.revision_number = (getattr(task, 'revision_number', 0) or 0) + 1
            # NOTE: update_task_files must be imported and defined correctly
            update_task_files(attachments, task.task_id, files_to_delete)

        db.session.commit()

        # Re-fetch the assigned_user_name for the final response
        final_assigned_to_display = data.get('assigned_to') # Start with what user sent
        if task.assigned_to:
            user = User.query.get(task.assigned_to)
            # Use the actual user name if found, otherwise the ID saved to the DB
            final_assigned_to_display = getattr(user, 'user_name', task.assigned_to)
        
        return jsonify({
            "message": "Task updated successfully",
            "task_id": task.task_id,
            "assigned_to_user_name": final_assigned_to_display,
            "files_added": len(attachments),
            "files_deleted": len(files_to_delete)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Database error updating task {task_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------------------------------
# (The serialize_task function and all GET/POST/DELETE routes are omitted for brevity, 
# as the user requested changes only to the PUT/update route, but they remain intact)
# ----------------------------------------------------------------------------------

# Update task by id (Accepts user_name/user_id, saves user_id)
# @tasks_bp.route('/tasks/<string:task_id>', methods=['PUT'])
# def update_task(task_id):
#     """
#     Update an existing task's metadata by its ID (using form-data).
#     Resolves 'assigned_to' (which can be user_name or user_id) to the internal user_id.
#     """
#     assigned_user_name_for_response = None # Initialized here
#     fields_updated = False
#     if 'multipart/form-data' not in request.mimetype:
#         return jsonify({'error': 'Request must be multipart/form-data.'}), 400

#     data = request.form
#     attachments = request.files.getlist("uploads")
    
#     try:
#         # Load files_to_delete list
#         files_to_delete = json.loads(data.get("files_to_delete", "[]"))
#     except json.JSONDecodeError:
#         return jsonify({'error': "Invalid JSON format for 'files_to_delete'."}), 400

#     task = Tasks.query.get_or_404(
#         task_id, 
#         description=f"Task with ID {task_id} not found"
#     )

#     fields_updated = False
#     assigned_user_id_to_save = None

#     # --- EDITED LOGIC: Resolve assigned_to to ID and save the ID ---
#     if 'assigned_to' in data:
#         assigned_user_identifier = data['assigned_to']
#         try:
#             # Use the utility function to resolve identifier to the internal user_id
#             assigned_user_id_to_save = resolve_assigned_to_id(assigned_user_identifier)
#             task.assigned_to = assigned_user_id_to_save
#             fields_updated = True
#         except ValueError as e:
#             # If the user is not found, return an error
#             return jsonify({'error': str(e)}), 404
#         # Handle status change for completion timestamp
#         if 'status' in data:
#             if data['status'].lower() == 'completed':
#                  task.completed_at = datetime.datetime.now()
#             elif task.completed_at is not None:
#                  task.completed_at = None
                 
#     # Generic update fields (excluding 'assigned_to' which is handled above)
#     updatable_fields = [
#         'task_name', 'description', 'status', 'priority', 'due_date', 'location', 
#         'estimated_hours', 'actual_hours', 'logged_hours' ,'task_type' , 'date' # Added missing fields
#     ]
    
#     for field in updatable_fields:
#         if field in data and field != 'assigned_to':
#             fields_updated = True # Ensure we don't overwrite assigned_to if set above
#             if 'status' in data:
                
#               new_status = data['status']
#               task.status = new_status  # 👈 THIS IS THE LINE THAT UPDATES THE STATUS
#               new_status_lower = new_status.lower()
#               fields_updated = True
        
#         # Check if the model has the 'completed_at' column before trying to use it
#               if hasattr(task, 'completed_at'):
#                 if new_status_lower == 'completed':
#                 # Set timestamp when completing
#                   if task.completed_at is None:
#                     task.completed_at = datetime.datetime.now()
#                   else:

#                 # Clear timestamp if status changes to non-completed
#                     if task.completed_at is not None:
#                       task.completed_at = None
#                 else:
#             # If the column is missing, the status field still updated successfully above
#                   logger.warning(f"Tasks model is missing 'completed_at' column for task {task_id}.")
#             # if field == 'status':
#             #     task.status = data['status']
#             #     if data['status'].lower() == 'completed':
#             #         task.completed_at = datetime.datetime.now()
#             #     elif task.completed_at is not None:
#             #         task.completed_at = None
            
#             fields_updated = True

#     try:
#         # Check if any update action was requested
#         if not fields_updated and not attachments and not files_to_delete:
#             return jsonify({"message": "No valid fields, attachments, or files for deletion provided."}), 200

#         # Handle file changes (uploads and deletions)
#         if attachments or files_to_delete:
#             # Assumes 'revision_number' is an existing field on Tasks
#             task.revision_number = (getattr(task, 'revision_number', 0) or 0) + 1
#             # NOTE: update_task_files must be imported and defined correctly
#             update_task_files(attachments, task.task_id, files_to_delete)

#         db.session.commit()

#         if assigned_user_name_for_response is None and task.assigned_to:
#             # If 'assigned_to' was not in data, but the task already has one (or was set via a bulk update),
#             # fetch the name to include in the final response.
#             user = User.query.get(task.assigned_to)
#             assigned_user_name_for_response = user.user_name if user else task.assigned_to

#         # Re-fetch the assigned_user_name for the response using serialize_task logic (or do it here)
#         # assigned_user_for_response = data.get('assigned_to') # Use the identifier from the request as a fallback/confirmation
#         final_assigned_to_display = assigned_user_name_for_response if assigned_user_name_for_response is not None else task.assigned_to
#         return jsonify({
#             "message": "Task updated successfully",
#             "task_id": task.task_id,
#             # If a new ID was saved, fetch the name to confirm, or return the ID. 
#             # For simplicity, returning the ID saved to the DB:
#             "assigned_to_user_name": final_assigned_to_display,
#         }), 200

#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Database error updating task {task_id}: {e}", exc_info=True)
#         return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------------------------------

# The original imports, utility functions (which are now ignored for 'assigned_to'), 
# and Tasks, db, update_task_files models are assumed to be imported.


    # 3. Handle 'assigned_to': Resolve name/ID to user_id and save the ID

      
    # 5. Handle File Changes
  
    # is_multipart = request.mimetype and 'multipart/form-data' in request.mimetype
    # attachments = []
    # files_to_delete = []
    # data = []

    # assigned_user_id = data.get('assigned_to')
    # user = None
    # if assigned_user_id: 
    #     # Note: Replace 'User' with your actual User model name if different
    #     user = User.query.filter_by(user_name=assigned_user_id).first()
        
        
        
    #     if not user and assigned_user_id.isalnum(): # Simple check if it looks like an ID/string without spaces
    #          user = User.query.get(assigned_user_id)
    #     if not user:
    #         return jsonify({
    #             'error': f"Assigned user ID '{assigned_user_id}' not found in the database. Please select a valid architect."
    #         }), 404
        
    #     assigned_user_id_to_save = user.user_id if user else None

    # if not is_multipart:
    #     return jsonify({'error': 'Request must be multipart/form-data'}), 400
    
    # data = request.form
    # attachments = request.files.getlist("uploads")
    # files_to_delete_json = data.get('files_to_delete', '[]')
    # try:
    #     files_to_delete = json.loads(files_to_delete_json)
    #     if not isinstance(files_to_delete, list):
    #         raise TypeError()
    # except (json.JSONDecodeError, TypeError):
    #     return jsonify({'error': "'files_to_delete' must be a JSON array of file IDs"}), 400  
    # task = Tasks.query.get_or_404(task_id)

    
    # if not task:
    #     return jsonify({"message":"Task not found"}) , 404
    # fields_updated = True
    # files_changed = attachments or files_to_delete
    # # if 'project_id' in data:
    # #     task.project_id = data['project_id']
    # if 'task_name' in data:
    #     task.task_name = data['task_name']
    # if 'description' in data:
    #     task.description = data['description']
    # if 'assigned_to' in data:
    #     task.assigned_to = data['assigned_user_id_to_save']
    # if 'due_date' in data:
    #     task.due_date = data['due_date']
    # if 'status' in data:
    #     task.status = data['status']
    # if 'completed_at' in data:
    #     task.completed_at = data['completed_at']
    # if 'priority' in data:
    #     task.priority = data['priority']
    # if 'estimated_hours' in data:
    #     task.estimated_hours = data['estimated_hours']
    # if 'actual_hours' in data:
    #     task.actual_hours = data['actual_hours']
    # if 'logged_hours' in data:
    #     task.logged_hours = data['logged_hours']
    # if 'location 'in data:
    #     task.location = data['location']
    # if 'date' in data:
    #     task.date = data['date']
    
    # try:
    #     if not fields_updated and files_changed:
    #         return jsonify({"message": "No valid metadata fields or files provided for update."}), 200
        
    #     if files_changed:
    #         task.revision_number = (task.revision_number or 0) + 1

    #         update_task_files(attachments , task.task_id , files_to_delete)

        
    #     db.session.commit()
    #     message = "Tasks Updated Successfully"
    #     if fields_updated and files_changed:
    #         message = "Task metadata and files updated successfully."
    #     elif fields_updated:
    #         message = "Task metadata updated successfully."
    #     return jsonify({
    #         "message":message , 
    #         "task_id":task.task_id , 
    #         "task_name":task.task_name,
    #         "location":task.location ,
    #         "date":task.date ,
    #         "description":task.description ,
    #         "assigned_to":task.assigned_to ,
    #         # "new_revision":task.revision_number , 
    #         "files_added": len(attachments) ,
    #         "files_deleted": len(files_to_delete)
    #     }) , 200
    # except Exception as e:
    #     return jsonify({"error" : str(e)}) , 500

# Update task by id (Accepts user_name/user_id, saves user_id)
# @tasks_bp.route('/tasks/<string:task_id>', methods=['PUT'])
# def update_task(task_id):
#     """
#     Update an existing task's metadata by its ID (using form-data).
#     Resolves 'assigned_to' (which can be user_name or user_id) to the internal user_id.
#     """
#     if 'multipart/form-data' not in request.mimetype:
#         return jsonify({'error': 'Request must be multipart/form-data.'}), 400

#     data = request.form
#     attachments = request.files.getlist("uploads")
    
#     try:
#         # Load files_to_delete list
#         files_to_delete = json.loads(data.get("files_to_delete", "[]"))
#     except json.JSONDecodeError:
#         return jsonify({'error': "Invalid JSON format for 'files_to_delete'."}), 400

#     task = Tasks.query.get_or_404(
#         task_id, 
#         description=f"Task with ID {task_id} not found"
#     )

#     fields_updated = False
#     assigned_user_name_for_response = None
    
#     # --- 1. Resolve and Update 'assigned_to' ---
#     if 'assigned_to' in data:
#         assigned_user_identifier = data['assigned_to']
#         try:
#             assigned_user_id_to_save = resolve_assigned_to_id(assigned_user_identifier)
#             task.assigned_to = assigned_user_id_to_save
#             fields_updated = True
#         except ValueError as e:
#             return jsonify({'error': str(e)}), 404
    
#     # --- 2. Generic Update Fields & Status Handling ---
#     updatable_fields = [
#         'task_name', 'description', 'priority', 'due_date', 'location', 
#         'estimated_hours', 'actual_hours', 'logged_hours', 'task_type', 'date', 'space_id',
#         'assigned_vendor' # Include all fields that can be updated via the PUT request
#     ]
    
#     for field in updatable_fields:
#         if field in data:
#             # **********************************************
#             # 💡 CRITICAL FIX: Set the attribute for the field
#             # **********************************************
#             setattr(task, field, data[field])
#             fields_updated = True
#             db.session.flush()  # Ensure changes are staged
#             db.session.refresh(task)  # Refresh to get latest state from DB
            
            
#     # --- 3. Status and completed_at Handling (Separate for Clarity) ---
#     if 'status' in data:
#         new_status = data['status'].lower()
        
#         # Check if the status is changing to 'completed'
#         if new_status == 'completed' and (not hasattr(task, 'completed_at') or task.completed_at is None):
#             # Set timestamp only if it wasn't already set
#             task.completed_at = datetime.datetime.now()
#             fields_updated = True
            
#         # Check if the status is changing away from 'completed'
#         elif new_status != 'completed' and hasattr(task, 'completed_at') and task.completed_at is not None:
#             # Clear timestamp
#             task.completed_at = None
#             fields_updated = True
            
#         # The status itself was already updated in the loop above: `task.status = data['status']`

#     try:
#         # Check if any update action was requested
#         if not fields_updated and not attachments and not files_to_delete:
#             return jsonify({"message": "No valid fields, attachments, or files for deletion provided."}), 200

#         # Handle file changes (uploads and deletions)
#         if attachments or files_to_delete:
#             task.revision_number = (getattr(task, 'revision_number', 0) or 0) + 1
#             # NOTE: update_task_files must be imported and defined correctly
#             update_task_files(attachments, task.task_id, files_to_delete)

#         db.session.commit()

#         # Prepare final response display name
#         if task.assigned_to:
#             user = User.query.get(task.assigned_to)
#             assigned_user_name_for_response = getattr(user, 'user_name', task.assigned_to)
        
#         return jsonify({
#             "message": "Task updated successfully",
#             "task_id": task.task_id,
#             "assigned_to_user_name": assigned_user_name_for_response,
#             "files_added": len(attachments),
#             "files_deleted": len(files_to_delete)
#         }), 200

#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Database error updating task {task_id}: {e}", exc_info=True)
#         return jsonify({"error": str(e)}), 500

@tasks_bp.route('/tasks/project/<string:project_id>' , methods = ['PUT'])
@jwt_required
def update_tasks_by_project_id(project_id):
    """
    Updates metadata for ALL tasks within a project_id. Optionally uploads files to a 
    specific task within the project if 'task_id' is provided in the form data.
    """
    data = request.form
    attachments = request.files.getlist("uploads")
    specific_task_id = data.get('task_id')
    
    updatable_fields = [
        'task_name', 'description', 'assigned_to', 'due_date', 'status',
        'priority', 'estimated_hours', 'actual_hours', 'logged_hours' , 'task_type' , 'date'
    ]

    try:
        assigned_user_id_to_save = None
        # 1. Resolve 'assigned_to' identifier to ID once, if present
        if 'assigned_to' in data:
            try:
                assigned_user_id_to_save = resolve_assigned_to_id(data['assigned_to'])
            except ValueError as e:
                 return jsonify({'error': str(e)}), 404

        # 2. Query all tasks for the project ID
        tasks = Tasks.query.filter_by(project_id=project_id).all()
        
        if not tasks:
            return jsonify({"message": f"No tasks found for Project ID '{project_id}'"}), 404

        fields_updated_count = 0
        tasks_updated_count = 0
        
        # 3. Loop through tasks and apply bulk metadata updates
        for task in tasks:
            update_applied_to_task = False
            
            for field in updatable_fields:
                if field in data:
                    if field == 'assigned_to':
                        # Use the pre-resolved ID for the bulk update
                        setattr(task, field, assigned_user_id_to_save) 
                    elif field == 'status':
                        task.status = data['status']
                        # Handle completion timestamp for bulk status updates
                        if data['status'].lower() == 'completed':
                            task.completed_at = datetime.now()
                        elif task.completed_at is not None:
                            task.completed_at = None
                    else:
                        setattr(task, field, data[field])
                        
                    fields_updated_count += 1
                    update_applied_to_task = True
            
            if update_applied_to_task:
                tasks_updated_count += 1
                
        # 4. Handle File Uploads (If a specific task ID is provided)
        files_uploaded_count = 0
        if specific_task_id and attachments:
            target_task = next((t for t in tasks if str(t.task_id) == specific_task_id), None)
            
            if target_task:
                # 🚨 Use the imported utility function 'upload_task_files'
                upload_task_files(attachments, target_task.task_id) 
                files_uploaded_count = len([f for f in attachments if f.filename])
            else:
                 return jsonify({"error": f"Task ID '{specific_task_id}' not found within Project ID '{project_id}'."}), 404
        
        if fields_updated_count == 0 and files_uploaded_count == 0:
            return jsonify({"message": "No valid fields or files provided for update."}), 200

        db.session.commit()
        
        message = f'Successfully updated metadata for {tasks_updated_count} tasks for Project ID {project_id}.'
        if files_uploaded_count > 0:
             message += f' {files_uploaded_count} file(s) uploaded to task {specific_task_id}.'
             
        return jsonify({'message': message, 'tasks_updated': tasks_updated_count}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected Error updating tasks for project {project_id}: {e}", exc_info=True) 
        return jsonify({"error" : "An unexpected server or database error occurred during the update."}), 500

@tasks_bp.route('/tasks/space/<string:space_id>' , methods = ['PUT'])
@jwt_required
def update_tasks_by_space_id(space_id):
    """
    Updates metadata for ALL tasks within a space_id. Optionally uploads files to a 
    specific task within the space if 'task_id' is provided in the form data.
    """
    data = request.form
    attachments = request.files.getlist("uploads")
    specific_task_id = data.get('task_id')
    
    updatable_fields = [
        'task_name', 'description', 'assigned_to', 'due_date', 'status',
        'priority', 'estimated_hours', 'actual_hours', 'logged_hours' , 'task_type' , 'date'
    ]

    try:
        assigned_user_id_to_save = None
        # 1. Resolve 'assigned_to' identifier to ID once, if present
        if 'assigned_to' in data:
            try:
                assigned_user_id_to_save = resolve_assigned_to_id(data['assigned_to'])
            except ValueError as e:
                 return jsonify({'error': str(e)}), 404

        # 2. Query all tasks for the space ID
        # 🚨 KEY DIFFERENCE: Filter by space_id
        tasks = Tasks.query.filter_by(space_id=space_id).all()
        
        if not tasks:
            return jsonify({"message": f"No tasks found for Space ID '{space_id}'"}), 404

        fields_updated_count = 0
        tasks_updated_count = 0
        
        # 3. Loop through tasks and apply bulk metadata updates
        for task in tasks:
            update_applied_to_task = False
            
            for field in updatable_fields:
                if field in data:
                    if field == 'assigned_to':
                        # Use the pre-resolved ID for the bulk update
                        setattr(task, field, assigned_user_id_to_save) 
                    elif field == 'status':
                        task.status = data['status']
                        # Handle completion timestamp for bulk status updates
                        if data['status'].lower() == 'completed':
                            task.completed_at = datetime.now()
                        elif task.completed_at is not None:
                            task.completed_at = None
                    else:
                        setattr(task, field, data[field])
                        
                    fields_updated_count += 1
                    update_applied_to_task = True
            
            if update_applied_to_task:
                tasks_updated_count += 1
                
        # 4. Handle File Uploads (If a specific task ID is provided)
        files_uploaded_count = 0
        if specific_task_id and attachments:
            target_task = next((t for t in tasks if str(t.task_id) == specific_task_id), None)
            
            if target_task:
                # 🚨 Use the imported utility function 'upload_task_files'
                upload_task_files(attachments, target_task.task_id) 
                files_uploaded_count = len([f for f in attachments if f.filename])
            else:
                 return jsonify({"error": f"Task ID '{specific_task_id}' not found within Space ID '{space_id}'."}), 404
        
        if fields_updated_count == 0 and files_uploaded_count == 0:
            return jsonify({"message": "No valid fields or files provided for update."}), 200

        db.session.commit()
        
        message = f'Successfully updated metadata for {tasks_updated_count} tasks for Space ID {space_id}.'
        if files_uploaded_count > 0:
             message += f' {files_uploaded_count} file(s) uploaded to task {specific_task_id}.'
             
        return jsonify({'message': message, 'tasks_updated': tasks_updated_count}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected Error updating tasks for space {space_id}: {e}", exc_info=True) 
        return jsonify({"error" : "An unexpected server or database error occurred during the update."}), 500    
# @tasks_bp.route('/tasks/project/<string:project_id>' , methods = ['PUT'])
# def update_tasks_by_project_id(project_id):
#     """
#     Updates metadata for ALL tasks within a project_id via form-data.
#     If 'task_id' is provided in the form, files are uploaded and associated 
#     with that single specific task.
#     """
#     """
#     Updates metadata for ALL tasks within a project_id and optionally uploads files to a single task via form-data.
#     ---
#     tags:
#       - Tasks
#     parameters:
#       - in: path
#         name: project_id
#         schema:
#           type: string
#         required: true
#         description: The ID of the project whose tasks are to be updated.
#     requestBody:
#       content:
#         multipart/form-data:
#           schema:
#             type: object
#             properties:
#               task_name: {type: string, description: New name for all tasks (optional)}
#               description: {type: string, description: New description for all tasks (optional)}
#               status: {type: string, description: New status for all tasks (optional)}
#               task_id: {type: string, description: Required ONLY if uploading files. Specifies the task to attach files to.}
#               uploads: {type: array, items: {type: string, format: binary}, description: Files to upload to the specified task_id.}
#     responses:
#       200:
#         description: Tasks and/or files updated successfully.
#       404:
#         description: No tasks found for the project ID, or the specific task_id for upload not found within the project.
#       500:
#         description: Internal server error.
#     """
#     """
#     Updates metadata for ALL tasks within a project_id. Resolves 'assigned_to' if provided.
#     """
#     data = request.form
#     attachments = request.files.getlist("uploads")
#     specific_task_id = data.get('task_id')
    
#     updatable_fields = [
#         'task_name', 'description', 'assigned_to', 'due_date', 'status',
#         'completed_at', 'priority', 'estimated_hours', 'actual_hours', 
#         'logged_hours'
#     ]

#     try:
#         # 1. Resolve 'assigned_to' identifier to ID once, if present
#         assigned_user_id_to_save = None
#         if 'assigned_to' in data:
#             try:
#                 assigned_user_id_to_save = resolve_assigned_to_id(data['assigned_to'])
#             except ValueError as e:
#                  return jsonify({'error': str(e)}), 404

#         # 2. Query all tasks for the project ID
#         tasks = Tasks.query.filter_by(project_id = project_id).all()
        
#         if not tasks:
#             return jsonify({"message": f"No tasks found for Project ID '{project_id}'"}), 404

#         fields_updated_count = 0
#         tasks_updated_count = 0
        
#         # 3. Loop through tasks and apply bulk metadata updates
#         for task in tasks:
#             update_applied_to_task = False
            
#             for field in updatable_fields:
#                 if field in data:
#                     if field == 'assigned_to':
#                          # Use the pre-resolved ID for the bulk update
#                         setattr(task, field, assigned_user_id_to_save) 
#                     else:
#                         setattr(task, field, data[field])
                        
#                     fields_updated_count += 1
#                     update_applied_to_task = True
            
#             if update_applied_to_task:
#                 tasks_updated_count += 1
                
#         # 4. Handle File Uploads (If a specific task ID is provided)
#         # File logic remains unchanged.
#         files_uploaded_count = 0
#         if specific_task_id and attachments:
#             target_task = next((t for t in tasks if str(t.task_id) == specific_task_id), None)
            
#             if target_task:
#                 # TODO: Implement upload_task_files here or use a dedicated utility
#                 # upload_task_files(attachments, target_task.task_id) 
#                 files_uploaded_count = len([f for f in attachments if f.filename])
#             else:
#                  return jsonify({"error": f"Task ID '{specific_task_id}' not found within Project ID '{project_id}'."}), 404
        
#         if fields_updated_count == 0 and files_uploaded_count == 0:
#             return jsonify({"message": "No valid fields or files provided for update."}), 200

#         db.session.commit()
        
#         message = f'Successfully updated metadata for {tasks_updated_count} tasks for Project ID {project_id}.'
#         if files_uploaded_count > 0:
#              message += f' {files_uploaded_count} file(s) uploaded to task {specific_task_id}.'
             
#         return jsonify({'message': message,'tasks_updated': tasks_updated_count}), 200

#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Unexpected Error updating tasks for project {project_id}: {e}", exc_info=True) 
#         return jsonify({"error" : "An unexpected server or database error occurred during the update."}), 500
#     # 🚨 KEY CHANGE: Use request.form for metadata and request.files for files
# #     data = request.form
# #     attachments = request.files.getlist("uploads")
    
# #     # Optional: Get a single task_id if files are being uploaded for a specific task
# #     specific_task_id = data.get('task_id')
    
# #     # Define updatable fields
# #     updatable_fields = [
# #         'task_name', 'description', 'assigned_to', 'due_date', 'status',
# #         'completed_at', 'priority', 'estimated_hours', 'actual_hours', 
# #         'logged_hours'
# #     ]

# #     try:
# #         # 1. Query all tasks for the project ID
# #         tasks = Tasks.query.filter_by(project_id = project_id).all()
        
# #         if not tasks:
# #             return jsonify({"message": f"No tasks found for Project ID '{project_id}'"}), 404

# #         fields_updated_count = 0
# #         tasks_updated_count = 0
        
# #         # 2. Loop through tasks and apply bulk metadata updates
# #         for task in tasks:
# #             update_applied_to_task = False
            
# #             for field in updatable_fields:
# #                 if field in data:
# #                     setattr(task, field, data[field])
# #                     fields_updated_count += 1
# #                     update_applied_to_task = True
            
# #             if update_applied_to_task:
# #                 tasks_updated_count += 1
                
# #         # 3. Handle File Uploads (If a specific task ID is provided)
# #         files_uploaded_count = 0
# #         if specific_task_id and attachments:
# #             # Find the specific task object within the retrieved list
# #             target_task = next((t for t in tasks if str(t.task_id) == specific_task_id), None)
            
# #             if target_task:
# #                 # 🚨 Utility Function Call: Must be defined and imported elsewhere
# #                 # This function must handle saving the files and creating Upload_Files records.
# #                 # upload_task_files(attachments, target_task.task_id) 
                
# #                 files_uploaded_count = len([f for f in attachments if f.filename])
# #             else:
# #                  # The task_id provided for file upload doesn't exist in this project
# #                  return jsonify({"error": f"Task ID '{specific_task_id}' not found within Project ID '{project_id}'."}), 404
        
# #         # 4. Check if any action was requested
# #         if fields_updated_count == 0 and files_uploaded_count == 0:
# #             return jsonify({"message": "No valid fields or files provided for update."}), 200

# #         # 5. Commit changes
# #         db.session.commit()
        
# #         # 6. Prepare success message
# #         message = f'Successfully updated metadata for {tasks_updated_count} tasks for Project ID {project_id}.'
# #         if files_uploaded_count > 0:
# #              message += f' {files_uploaded_count} file(s) uploaded to task {specific_task_id}.'
             
# #         return jsonify({
# #             'message': message,
# #             'tasks_updated': tasks_updated_count
# #         }), 200

# #     except Exception as e:
# #         # This structure simplifies the two except blocks into one robust block
# #         db.session.rollback()
# #         # Logging the error for debugging purposes (assuming current_app.logger is set up)
# #         # current_app.logger.error(f"Unexpected Error updating tasks for project {project_id}: {e}", exc_info=True) 
# #         return jsonify({"error" : "An unexpected server or database error occurred during the update."}), 500

# @tasks_bp.route('/tasks/space/<string:space_id>' , methods = ['PUT'])
# def update_tasks_by_space_id(space_id):
#     """
#     Updates metadata for ALL tasks within a space_id. Resolves 'assigned_to' if provided.
#     """
#     data = request.form
#     attachments = request.files.getlist("uploads")
#     specific_task_id = data.get('task_id')
    
#     try:
#         # 1. Resolve 'assigned_to' identifier to ID once, if present
#         assigned_user_id_to_save = None
#         if 'assigned_to' in data:
#             try:
#                 assigned_user_id_to_save = resolve_assigned_to_id(data['assigned_to'])
#             except ValueError as e:
#                  return jsonify({'error': str(e)}), 404

#         # 2. Retrieve all tasks by space_id
#         tasks = Tasks.query.filter_by(space_id = space_id).all()
        
#         if not tasks:
#             return jsonify({"message":"No tasks found for the given space ID"}) , 404

#         tasks_updated = 0
        
#         # 3. Bulk Update Metadata for ALL Tasks in the Space
#         updatable_fields = [
#             'task_name', 'description', 'assigned_to', 'due_date', 'status', 
#             'completed_at', 'priority', 'estimated_hours', 'actual_hours', 
#             'logged_hours', 'location'
#         ]
        
#         for task in tasks:
#             update_applied = False
            
#             for field in updatable_fields:
#                 if field in data:
#                     if field == 'assigned_to':
#                         setattr(task, field, assigned_user_id_to_save)
#                     else:
#                         setattr(task, field, data[field])

#                     update_applied = True
            
#             if update_applied:
#                 tasks_updated += 1
                
#         # 4. Handle File Uploads (Only if a specific task ID is provided)
#         # File logic remains unchanged.
#         files_uploaded_count = 0
#         if specific_task_id and attachments:
#             target_task = next((t for t in tasks if str(t.task_id) == specific_task_id), None)
            
#             if target_task:
#                 # TODO: Implement upload_task_files here or use a dedicated utility
#                 # upload_task_files(attachments, target_task.task_id) 
#                 files_uploaded_count = len([f for f in attachments if f.filename])
        
#         if tasks_updated == 0 and files_uploaded_count == 0:
#              return jsonify({"message": "No valid metadata fields or files provided for update."}), 200

#         db.session.commit()
        
#         message = f'Tasks updated successfully ({tasks_updated} tasks metadata changed).'
#         if files_uploaded_count > 0:
#              message += f' {files_uploaded_count} file(s) uploaded to task {specific_task_id}.'
             
#         return jsonify({'message': message}) , 200
        
#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error updating tasks in space {space_id}: {e}", exc_info=True)
#         return jsonify({"error" : str(e)}) , 500
   
#     """
#     Updates metadata for ALL tasks within a space_id and optionally uploads files to a single task via form-data.
#     ---
#     tags:
#       - Tasks
#     parameters:
#       - in: path
#         name: space_id
#         schema:
#           type: string
#         required: true
#         description: The ID of the space whose tasks are to be updated.
#     requestBody:
#       content:
#         multipart/form-data:
#           schema:
#             type: object
#             properties:
#               status: {type: string, description: New status for all tasks (optional)}
#               task_id: {type: string, description: Required ONLY if uploading files. Specifies the task to attach files to.}
#               uploads: {type: array, items: {type: string, format: binary}, description: Files to upload to the specified task_id.}
#               # ... (include other updatable fields)
#     responses:
#       200:
#         description: Tasks and/or files updated successfully.
#       404:
#         description: No tasks found for the space ID, or the specific task_id for upload not found within the space.
#       500:
#         description: Internal server error.
#     """
#     # 🚨 KEY CHANGE: Use request.form for metadata and request.files for files
#     data = request.form
#     attachments = request.files.getlist("uploads")
    
#     # Optional: Get a single task_id if files are being uploaded for a specific task
#     specific_task_id = data.get('task_id')
    
#     try:
#         # 1. Retrieve all tasks by space_id
#         tasks = Tasks.query.filter_by(space_id = space_id).all()
        
#         if not tasks:
#             return jsonify({"message":"No tasks found for the given space ID"}) , 404

#         tasks_updated = 0
        
#         # 2. Bulk Update Metadata for ALL Tasks in the Space
#         for task in tasks:
#             update_applied = False
            
#             # Use 'data' (from request.form) to update fields
#             if 'task_name' in data:
#                 task.task_name = data['task_name']
#                 update_applied = True
#             if 'description' in data:
#                 task.description = data['description']
#                 update_applied = True
#             if 'assigned_to' in data:
#                 task.assigned_to = data['assigned_to']
#                 update_applied = True
#             if 'due_date' in data:
#                 task.due_date = data['due_date']
#                 update_applied = True
#             if 'status' in data:
#                 task.status = data['status']
#                 update_applied = True
#             if 'complete
# d_at' in data:
#                 task.completed_at = data['completed_at']
#                 update_applied = True
#             if 'priority' in data:
#                 task.priority = data['priority']
#                 update_applied = True
#             if 'estimated_hours' in data:
#                 task.estimated_hours = data['estimated_hours']
#                 update_applied = True
#             if 'actual_hours' in data:
#                 task.actual_hours = data['actual_hours']
#                 update_applied = True
#             if 'logged_hours' in data:
#                 task.logged_hours = data['logged_hours']
#                 update_applied = True
#             if 'loaction' in data:
#                 task.location = data['location']
#                 update_applied = True
            
#             if update_applied:
#                 tasks_updated += 1
                
#         # 3. Handle File Uploads (Only if a specific task ID is provided)
#         files_uploaded_count = 0
#         if specific_task_id and attachments:
#             target_task = next((t for t in tasks if str(t.task_id) == specific_task_id), None)
            
#             if target_task:
#                 # 🚨 Call your utility function (must be defined elsewhere)
#                 # This function should save the files and create Upload_Files records.
#                 # upload_task_files(attachments, target_task.task_id) 
                
#                 files_uploaded_count = len([f for f in attachments if f.filename])
                
        
#         if tasks_updated == 0 and files_uploaded_count == 0:
#              return jsonify({"message": "No valid metadata fields or files provided for update."}), 200

#         # 4. Commit all changes (metadata and file record creations)
#         db.session.commit()
        
#         message = f'Tasks updated successfully ({tasks_updated} tasks metadata changed).'
#         if files_uploaded_count > 0:
#              message += f' {files_uploaded_count} file(s) uploaded to task {specific_task_id}.'
             
#         return jsonify({'message': message}) , 200
        
#     except Exception as e:
#         db.session.rollback()
#         # You should use current_app.logger.error here, not just return the string
#         # current_app.logger.error(f"Error updating tasks in space {space_id}: {e}", exc_info=True)
#         return jsonify({"error" : str(e)}) , 500

#delete task by id
@tasks_bp.route('/tasks/<string:task_id>' , methods = ['DELETE'])
@jwt_required
def delete_task(task_id):
    """
    Deletes a single task by its unique ID.
    ---
    tags:
      - Tasks
    parameters:
      - in: path
        name: task_id
        schema:
          type: string
        required: true
        description: The unique ID of the task to delete.
    responses:
      200:
        description: Task deleted successfully.
      404:
        description: Task not found.
      500:
        description: Internal server error.
    """
    task = Tasks.query.get_or_404(task_id)
    if not task:
        return jsonify({"message":"Task not found"}) , 404
    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({"message":"Task deleted successfully"}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
@tasks_bp.route('/tasks/project/<string:project_id>' , methods = ['DELETE'])
@jwt_required
def delete_tasks_by_project_id(project_id):
    
    """
    Deletes all tasks and their associated file records belonging to the given project_id.
    ---
    tags:
      - Tasks
    parameters:
      - in: path
        name: project_id
        schema:
          type: string
        required: true
        description: The ID of the project whose tasks are to be deleted.
    responses:
      200:
        description: Tasks and file records deleted successfully.
      404:
        description: No tasks found for the project ID.
      500:
        description: Database error during deletion.
    """
    try:
        # 1. Retrieve all tasks for the project
        tasks = Tasks.query.filter_by(project_id=project_id).all()
        
        if not tasks:
            return jsonify({"message": f"No tasks found for Project ID '{project_id}'"}), 404

        tasks_deleted_count = 0
        files_deleted_count = 0
        
        # 2. Loop through all tasks and their associated files for staged deletion
        for task in tasks:
            # 2a. Delete associated file records (Upload_Files) first
            # NOTE: Include physical file deletion logic here if necessary
            uploads = Upload_Files.query.filter_by(task_id=task.task_id).all()
            for upload in uploads:
                db.session.delete(upload)
                files_deleted_count += 1
            
            # 2b. Delete the main Task record
            db.session.delete(task)
            tasks_deleted_count += 1
            
        # 3. Commit all staged deletions in one transaction
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully deleted {tasks_deleted_count} task(s) and {files_deleted_count} associated file record(s) from project {project_id}.",
            "tasks_deleted": tasks_deleted_count,
            "files_records_deleted": files_deleted_count
        }), 200
        
    except Exception as e:
        # 4. Handle errors (e.g., database integrity errors)
        db.session.rollback()
        # Log the error for debugging
        # current_app.logger.error(f"Error deleting tasks in project {project_id}: {e}", exc_info=True)
        return jsonify({"error": "A database error occurred during deletion."}), 500
    
@tasks_bp.route('/tasks/space/<string:space_id>' , methods = ['DELETE'])
@jwt_required
def delete_tasks_by_space_id(space_id):
    """
    Deletes all tasks and their associated file records belonging to the given space_id.
    """
    try:
        # 1. Retrieve all tasks for the space
        tasks = Tasks.query.filter_by(space_id=space_id).all()
        
        if not tasks:
            return jsonify({"message": f"No tasks found for Space ID '{space_id}'"}), 404

        tasks_deleted_count = 0
        files_deleted_count = 0
        
        # 2. Loop through all tasks and their associated files for deletion
        for task in tasks:
            # 2a. Delete associated file records (Upload_Files) first
            # NOTE: You may also need code here to delete the physical file from disk/S3
            uploads = Upload_Files.query.filter_by(task_id=task.task_id).all()
            for upload in uploads:
                db.session.delete(upload)
                files_deleted_count += 1
            
            # 2b. Delete the main Task record
            db.session.delete(task)
            tasks_deleted_count += 1
            
        # 3. Commit all staged deletions in one transaction
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully deleted {tasks_deleted_count} task(s) and {files_deleted_count} associated file record(s) from space {space_id}.",
            "tasks_deleted": tasks_deleted_count,
            "files_records_deleted": files_deleted_count
        }), 200
        
    except Exception as e:
        # 4. Handle errors (e.g., database integrity errors)
        db.session.rollback()
        # Log the error for debugging
        # current_app.logger.error(f"Error deleting tasks in space {space_id}: {e}", exc_info=True)
        return jsonify({"error": "A database error occurred during deletion."}), 500
    
# --- PATCH Route to update vendor_id for a specific task ---
@tasks_bp.route('/tasks/assign_vendor/<string:task_id>', methods=['PATCH'])
@jwt_required
def assign_vendor_to_task(task_id):
    data = request.json
    
    # 1. Check if the vendor_id is present in the request body
    vendor_id = data.get('vendor_id')
    if not vendor_id:
        return jsonify({"error": "vendor_id is required to assign a vendor"}), 400

    # 2. Find the task by its ID
    task = Tasks.query.get_or_404(task_id)

    # 3. (Optional but recommended) Verify that the vendor_id exists in the Vendors table
    vendor = Vendors.query.get(vendor_id)
    if not vendor:
        return jsonify({"error": "The specified vendor does not exist"}), 404

    try:
        # 4. Update the vendor_id field on the task
        task.vendor_id = vendor_id
        
        # 5. Commit the changes to the database
        db.session.commit()
        
        return jsonify({"message": "Task successfully assigned to vendor"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

#===================for completion status=========================
# @tasks_bp.route('/tasks/<string:task_id>/complete', methods=['PATCH'])
# def mark_task_as_complete(task_id):
#     """
#     Marks a specific task as 'completed' and records the completion timestamp.
#     """
#     try:
#         # 1. Retrieve the task by ID, or return 404 if not found
#         task = Tasks.query.filter_by(task_id=task_id).first_or_404(
#             description=f'Task with ID {task_id} not found'
#         )

#         # 2. Check current status (Optional: Prevent re-completing)
#         if task.status == 'completed':
#             return jsonify({"message": "Task is already marked as completed"}), 200

#         # 3. Update the status and completion timestamp
#         task.status = 'completed'
#         task.completed_at = datetime.datetime.now()

#         # 4. Commit the changes to the database
#         db.session.commit()
        
#         return jsonify({
#             "message": "Task marked as completed successfully",
#             "task_id": task.task_id,
#             "completed_at": task.completed_at.isoformat() if task.completed_at else None # Return ISO format for client
#         }), 200

#     except Exception as e:
#         db.session.rollback()
#         # Log the error here for debugging
#         logger.error("Error completing task %s: %s", task_id, str(e), exc_info=True)
#         return jsonify({"error": "An unexpected server or database error occurred while completing the task."}), 500
    
#========================PUT for completion status=======================
# @tasks_bp.route('/tasks/<string:task_id>' , methods = ['PUT'])
# def update_task(task_id):
#     data = request.form
#     task = Tasks.query.get_or_404(task_id)
#     if not task:
#         return jsonify({"message":"Task not found"}) , 404
        
    # ... (existing updates for task_name, description, assigned_to, etc.) ...

    # if 'due_date' in data:
    #     task.due_date = data['due_date']
    # if 'status' in data:
    #     task.status = data['status']
    #     # 🚨 NEW LOGIC: If status is set to 'completed', set completed_at to now
    #     if data['status'].lower() == 'completed':
    #         task.completed_at = datetime.datetime.now()
    #     # 🚨 NEW LOGIC: If status is set to anything else, clear completed_at
    #     elif task.completed_at is not None:
    #         task.completed_at = None
    
    # # The frontend might also explicitly send 'completed_at' (e.g., if manually setting a past completion time)
    # if 'completed_at' in data:
    #     # Assuming completed_at is sent as a string and needs parsing
    #     # You might need more robust date parsing here (e.g., try/except with different formats)
    #     try:
    #         task.completed_at = datetime.datetime.fromisoformat(data['completed_at'])
    #     except ValueError:
    #         # Handle empty string or invalid format
    #         task.completed_at = None 

    # if 'priority' in data:
    #     task.priority = data['priority']


# @tasks_bp.route('/tasks/<string:task_id>' , methods = ['DELETE'])
# def delete_task(task_id):
#     task = Tasks.query.get_or_404(task_id)
#     try:
#         db.session.delete(task)
#         db.session.commit()
#         return jsonify({"message":"Task deleted successfully"}) , 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error" : str(e)}) , 500
    
# @tasks_bp.route('/tasks/project/<string:project_id>' , methods = ['DELETE'])
# def delete_tasks_by_project_id(project_id):
#     try:
#         tasks = Tasks.query.filter_by(project_id=project_id).all()
        
#         if not tasks:
#             return jsonify({"message": f"No tasks found for Project ID '{project_id}'"}), 404

#         tasks_deleted_count = 0
#         files_deleted_count = 0
        
#         for task in tasks:
#             uploads = Upload_Files.query.filter_by(task_id=task.task_id).all()
#             for upload in uploads:
#                 db.session.delete(upload)
#                 files_deleted_count += 1
            
#             db.session.delete(task)
#             tasks_deleted_count += 1
            
#         db.session.commit()
        
#         return jsonify({
#             "message": f"Successfully deleted {tasks_deleted_count} task(s) and {files_deleted_count} associated file record(s) from project {project_id}.",
#             "tasks_deleted": tasks_deleted_count,
#             "files_records_deleted": files_deleted_count
#         }), 200
        
#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error deleting tasks in project {project_id}: {e}", exc_info=True)
#         return jsonify({"error": "A database error occurred during deletion."}), 500
    
# @tasks_bp.route('/tasks/space/<string:space_id>' , methods = ['DELETE'])
# def delete_tasks_by_space_id(space_id):
#     try:
#         tasks = Tasks.query.filter_by(space_id=space_id).all()
        
#         if not tasks:
#             return jsonify({"message": f"No tasks found for Space ID '{space_id}'"}), 404

#         tasks_deleted_count = 0
#         files_deleted_count = 0
        
#         for task in tasks:
#             uploads = Upload_Files.query.filter_by(task_id=task.task_id).all()
#             for upload in uploads:
#                 db.session.delete(upload)
#                 files_deleted_count += 1
            
#             db.session.delete(task)
#             tasks_deleted_count += 1
            
#         db.session.commit()
        
#         return jsonify({
#             "message": f"Successfully deleted {tasks_deleted_count} task(s) and {files_deleted_count} associated file record(s) from space {space_id}.",
#             "tasks_deleted": tasks_deleted_count,
#             "files_records_deleted": files_deleted_count
#         }), 200
        
#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"Error deleting tasks in space {space_id}: {e}", exc_info=True)
#         return jsonify({"error": "A database error occurred during deletion."}), 500
    
# # --- PATCH Route to update vendor_id for a specific task (No functional change required) ---
# @tasks_bp.route('/tasks/assign_vendor/<string:task_id>', methods=['PATCH'])
# def assign_vendor_to_task(task_id):
#     data = request.json
    
#     vendor_id = data.get('vendor_id')
#     if not vendor_id:
#         return jsonify({"error": "vendor_id is required to assign a vendor"}), 400

#     task = Tasks.query.get_or_404(task_id)

#     vendor = Vendors.query.get(vendor_id)
#     if not vendor:
#         return jsonify({"error": "The specified vendor does not exist"}), 404

#     try:
#         task.vendor_id = vendor_id
#         db.session.commit()
        
#         return jsonify({"message": "Task successfully assigned to vendor"}), 200
    
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

