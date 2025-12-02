from flask import Blueprint, request, jsonify, current_app
from models import db, Spaces , Upload_Files , Drawings , Preset , Projects ,  Tasks
from .upload_files_routes import upload_space_files
import logging
import os
from flask_cors import CORS
from sqlalchemy.orm.exc import NoResultFound
from flask_jwt_extended import jwt_required , get_jwt_identity , create_access_token , create_refresh_token
import json
from sqlalchemy import distinct, func
from auth.auth import jwt_required
from utils.email_utils import send_email

spaces_bp = Blueprint('Spaces' , __name__)
CORS(spaces_bp)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def serialize_space(space):
    """Converts a Spaces object to a dictionary, including associated file metadata."""
    space_dict = {
        "space_id": space.space_id,
        "project_id": space.project_id,
        "space_name": space.space_name,
        "description": space.description,
        "space_type": space.space_type,
        "category": space.category,
        "status": space.status,
        "files": []
    }
    # Find and attach all associated files
    find_uploads = db.session.query(Upload_Files).filter(Upload_Files.space_id == space.space_id).all()
    for file in find_uploads:
        file_dict = {
            'file_id': file.file_id,
            'filename': file.filename,
            'file_size': file.file_size,
            'file_path': file.file_path
        }
        space_dict['files'].append(file_dict)
    return space_dict

@spaces_bp.route('/get/spaces', methods=['GET'])
@jwt_required
def get_all_spaces():
    """
    Retrieve All Spaces
    ---
    tags:
      - Spaces
    responses:
      200:
        description: A list of all space records with their associated files.
        schema:
          type: array
          items:
            $ref: '#/definitions/SpaceResponse'
      500:
        description: Failed to retrieve data due to a server error.
    """
    all_spaces = []
    spaces = Spaces.query.all()
    for space in spaces:

        space_dict = {
                "space_id": space.space_id,
                "project_id": space.project_id,
                "space_name": space.space_name,
                "description": space.description,
                "space_type": space.space_type,
                "category": space.category,
                "status": space.status , 
                "files":[]
        }
        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.space_id == space.space_id).all()
        for file in find_uploads:
            file_dict = {
                'file_id':file.file_id,
                'filename':file.filename,
                'file_size':file.file_size,
                'file_path':file.file_path
            }
            space_dict['files'].append(file_dict)
        all_spaces.append(space_dict)
    return jsonify(all_spaces),200

@spaces_bp.route('/get/<string:space_id>', methods=['GET'])
@jwt_required
def get_space_by_id(space_id):
    """
    Get Space by ID
    ---
    tags:
      - Spaces
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
        description: The ID of the space record to retrieve.
    responses:
      200:
        description: The single space record.
        schema:
          $ref: '#/definitions/SpaceResponse'
      404:
        description: Space with the specified ID not found.
      500:
        description: Internal server error.
    """
    try:

        space = Spaces.query.filter_by(space_id = space_id).first_or_404(
            description = f'Space with ID {space_id} not found'
        )
    # if space:
    #     return jsonify({
    #         "space_id": space.space_id,
    #         "project_id": space.project_id,
    #         "space_name": space.space_name,
    #         "description": space.description,
    #         "space_type": space.space_type,
    #         "status": space.status
    #     }), 200
    # return jsonify({"error": "Space not found"}), 404
        space_dict = {
            'space_id':space.space_id ,
            'project_id':space.project_id , 
            'space_name':space.space_name , 
            'description':space.description , 
            'space_type':space.space_type , 
            'category':space.category,
            'status':space.status,
            'files':[]
        }

        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.space_id == space.space_id).all()
        for file in find_uploads:
            file_dict = {
                'file_id':file.file_id,
                'filename':file.filename , 
                'file_path':file.file_path,
                'file_size':file.file_size
            }
            space_dict['files'].append(file_dict)
        return jsonify(space_dict),200
    except Exception as e:
        return jsonify({"error":"cannot retrieve data"}) , 500


@spaces_bp.route('/post', methods=['POST'])
@jwt_required
def create_space():
    """
    Create New Space
    ---
    tags:
      - Spaces
    consumes:
      - multipart/form-data
    parameters:
      - name: project_id
        in: formData
        type: string
        required: false
      - name: space_name
        in: formData
        type: string
        required: true
      - name: description
        in: formData
        type: string
        required: false
      - name: space_type
        in: formData
        type: string
        required: false
      - name: category
        in: formData
        type: string
        required: true
      - name: status
        in: formData
        type: string
        required: false
      - name: uploads
        in: formData
        type: file
        required: false
        description: Optional file attachments.
    responses:
      201:
        description: Space and files created successfully.
        schema:
          properties:
            message: {type: string}
            space_id: {type: string}
            file_location: {type: string}
      400:
        description: Missing required fields or data integrity error.
      500:
        description: Failed to create space due to server error.
    """
    data = request.form

    required_fields = ['space_name', 'category']
    if any(field not in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
   
    attachments = request.files.getlist("uploads")

    project_id = data.get("project_id")
    space_name = data.get("space_name")
    description = data.get("description" , None)
    space_type = data.get("space_type")
    status = data.get("status", "To Do")
    category = data.get("category", "Custom") , 
    preset_id = data.get("preset_id")  # optional

    # Optional validation for preset existence
    if preset_id:
        preset = Preset.query.filter_by(preset_id=preset_id).first()
        if not preset:
            return jsonify({"error": "Invalid preset_id"}), 400

    new_space = Spaces(
        project_id=project_id,
        space_name=space_name,
        description=description,
        space_type=space_type,
        category = category,
        status=status,
        preset_id =preset_id
    )

     # Optional validation for preset existence
    if preset_id:
        preset = Preset.query.filter_by(preset_id=preset_id).first()
        if not preset:
            return jsonify({"error": "Invalid preset_id"}), 400

    try:
        db.session.add(new_space)
        db.session.flush()
        # db.session.commit()
        upload_space_files(attachments , new_space.space_id)
        db.session.commit()
        return jsonify({
            "message": "Space created successfully", 
            "space_id": new_space.space_id,
            "file_location": f"Processed {len(attachments)} file(s)"
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating drawing: {e}")
        return jsonify({"error": "Failed to create space"}), 500
    
@spaces_bp.route('/update/<string:space_id>', methods=['PUT'])
@jwt_required
def update_space(space_id):
    """
    Update Space (Metadata and/or Files)
    ---
    tags:
      - Spaces
    consumes:
      - application/json
      - multipart/form-data
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
      - name: space_name
        in: formData
        type: string
        required: false
      - name: description
        in: formData
        type: string
        required: false
      - name: space_type
        in: formData
        type: string
        required: false
      - name: category
        in: formData
        type: string
        required: false
      - name: status
        in: formData
        type: string
        required: false
      - name: uploads
        in: formData
        type: file
        required: false
        description: New file attachments to add.
      - name: files_to_delete
        in: formData
        type: string
        required: false
        description: JSON array string of file_ids to delete (e.g., "[1, 2, 3]").
    responses:
      200:
        description: Space updated successfully.
      404:
        description: Space not found.
      400:
        description: Invalid request data or JSON format.
      500:
        description: Failed to update space due to server error.
    """
    space = Spaces.query.get(space_id)
    if not space:
        return jsonify({"error": "Space not found"}), 404
    
    is_multipart = 'multipart/form-data' in request.content_type

    attachments = []
    file_to_delete = []

    if is_multipart:
        data = request.form
        attachments = request.files.getlist("uploads")

        files_to_delete_json = data.get('files_to_delete' , '[]')
        try:
            files_to_delete = json.loads(files_to_delete_json)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format for files_to_delete"}), 400


    data = request.get_json()
    try:
        space.space_name = data.get('space_name', space.space_name)
        space.description = data.get('description', space.description)
        space.space_type = data.get('space_type', space.space_type)
        space.category = data.get('category', space.category)
        space.status = data.get('status', space.status)
        db.session.commit()
        return jsonify({"message": "Space updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update space"}), 500
    
@spaces_bp.route('/delete/<string:space_id>', methods=['DELETE'])
@jwt_required
def delete_space(space_id):
    space = Spaces.query.get(space_id)
    if not space:
        return jsonify({"error": "Space not found"}), 404

    try:
        with db.session.no_autoflush:
            # 1. Delete uploads, drawings, tasks linked to this space
            Upload_Files.query.filter_by(space_id=space_id).delete(synchronize_session=False)
            Drawings.query.filter_by(space_id=space_id).delete(synchronize_session=False)
            Tasks.query.filter_by(space_id=space_id).delete(synchronize_session=False)

            # 2. Detach projects from presets
            presets = Preset.query.filter_by(space_id=space_id).all()
            for preset in presets:
                # Detach projects that use this preset
                projects = Projects.query.filter_by(preset_id=preset.preset_id).all()
                for project in projects:
                    project.preset_id = None

            db.session.flush()  # Make sure project detachment is applied

            # 3. Detach presets from this space (instead of deleting)
            for preset in presets:
                preset.space_id = None  # Detach from the space

            db.session.flush()  # Apply detachment

            # 4. Detach all spaces from the project linked to this space
            if space.project_id:
                # Detach all spaces referencing this project
                spaces_linked = Spaces.query.filter_by(project_id=space.project_id).all()
                for s in spaces_linked:
                    s.project_id = None

                db.session.flush()  # Apply detachment

                # Now it's safe to delete the project
                project = Projects.query.get(space.project_id)
                if project:
                    db.session.delete(project)

            # 5. Delete the space itself
            db.session.delete(space)

        db.session.commit()
        return jsonify({"message": "Space deleted, project detached, and presets updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to delete space",
            "details": str(e)
        }), 500

@spaces_bp.route('/get/project/<string:project_id>', methods=['GET'])
@jwt_required
def get_spaces_by_project_id(project_id):
    """
    Retrieve All Spaces for a specific Project ID.
    """
    try:
        # 1. Query all spaces belonging to the project_id
        spaces = Spaces.query.filter_by(project_id=project_id).all()
        
        if not spaces:
            return jsonify({"message": f"No spaces found for project ID {project_id}"}), 404

        all_spaces_data = [serialize_space(space) for space in spaces]
        
        return jsonify(all_spaces_data), 200

    except Exception as e:
        logger.error(f"Error retrieving spaces for project {project_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve data"}), 500
    
@spaces_bp.route('/update/project/<string:project_id>', methods=['PUT'])
@jwt_required
def update_space_by_project_id_with_files(project_id):
    """
    Update a SINGLE Space within a Project ID. Requires space_id in form data.
    """
    is_multipart = 'multipart/form-data' in request.content_type
    
    if not is_multipart:
         return jsonify({"error": "Content-Type must be multipart/form-data for update"}), 400

    data = request.form
    attachments = request.files.getlist("uploads")
    
    space_id_to_update = data.get('space_id')
    if not space_id_to_update:
        return jsonify({"error": "Missing required field: space_id"}), 400

    space = Spaces.query.filter_by(project_id=project_id, space_id=space_id_to_update).first()
    
    if not space:
        return jsonify({"error": f"Space with ID {space_id_to_update} not found in project {project_id}"}), 404

    # --- Metadata Update ---
    try:
        space.space_name = data.get('space_name', space.space_name)
        space.description = data.get('description', space.description)
        space.space_type = data.get('space_type', space.space_type)
        space.category = data.get('category', space.category)
        space.status = data.get('status', space.status)

        # --- File Deletion and Upload ---
        files_to_delete_json = data.get('files_to_delete', '[]')
        file_ids_to_delete = json.loads(files_to_delete_json)
        
        for file_id in file_ids_to_delete:
            file_to_delete = Upload_Files.query.get(file_id)
            if file_to_delete and file_to_delete.space_id == space.space_id:
                # TODO: Add logic here to delete the physical file from the file system (os.remove)
                db.session.delete(file_to_delete)

        if attachments:
            upload_space_files(attachments, space.space_id)
        
        db.session.commit()
        
        return jsonify({"message": f"Space {space_id_to_update} updated successfully in project {project_id}"}), 200

    except json.JSONDecodeError:
        db.session.rollback()
        return jsonify({"error": "Invalid JSON format for files_to_delete"}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating space {space_id_to_update}: {e}")
        return jsonify({"error": "Failed to update space"}), 500

# @spaces_bp.route('/delete/project/<string:project_id>', methods=['DELETE'])
# @jwt_required_now
# def delete_spaces_by_project_id(project_id):
#     """
#     Delete ALL Spaces and associated files/drawings for a given Project ID.
#     This resolves Foreign Key Constraints by deleting children first.
#     """
#     try:
#         # 1. Find all spaces belonging to the project
#         spaces_to_delete = Spaces.query.filter_by(project_id=project_id).all()
        
#         if not spaces_to_delete:
#             return jsonify({"message": f"No spaces found for project ID {project_id} to delete"}), 404
        
#         deleted_count = 0
        
#         for space in spaces_to_delete:
#             space_id = space.space_id
            
#             # 2. Delete all associated file records (Upload_Files and Drawings)
            
#             # 2a. Delete Drawings (Child table)
#             drawings = Drawings.query.filter_by(space_id=space_id).all()
#             for drawing in drawings:
#                 db.session.delete(drawing)
#                 db.session.commit()
            
#             # 2b. Delete Upload_Files (Child table)
#             uploads = Upload_Files.query.filter_by(space_id=space_id).all()
#             for upload in uploads:
#                 # TODO: Add logic here to delete the physical file from the file system (os.remove)
#                 db.session.delete(upload)
#                 db.session.commit()
            
#             # 3. Delete the parent Space record
#             db.session.delete(space)
#             deleted_count += 1

#         db.session.commit()
        
#         return jsonify({
#             "message": f"Successfully deleted {deleted_count} spaces and associated records for project ID {project_id}"
#         }), 200 
    
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error deleting spaces for project {project_id}: {e}")
#         return jsonify({"error": "Failed to delete spaces", "details": str(e)}), 

# --- New Route in spaces_bp ---
def serialize_space(space):
    """
    Serializes a Space record without preset instance.
    """
    return {
        "space_id": space.space_id,
        "space_name": space.space_name,
        "project_id": space.project_id,
        "description": space.description,
        "space_type": space.space_type,
        "category": space.category,
    }


@spaces_bp.route('/get/preset/<string:preset_id>', methods=['GET'])
@jwt_required
def get_spaces_by_preset_id(preset_id):
    """
    Retrieves all Space records associated with a specific Preset ID
    and returns combined Space list + Preset details + count.
    """
    try:
        # --- Find preset details ---
        preset = Preset.query.filter_by(preset_id=preset_id).first()
        if not preset:
            return jsonify({"message": f"Preset with ID {preset_id} not found"}), 404

        # --- Fetch all spaces where space_id matches preset.space_id ---
        spaces = Spaces.query.filter_by(preset_id=preset_id).all()

        if not spaces:
            return jsonify({"error": f"No spaces found for Preset ID {preset_id}"}), 404

        # --- Serialize each space ---
        serialized_spaces = [serialize_space(space) for space in spaces]

        # --- Response format ---
        response_data = {
            "preset_id": preset.preset_id,
            "preset_name": preset.preset_name if hasattr(preset, "preset_name") else None,
            "preset_description": preset.preset_description if hasattr(preset, "preset_description") else None,
            "created_at": preset.created_at.isoformat() if hasattr(preset, "created_at") and preset.created_at else None,
            "total_spaces": len(serialized_spaces),
            "spaces": serialized_spaces
        }

        return jsonify(response_data), 200

    except Exception as e:
        logging.exception(f"[ERROR] Failed to retrieve spaces for preset {preset_id}: {e}")
        return jsonify({"error": "Failed to retrieve data"}), 500

    

# --- New Route in spaces_bp ---

@spaces_bp.route('/update/preset/<string:preset_id>', methods=['PUT', 'PATCH'])
@jwt_required
def update_space_by_preset_id(preset_id):
    """
    Updates the metadata of the single Space record associated with a specific Preset ID.
    (Does NOT handle file uploads/deletions - use the dedicated /update/<space_id> route for that)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    try:
        # 1. Find the Preset to get its space_id
        preset = Preset.query.get(preset_id)
        if not preset or not preset.space_id:
            return jsonify({"message": f"Preset {preset_id} not found or has no associated Space"}), 404

        space_id = preset.space_id
        space = Spaces.query.get(space_id)
        
        if not space:
            return jsonify({"error": f"Associated Space with ID {space_id} not found"}), 404

        # 2. Apply updates dynamically (similar to your existing update logic)
        for key, value in data.items():
            # Only update mutable attributes that exist on the model
            if hasattr(space, key) and key not in ['space_id', 'project_id']:
                setattr(space, key, value)
        
        db.session.commit()
        
        # Return the updated space data
        return jsonify(serialize_space(space)), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating space for preset {preset_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update space", "details": str(e)}), 500
    
# --- New Route in spaces_bp ---

@spaces_bp.route('/delete/preset/<string:preset_id>', methods=['DELETE'])
@jwt_required
def delete_space_by_preset_id(preset_id):
    """
    Deletes the associated Space (and its files/drawings) AND the Preset itself.
    This action maintains data integrity by removing the dependent Preset.
    """
    try:
        # 1. Find the Preset to get its space_id
        preset = Preset.query.get(preset_id)
        if not preset:
            return jsonify({"message": f"Preset with ID {preset_id} not found"}), 404

        space_id = preset.space_id
        
        # 2. Delete the Preset immediately (as its foreign key reference is about to be deleted)
        db.session.delete(preset)
        
        # 3. Find and delete the Space and its children (if an association exists)
        if space_id:
            space = Spaces.query.get(space_id)

            if space:
                # Use the existing delete_space logic but ensure a full cleanup (children first)

                # Delete Drawings (Child table)
                drawings = Drawings.query.filter_by(space_id=space_id).all()
                for drawing in drawings:
                    db.session.delete(drawing)

                # Delete Upload_Files (Child table)
                uploads = Upload_Files.query.filter_by(space_id=space_id).all()
                for upload in uploads:
                    # TODO: Add logic to delete the physical file
                    db.session.delete(upload)
                    db.session.commit()

                # Delete the parent Space record
                db.session.delete(space)
                db.session.commit()
                return jsonify({
                    "message": f"Preset {preset_id}, its associated Space {space_id}, and all related files/drawings deleted successfully."
                }), 200
            
            else:
                db.session.commit() # Commit the Preset deletion even if space wasn't found
                return jsonify({
                    "message": f"Preset {preset_id} deleted successfully. Its associated Space {space_id} was already missing."
                }), 200
        
        # Case: Preset had no space_id
        db.session.commit()
        return jsonify({"message": f"Preset {preset_id} deleted successfully. No associated Space to delete."}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting space/preset for preset {preset_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete records", "details": str(e)}), 500
    

@spaces_bp.route('/bulk', methods=['POST'])
@jwt_required
def create_spaces_bulk():
    data = request.get_json()
    spaces_list = data.get("spaces", [])

    if not isinstance(spaces_list, list) or not spaces_list:
        return jsonify({"error": "spaces must be a non-empty array"}), 400

    # 1. Create a list to hold the model objects temporarily
    new_space_objects = [] 

    try:
        for s in spaces_list:
            space_name = s.get("space_name")
            category = s.get("category", "Custom")

            if not space_name:
                return jsonify({"error": "Each space must have a space_name"}), 400

            new_space = Spaces(
                space_name=space_name,
                category=category
            )
            db.session.add(new_space)
            # Store the object, but DO NOT access the ID yet
            new_space_objects.append(new_space) 

        # 2. Commit the transaction (IDs are generated here)
        db.session.commit() 
        
        # 3. NOW build the response list using the generated IDs
        created_spaces = []
        for space_obj in new_space_objects:
             created_spaces.append({
                 "space_id": space_obj.space_id,  # <-- ID is available here
                 "space_name": space_obj.space_name
             })
             
        return jsonify({"created_spaces": created_spaces}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Bulk creation failed"}), 500
    
@spaces_bp.route('/spaces/duplicate', methods=['POST'])
@jwt_required
def duplicate_spaces_to_project():
    try:
        data = request.get_json()
        source_project_id = data.get("source_project_id")
        target_project_id = data.get("target_project_id")

        if not source_project_id or not target_project_id:
            return jsonify({"message": "Both source_project_id and target_project_id are required"}), 400

        # Fetch all spaces from source project
        source_spaces = Spaces.query.filter_by(project_id=source_project_id).all()

        if not source_spaces:
            return jsonify({"message": "No spaces found for the source project"}), 404

        # Duplicate each space into the target project
        for space in source_spaces:
            new_space = Spaces(
                project_id=target_project_id,
                space_name=space.space_name,
                description=space.description,
                space_type=space.space_type,
                category=space.category
            )
            db.session.add(new_space)

        db.session.commit()

        return jsonify({"message": "Spaces duplicated successfully to target project",
                        "count": len(source_spaces)}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500

@spaces_bp.route('/spaces/apply-template', methods=['POST'])
@jwt_required
def apply_template_to_project():
    try:
        data = request.get_json()
        selected_preset_id = data.get("preset_id") # Changed variable name for clarity
        project_id = data.get("project_id")

        if not selected_preset_id or not project_id:
            return jsonify({"message": "preset_id and project_id are required"}), 400

        # 1. Validate Preset existence and fetch its name for the new spaces' category
        try:
            preset_info = Preset.query.filter_by(preset_id=selected_preset_id).one()
            preset_name = preset_info.preset_name
        except NoResultFound:
            return jsonify({"message": f"Preset with ID {selected_preset_id} not found"}), 404

        # 2. Get the blueprint (list of unique space names) from the Spaces table itself
        # This assumes all unique space_name entries linked to this preset_id define the template.
        blueprint_spaces_results = db.session.query(distinct(Spaces.space_name)).filter(
            Spaces.preset_id == selected_preset_id
        ).all()
        
        # Extract the names from the query result tuples
        blueprint_space_names = [r[0] for r in blueprint_spaces_results]

        if not blueprint_space_names:
            return jsonify({"message": f"No blueprint spaces found in the database for preset ID {selected_preset_id}"}), 404

        created_spaces = []
        for space_name_to_clone in blueprint_space_names:
            # 3. Create a new Space record for the target project
            # NOTE: Since we only have the name (blueprint), we use default/derived values 
            # for description, type, and status.
            new_space = Spaces(
                project_id=project_id,
                space_name=space_name_to_clone,
                description=f"Space created from '{preset_name}' template.",
                space_type='Preset', # Use a standard type
                category=preset_name, # Use the Preset's name as the category
                preset_id=selected_preset_id # Keep the link back to the source preset
            )
            db.session.add(new_space)
            created_spaces.append(new_space.space_name)

        db.session.commit()

        return jsonify({
            "message": "Template applied successfully. New spaces created.",
            "project_id": project_id,
            "created_spaces_count": len(created_spaces),
            "created_space_names": created_spaces
        }), 201

    except Exception as e:
        db.session.rollback()
        # Ensure current_app.logger is imported/available if you use it, or just use print/logging
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500

@spaces_bp.route('/projects/<project_id>/apply-preset', methods=['POST'])
@jwt_required
def apply_preset_to_project(project_id):
    data = request.get_json()
    preset_id = data.get("preset_id")

    if not preset_id:
        return jsonify({"error": "preset_id is required"}), 400

    # Fetch project
    project = Projects.query.filter_by(project_id=project_id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Fetch preset
    preset = Preset.query.filter_by(preset_id=preset_id).first()
    if not preset:
        return jsonify({"error": "Preset not found"}), 404

    # Apply preset to project
    project.preset_id = preset_id

    # Create a new space based on the preset
    new_space = Spaces(
        project_id=project.project_id,
        preset_id=preset.preset_id,
        space_name=preset.preset_name,              # you can customize this
        description=preset.preset_description,      # optional
        space_type=preset.preset_type,             # from preset_type
        category="Preset"                           # categorize as preset-generated
    )

    db.session.add(new_space)
    db.session.commit()

    return jsonify({
        "message": "Preset applied and space generated successfully",
        "project_id": project_id,
        "preset_id": preset_id,
        "generated_space_id": new_space.space_id
    }), 200


@spaces_bp.route('/delete/project/<string:project_id>', methods=['DELETE'])
@jwt_required
def delete_spaces_by_project_id(project_id):
    """
    Delete ALL Spaces, and associated files/drawings for a given Project ID.
    This resolves Foreign Key Constraints by deleting children first, and 
    uses a single transaction for atomicity.
    """
    try:
        # 1. Find all spaces belonging to the project
        spaces_to_delete = Spaces.query.filter_by(project_id=project_id).all()
        
        if not spaces_to_delete:
            return jsonify({"message": f"No spaces found for project ID {project_id} to delete"}), 404
        
        deleted_count = 0
        
        for space in spaces_to_delete:
            space_id = space.space_id
            
            # --- START DELETION OF CHILDREN (Child -> Parent Order) ---
            
            # Find all Drawings belonging to this space
            drawings_to_delete = Drawings.query.filter_by(space_id=space_id).all()
            
            # 2. Iterate through Drawings to delete their children (Upload_Files) first.
            for drawing in drawings_to_delete:
                drawing_id = drawing.drawing_id

                # 2a. Delete Upload_Files (Child table referencing Drawings).
                uploads = Upload_Files.query.filter_by(drawing_id=drawing_id).all()
                for upload in uploads:
                    # TODO: Add logic here to delete the physical file from the file system (os.remove)
                    db.session.delete(upload)
                    db.session.commit()
                # 2b. Delete the parent Drawing record.
                db.session.delete(drawing)
                db.session.commit()
                
            # >>>>>> FIX IS ADDED HERE: Delete records from the 'tasks' table <<<<<<
            # Note: Add deletion logic for any other tables that reference Space here (e.g., Tasks)
            tasks_to_delete = Tasks.query.filter_by(space_id=space_id).all() # Assuming Tasks is your model
            for task in tasks_to_delete:
                db.session.delete(task)
                db.session.commit()
            
            # 3. Delete the ultimate parent Space record
            db.session.delete(space)
            deleted_count += 1
            db.session.commit()

        # 4. Commit all deletions at once (Single Transaction)
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully deleted {deleted_count} spaces and associated records for project ID {project_id}"
        }), 200
        
    except Exception as e:
        # 5. Rollback on any error to ensure data integrity
        db.session.rollback()
        
        print(f"Error deleting spaces for project {project_id}: {e}") 
        
        return jsonify({
            "error": "Failed to delete spaces due to a database error.", 
            "details": str(e)
        }), 500