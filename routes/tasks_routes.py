from flask import Blueprint , jsonify , request , current_app
from models import Tasks , db , Vendors , Upload_Files , Clients, Projects
import datetime
from  .upload_files_routes import upload_task_files
import uuid
import logging
from flask_cors import CORS

tasks_bp = Blueprint('tasks', __name__)
CORS(tasks_bp)

#get all tasks
@tasks_bp.route('/tasks' , methods = ['GET'])
def get_all_tasks():
    try:
        all_tasks = []
        tasks = Tasks.query.all()
        
        for task in tasks:
            task_dict = ({
                'task_id' : task.task_id , 
                'project_id' : task.project_id , 
                'task_name' : task.task_name , 
                'description' : task.description , 
                # 'assigned_to' : task.assigned_to , 
                # 'due_date' : task.due_date , 
                # 'status' : task.status , 
                # 'created_at' : task.created_at , 
                # 'updated_at' : task.updated_at ,
                # 'completed_at' : task.completed_at ,
                # 'priority' : task.priority ,
                # 'estimated_hours' : task.estimated_hours ,
                # 'actual_hours' : task.actual_hours ,
                # 'logged_hours' : task.logged_hours,
                # 'assigned_vendor':task.assigned_vendor,
                # 'location':task.location , 
                # 'assigned_team':task.assigned_team , 
                'task_type':task.task_type,
                # 'sapce_id':task.space_id,
                # 'files':[]
            })
            find_uploads = db.session.query(Upload_Files).filter(Upload_Files == task.task_id).all()
            for file in find_uploads:
                file_dict = {
                    'file_id':file.file_id , 
                    'filename':file.filename , 
                    'file_size':file.files_size , 
                    'file_path' : file.file_path
                }
                task_dict['files'].append(file_dict)
            all_tasks.append(task_dict)

        return jsonify(all_tasks) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#get single task by id
@tasks_bp.route('/tasks/<string:task_id>' , methods = ['GET'])
def get_task_by_id(task_id):

    task = Tasks.query.filter_by(task_id = task_id).first_or_404(
        description = f'Task with ID {task_id} not found'
    )
    
    task_dict = {
        'task_id' : task.task_id , 
        'project_id' : task.project_id , 
        'task_name' : task.task_name , 
        'description' : task.description , 
        'assigned_to' : task.assigned_to , 
        # 'due_date' : task.due_date , 
        # 'status' : task.status , 
        # 'created_at' : task.created_at ,
        # 'updated_at' : task.updated_at , 
        # 'completed_at' : task.completed_at ,
        # 'priority' : task.priority , 
        # 'estimated_hours' : task.estimated_hours ,
        # 'actual_hours' : task.actual_hours , 
        # 'logged_hours' : task.logged_hours,
        # 'assigned_vendor':task.assigned_vendor,
        # 'location':task.location , 
        'task_type':task.task_type , 
        # 'assigned_team':task.assigned_team,
        # 'space_id':task.space_id,
        # 'files':[]

    }
    find_uploads = db.session.query(Upload_Files).filter(Upload_Files.task_id == task.task_id).all()
    for file in find_uploads:
        file_dict = {
            "file_id" : file.file_id , 
            "filenname" : file.filename , 
            "file_path" : file.file_path , 
            "file_size" : file.file_size
        } 
        task_dict['files'].append(file_dict)
    return jsonify(task_dict) , 200


#Get tasks by project_id and space_id
@tasks_bp.route('/tasks/project/<string:project_id>' , methods = ['GET'])
def get_tasks_by_project_id(project_id):
    tasks = Tasks.query.filter_by(project_id = project_id).all()
    all_tasks = []
    for task in tasks:
        task_dict = {
            'task_id' : task.task_id , 
            'project_id' : task.project_id , 
            'task_name' : task.task_name , 
            'description' : task.description , 
            'assigned_to' : task.assigned_to , 
            # 'due_date' : task.due_date , 
            # 'status' : task.status , 
            # 'created_at' : task.created_at , 
            # 'updated_at' : task.updated_at ,
            # 'completed_at' : task.completed_at ,
            # 'priority' : task.priority ,
            # 'estimated_hours' : task.estimated_hours ,
            # 'actual_hours' : task.actual_hours ,
            # 'logged_hours' : task.logged_hours,
            # 'assigned_vendor':task.assigned_vendor,
            # 'location':task.location , 
            # 'assigned_team':task.assigned_team , 
            'task_type':task.task_type,
            # 'space_id':task.space_id,
            # 'files':[]
        }
        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.task_id == task.task_id).all()
        for file in find_uploads:
            file_dict = {
                'file_id':file.file_id , 
                'filename':file.filename , 
                'file_size':file.files_size , 
                'file_path' : file.file_path
            }
            task_dict['files'].append(file_dict)
        all_tasks.append(task_dict)

    return jsonify(all_tasks) , 200

@tasks_bp.route('/tasks/space/<string:space_id>' , methods = ['GET'])
def get_tasks_by_space_id(space_id):
    tasks = Tasks.query.filter_by(space_id = space_id).all()
    all_tasks = []
    for task in tasks:
        task_dict = {
            'task_id' : task.task_id , 
            'project_id' : task.project_id , 
            'task_name' : task.task_name , 
            'description' : task.description , 
            'assigned_to' : task.assigned_to , 
            # 'due_date' : task.due_date , 
            # 'status' : task.status , 
            # 'created_at' : task.created_at , 
            # 'updated_at' : task.updated_at ,
            # 'completed_at' : task.completed_at ,
            # 'priority' : task.priority ,
            # 'estimated_hours' : task.estimated_hours ,
            # 'actual_hours' : task.actual_hours ,
            # 'logged_hours' : task.logged_hours,
            # 'assigned_vendor':task.assigned_vendor,
            # 'location':task.location , 
            # 'assigned_team':task.assigned_team , 
            'task_type':task.task_type,
            # 'space_id':task.space_id,
            # 'files':[]
        }
        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.task_id == task.task_id).all()
        for file in find_uploads:
            file_dict = {
                'file_id':file.file_id , 
                'filename':file.filename , 
                'file_size':file.files_size , 
                'file_path' : file.file_path
            }
            task_dict['files'].append(file_dict)
        all_tasks.append(task_dict)

    return jsonify(all_tasks) , 200



#post task

# Setup basic logging (You should configure this once in your app.py)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 
@tasks_bp.route('/tasks' , methods = ['POST'])
def add_tasks():
    data = request.get_json()
    logger.info("Received POST request data: %s", data)
    required_fields = ['task_name', 'description', 'task_type', 'project_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f"'{field}' is required"}), 400
            
    # Validate project exists
    project = Projects.query.get(data.get('project_id'))
    if not project:
        return jsonify({'error': f"Project with ID {data.get('project_id')} not found"}), 404
        
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
                        'file_location' : f"Processed {len(attachments)} file(s)"}) , 201
    except Exception as e:
        db.session.rollback()
        logger.error("Error creating task: %s", str(e), exc_info=True) # Log the traceback
        return jsonify({"error" : str(e)}) , 500
    
#update task by id
@tasks_bp.route('/tasks/<string:task_id>' , methods = ['PUT'])
def update_task(task_id):
    data = request.form
    task = Tasks.query.get_or_404(task_id)
    if not task:
        return jsonify({"message":"Task not found"}) , 404
    # if 'project_id' in data:
    #     task.project_id = data['project_id']
    if 'task_name' in data:
        task.task_name = data['task_name']
    if 'description' in data:
        task.description = data['description']
    if 'assigned_to' in data:
        task.assigned_to = data['assigned_to']
    if 'due_date' in data:
        task.due_date = data['due_date']
    if 'status' in data:
        task.status = data['status']
    if 'completed_at' in data:
        task.completed_at = data['completed_at']
    if 'priority' in data:
        task.priority = data['priority']
    if 'estimated_hours' in data:
        task.estimated_hours = data['estimated_hours']
    if 'actual_hours' in data:
        task.actual_hours = data['actual_hours']
    if 'logged_hours' in data:
        task.logged_hours = data['logged_hours']
    
    try:
        db.session.commit()
        return jsonify({'message':'Task updated successfully'}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
@tasks_bp.route('/tasks/project/<string:project_id>' , methods = ['PUT'])
def update_tasks_by_project_id(project_id):
    """
    Updates metadata for ALL tasks within a project_id via form-data.
    If 'task_id' is provided in the form, files are uploaded and associated 
    with that single specific task.
    """
    # 🚨 KEY CHANGE: Use request.form for metadata and request.files for files
    data = request.form
    attachments = request.files.getlist("uploads")
    
    # Optional: Get a single task_id if files are being uploaded for a specific task
    specific_task_id = data.get('task_id')
    
    # Define updatable fields
    updatable_fields = [
        'task_name', 'description', 'assigned_to', 'due_date', 'status',
        'completed_at', 'priority', 'estimated_hours', 'actual_hours', 
        'logged_hours'
    ]

    try:
        # 1. Query all tasks for the project ID
        tasks = Tasks.query.filter_by(project_id = project_id).all()
        
        if not tasks:
            return jsonify({"message": f"No tasks found for Project ID '{project_id}'"}), 404

        fields_updated_count = 0
        tasks_updated_count = 0
        
        # 2. Loop through tasks and apply bulk metadata updates
        for task in tasks:
            update_applied_to_task = False
            
            for field in updatable_fields:
                if field in data:
                    setattr(task, field, data[field])
                    fields_updated_count += 1
                    update_applied_to_task = True
            
            if update_applied_to_task:
                tasks_updated_count += 1
                
        # 3. Handle File Uploads (If a specific task ID is provided)
        files_uploaded_count = 0
        if specific_task_id and attachments:
            # Find the specific task object within the retrieved list
            target_task = next((t for t in tasks if str(t.task_id) == specific_task_id), None)
            
            if target_task:
                # 🚨 Utility Function Call: Must be defined and imported elsewhere
                # This function must handle saving the files and creating Upload_Files records.
                # upload_task_files(attachments, target_task.task_id) 
                
                files_uploaded_count = len([f for f in attachments if f.filename])
            else:
                 # The task_id provided for file upload doesn't exist in this project
                 return jsonify({"error": f"Task ID '{specific_task_id}' not found within Project ID '{project_id}'."}), 404
        
        # 4. Check if any action was requested
        if fields_updated_count == 0 and files_uploaded_count == 0:
            return jsonify({"message": "No valid fields or files provided for update."}), 200

        # 5. Commit changes
        db.session.commit()
        
        # 6. Prepare success message
        message = f'Successfully updated metadata for {tasks_updated_count} tasks for Project ID {project_id}.'
        if files_uploaded_count > 0:
             message += f' {files_uploaded_count} file(s) uploaded to task {specific_task_id}.'
             
        return jsonify({
            'message': message,
            'tasks_updated': tasks_updated_count
        }), 200

    except Exception as e:
        # This structure simplifies the two except blocks into one robust block
        db.session.rollback()
        # Logging the error for debugging purposes (assuming current_app.logger is set up)
        # current_app.logger.error(f"Unexpected Error updating tasks for project {project_id}: {e}", exc_info=True) 
        return jsonify({"error" : "An unexpected server or database error occurred during the update."}), 500

@tasks_bp.route('/tasks/space/<string:space_id>' , methods = ['PUT'])
def update_tasks_by_space_id(space_id):
    """
    Updates metadata for ALL tasks within a space_id via form-data.
    If 'task_id' is provided in the form, files are uploaded and associated 
    with that single specific task.
    """
    # 🚨 KEY CHANGE: Use request.form for metadata and request.files for files
    data = request.form
    attachments = request.files.getlist("uploads")
    
    # Optional: Get a single task_id if files are being uploaded for a specific task
    specific_task_id = data.get('task_id')
    
    try:
        # 1. Retrieve all tasks by space_id
        tasks = Tasks.query.filter_by(space_id = space_id).all()
        
        if not tasks:
            return jsonify({"message":"No tasks found for the given space ID"}) , 404

        tasks_updated = 0
        
        # 2. Bulk Update Metadata for ALL Tasks in the Space
        for task in tasks:
            update_applied = False
            
            # Use 'data' (from request.form) to update fields
            if 'task_name' in data:
                task.task_name = data['task_name']
                update_applied = True
            if 'description' in data:
                task.description = data['description']
                update_applied = True
            if 'assigned_to' in data:
                task.assigned_to = data['assigned_to']
                update_applied = True
            if 'due_date' in data:
                task.due_date = data['due_date']
                update_applied = True
            if 'status' in data:
                task.status = data['status']
                update_applied = True
            if 'completed_at' in data:
                task.completed_at = data['completed_at']
                update_applied = True
            if 'priority' in data:
                task.priority = data['priority']
                update_applied = True
            if 'estimated_hours' in data:
                task.estimated_hours = data['estimated_hours']
                update_applied = True
            if 'actual_hours' in data:
                task.actual_hours = data['actual_hours']
                update_applied = True
            if 'logged_hours' in data:
                task.logged_hours = data['logged_hours']
                update_applied = True
            
            if update_applied:
                tasks_updated += 1
                
        # 3. Handle File Uploads (Only if a specific task ID is provided)
        files_uploaded_count = 0
        if specific_task_id and attachments:
            target_task = next((t for t in tasks if str(t.task_id) == specific_task_id), None)
            
            if target_task:
                # 🚨 Call your utility function (must be defined elsewhere)
                # This function should save the files and create Upload_Files records.
                # upload_task_files(attachments, target_task.task_id) 
                
                files_uploaded_count = len([f for f in attachments if f.filename])
                
        
        if tasks_updated == 0 and files_uploaded_count == 0:
             return jsonify({"message": "No valid metadata fields or files provided for update."}), 200

        # 4. Commit all changes (metadata and file record creations)
        db.session.commit()
        
        message = f'Tasks updated successfully ({tasks_updated} tasks metadata changed).'
        if files_uploaded_count > 0:
             message += f' {files_uploaded_count} file(s) uploaded to task {specific_task_id}.'
             
        return jsonify({'message': message}) , 200
        
    except Exception as e:
        db.session.rollback()
        # You should use current_app.logger.error here, not just return the string
        # current_app.logger.error(f"Error updating tasks in space {space_id}: {e}", exc_info=True)
        return jsonify({"error" : str(e)}) , 500

#delete task by id
@tasks_bp.route('/tasks/<string:task_id>' , methods = ['DELETE'])
def delete_task(task_id):
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
def delete_tasks_by_project_id(project_id):
    """
    Deletes all tasks and their associated file records belonging to the given project_id.
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
