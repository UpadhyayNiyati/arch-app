from flask import Blueprint , jsonify , request , current_app
from models import Tasks , db , Vendors , Upload_Files
import datetime
from  .upload_files_routes import upload_task_files
import uuid
import logging

tasks_bp = Blueprint('tasks', __name__)

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
                'assigned_to' : task.assigned_to , 
                'due_date' : task.due_date , 
                'status' : task.status , 
                'created_at' : task.created_at , 
                'updated_at' : task.updated_at ,
                'completed_at' : task.completed_at ,
                'priority' : task.priority ,
                'estimated_hours' : task.estimated_hours ,
                'actual_hours' : task.actual_hours ,
                'logged_hours' : task.logged_hours,
                'assigned_vendor':task.assigned_vendor,
                'location':task.location , 
                'assigned_team':task.assigned_team , 
                'task_type':task.task_type,
                'sapce_id':task.space_id,
                'files':[]
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
        'due_date' : task.due_date , 
        'status' : task.status , 
        'created_at' : task.created_at ,
        'updated_at' : task.updated_at , 
        'completed_at' : task.completed_at ,
        'priority' : task.priority , 
        'estimated_hours' : task.estimated_hours ,
        'actual_hours' : task.actual_hours , 
        'logged_hours' : task.logged_hours,
        'assigned_vendor':task.assigned_vendor,
        'location':task.location , 
        'task_type':task.task_type , 
        'assigned_team':task.assigned_team,
        'space_id':task.space_id,
        'files':[]

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



#post task

# Setup basic logging (You should configure this once in your app.py)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) 
@tasks_bp.route('/tasks' , methods = ['POST'])
def add_tasks():
    data = request.form
    logger.info("Received POST request data: %s", data)
    required_fields = ['project_id' , 'task_name' , 'description' , 'assigned_to' , 'due_date' , 'status' , 'space_id' , 'task_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"'{field}' is required"}), 400
        
    assigned_vendor = data.get('assigned_vendor')
    assigned_team = data.get('assigned_team')

    # Condition: Must have AT LEAST ONE and NOT BOTH (Exclusive OR / XOR)
    has_vendor = bool(assigned_vendor)
    has_team = bool(assigned_team)
    
    # Check for XOR (Either one, but not both, is true)
    if has_vendor == has_team: # This is true if (True and True) or (False and False)
        if has_vendor and has_team:
            return jsonify({'error': "Task cannot be assigned to both a vendor and a team. Choose one."}), 400
        else:
            return jsonify({'error': "Task must be assigned to either an 'assigned_vendor' or an 'assigned_team'."}), 400
        
    attachments = request.files.getlist("uploads")
    logger.info("Detected %d file attachment(s).", len(attachments))
    try:
        new_task = Tasks(
            project_id = data.get('project_id') , 
            task_name = data.get('task_name') , 
            description = data.get('description') , 
            assigned_to = data.get('assigned_to') ,
            due_date = data.get('due_date') , 
            status = data.get('status') , 
            priority = data.get('priority') ,
            estimated_hours = data.get('estimated_hours') ,
            #actual_hours = data.get('actual_hours') ,
            #logged_hours = data.get('logged_hours') , 
            assigned_vendor = data.get('assigned_vendor'),
            assigned_team = data.get('assigned_team'),
            space_id = data.get('space_id'),
            task_type = data.get('task_type') , 
            location = data.get('location')
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
