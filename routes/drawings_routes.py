from flask import Blueprint, request, jsonify, current_app
from models import Upload_Files, db, Drawings ,Spaces # Assuming your models are in 'your_app_module'
import logging
from .upload_files_routes import upload_drawing_files , update_drawing_files
from flask_jwt_extended import jwt_required , get_jwt_identity , create_access_token , create_refresh_token
from datetime import datetime , timedelta
import os
from flask_cors import CORS
import json

drawings_bp = Blueprint('drawings_bp', __name__)

logger = logging.getLogger(__name__)


CORS(drawings_bp)
# Route to get all drawings
@drawings_bp.route('/get', methods=['GET'])
# @jwt_required()
def get_drawings():
    """
    Retrieves all drawings from the database, with their associated file details.
    """
    try:
        all_drawings = []
        drawings = Drawings.query.all()
        
        for drawing in drawings:
            drawing_dict = {
                "drawing_id": drawing.drawing_id,
                "space_id": drawing.space_id,
                "drawing_name": drawing.drawing_name,
                "revision_number": drawing.revision_number,
                "description": drawing.description,
                "uploaded_at": drawing.uploaded_at.isoformat(),
                "files" : []
            }
            
            find_uploads = db.session.query(Upload_Files).filter(Upload_Files.drawing_id == drawing.drawing_id).all()
            print(find_uploads)
            for file in find_uploads:
                file_dict = {
                    "file_id": file.file_id,
                    "filename": file.filename,
                    "file_path": file.file_path,
                    "file_size": file.file_size,
                    
                }
                drawing_dict["files"].append(file_dict)
            
            all_drawings.append(drawing_dict)
            
        return jsonify(all_drawings), 200
        
    except Exception as e:
        logging.exception(f"Error retrieving drawings: {e}")
        return jsonify({"error": str(e)}), 500


@drawings_bp.route('/get/<string:drawing_id>', methods=['GET'])
# @jwt_required()
def get_drawing_by_id(drawing_id):
    """
    Retrieves a single drawing by ID from the database, with its associated file details.
    
    :param drawing_id: The ID of the drawing to retrieve.
    """
    try:
        # 1. Retrieve the single drawing by its ID. Use first_or_404 for convenience.
        drawing = Drawings.query.filter_by(drawing_id=drawing_id).first_or_404(
            description=f'Drawing with ID {drawing_id} not found'
        )
        
        # 2. Convert the drawing object to a dictionary
        drawing_dict = {
            "drawing_id": drawing.drawing_id,
            "space_id": drawing.space_id,
            "drawing_name": drawing.drawing_name,
            "revision_number": drawing.revision_number,
            "description": drawing.description,
            "uploaded_at": drawing.uploaded_at.isoformat(),
            "files" : []
        }
        
        # 3. Retrieve all associated files for this specific drawing
        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.drawing_id == drawing.drawing_id).all()
        
        # 4. Loop through the files and add their details to the files list in the drawing_dict
        for file in find_uploads:
            file_dict = {
                "file_id": file.file_id,
                "filename": file.filename,
                "file_path": file.file_path,
                "file_size": file.file_size,
            }
            drawing_dict["files"].append(file_dict)
            
        # 5. Return the single drawing dictionary
        return jsonify(drawing_dict), 200
        
    except Exception as e:
        # Use logging for server-side error tracking
        logging.exception(f"Error retrieving drawing ID {drawing_id}: {e}")
        
        # Check if the error is due to a missing resource (e.g., from first_or_404)
        if hasattr(e, 'code') and e.code == 404:
            return jsonify({"error": str(e)}), 404
            
        return jsonify({"error": "An unexpected error occurred."}), 500
    
@drawings_bp.route('/update/drawing/<string:drawing_id>', methods=['PUT'])
# @jwt_required()
def update_drawing_by_id(drawing_id):
    """
    Updates a single drawing's metadata and files using only the drawing_id from the URL.
    This replaces the constraint based on space_id.
    """
    
    # --- 1. Data Retrieval and Content Type Check ---
    is_multipart = request.mimetype and 'multipart/form-data' in request.mimetype
    attachments = []
    files_to_delete = []
    data = {}
    
    if not is_multipart:
         # Use 415 if the content type is required to be multipart
         return jsonify({"error": "Content-Type must be multipart/form-data for file/metadata updates."}), 415 

    # Data is retrieved from request.form for multipart/form-data
    data = request.form
    attachments = request.files.getlist("uploads")
    
    # Parse files to delete
    files_to_delete_json = data.get('files_to_delete', '[]')
    try:
        files_to_delete = json.loads(files_to_delete_json)
        if not isinstance(files_to_delete, list):
            raise TypeError()
    except (json.JSONDecodeError, TypeError):
        return jsonify({"error": "Invalid format for files_to_delete. Must be a JSON array string."}), 400
    
    # --- 2. Validation and Query ---
    
    # 🛑 CORE QUERY: Find the drawing using the ID from the URL 🛑
    # Use .get() which searches by primary key (drawing_id)
    drawing = Drawings.query.get(drawing_id) 
    
    if not drawing:
        return jsonify({"error": f"Drawing ID '{drawing_id}' not found."}), 404

    # --- 3. Update Logic ---
    fields_updated = False
    files_changed = attachments or files_to_delete
    
    # Apply metadata changes
    if 'drawing_name' in data:
        drawing.drawing_name = data['drawing_name']
        fields_updated = True
        
    if 'description' in data:
        drawing.description = data['description']
        fields_updated = True
        
    if 'tags' in data:
        drawing.tags = data['tags'] # Assuming 'tags' field exists in Drawings model
        fields_updated = True


    try:
        # Check if no changes were requested at all
        if not fields_updated and not files_changed:
            return jsonify({"message": "No metadata or files provided for update."}), 200

        # Handle File/Revision Updates if a file action occurred
        if files_changed:
            # Increment revision number
            drawing.revision_number = (drawing.revision_number or 0) + 1
            
            # Call your file utility function
            update_drawing_files(attachments, drawing.drawing_id, files_to_delete)
        
        # Commit all changes 
        db.session.commit()
        
        # --- 4. Success Response ---
        message = "Drawing updated successfully"
        if fields_updated and files_changed:
            message = "Drawing metadata and files updated successfully"
        elif files_changed:
            message = "Drawing files updated successfully (no metadata changed)"
        
        return jsonify({
            "message": message,
            "drawing_id": drawing.drawing_id,
            "new_revision": drawing.revision_number,
            "files_added": len(attachments),
            "files_deleted": len(files_to_delete)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating drawing/files for ID {drawing_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update drawing or files"}), 500
    
    

@drawings_bp.route('/get/space/<string:space_id>', methods=['GET'])
# @jwt_required()
def get_drawings_by_space_id(space_id):
    """
    Retrieves ALL drawings associated with a specific space_id, with file details.
    """
    try:
        # 1. Retrieve ALL drawings by space_id
        drawings = Drawings.query.filter_by(space_id=space_id).all()
        
        if not drawings:
            # Return 404 if the space exists but has no drawings
            return jsonify({"message": f"No drawings found for space ID '{space_id}'"}), 404

        all_drawings_data = []
        
        for drawing in drawings:
            drawing_dict = {
                "drawing_id": drawing.drawing_id,
                "space_id": drawing.space_id,
                "drawing_name": drawing.drawing_name,
                "revision_number": drawing.revision_number,
                "description": drawing.description,
                "uploaded_at": drawing.uploaded_at.isoformat(),
                "files" : []
            }
            
            # 2. Retrieve and attach associated files for each drawing
            find_uploads = db.session.query(Upload_Files).filter(Upload_Files.drawing_id == drawing.drawing_id).all()
            for file in find_uploads:
                drawing_dict["files"].append({
                    "file_id": file.file_id,
                    "filename": file.filename,
                    "file_path": file.file_path,
                    "file_size": file.file_size,
                })
            
            all_drawings_data.append(drawing_dict)
            
        return jsonify(all_drawings_data), 200
        
    except Exception as e:
        logging.exception(f"Error retrieving drawings by space ID {space_id}: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500


@drawings_bp.route('/update/<string:space_id>', methods=['PUT'])
# @jwt_required()
def update_drawing_by_space_id_handler(space_id):
    """
    Updates a single drawing's metadata and files, identified by a drawing_id 
    in the body, constrained by the space_id in the URL.
    """
    
    # --- 1. Data Retrieval ---
    is_multipart = request.mimetype and 'multipart/form-data' in request.mimetype
    attachments = []
    files_to_delete = []
    data = {}
    drawing_id = None
    
    if is_multipart:
        data = request.form
        drawing_id = data.get('drawing_id')
        attachments = request.files.getlist("uploads")
        
        # Parse files to delete
        files_to_delete_json = data.get('files_to_delete', '[]')
        try:
            files_to_delete = json.loads(files_to_delete_json)
            if not isinstance(files_to_delete, list):
                raise TypeError()
        except (json.JSONDecodeError, TypeError):
            return jsonify({"error": "Invalid format for files_to_delete. Must be a JSON array string."}), 400

    else: # application/json
        try:
            data = request.get_json()
            if data is not None:
                drawing_id = data.get('drawing_id')
        except:
            return jsonify({"error": "Invalid JSON body."}), 400
    
    # --- 2. Validation and Query ---
    if not drawing_id:
        return jsonify({"error": "A 'drawing_id' is required in the request body to identify the drawing to update."}), 400

    # Log the exact parameters used for the query (for debugging 404s)
    logger.info(f"Attempting to update Drawing ID: '{drawing_id}' in Space ID: '{space_id}'")

    # 🛑 THE CORE QUERY: Ensures drawing belongs to the space 🛑
    drawing = Drawings.query.filter_by(drawing_id=drawing_id, space_id=space_id).first()
    
    if not drawing:
        # Returns 404 because the ID pair did not match a record.
        return jsonify({"error": f"Drawing ID '{drawing_id}' not found in Space ID '{space_id}'"}), 404

    # --- 3. Update Logic ---
    fields_updated = ('drawing_name' in data or 'description' in data)
    files_changed = attachments or files_to_delete
    
    # Apply metadata changes
    if 'drawing_name' in data:
        drawing.drawing_name = data['drawing_name']
        
    if 'description' in data:
        drawing.description = data['description']

    try:
        # Check if no changes were requested at all
        if not fields_updated and not files_changed:
            return jsonify({"message": "No metadata or files provided for update."}), 200

        # Handle File/Revision Updates if a file action occurred
        if files_changed:
            # Increment revision number
            drawing.revision_number = (drawing.revision_number or 0) + 1
            
            # Call your file utility function
            update_drawing_files(attachments, drawing.drawing_id, files_to_delete)
        
        # Commit all changes 
        db.session.commit()
        
        # --- 4. Success Response ---
        message = "Drawing updated successfully"
        if fields_updated and files_changed:
             message = "Drawing metadata and files updated successfully"
        elif files_changed:
             message = "Drawing files updated successfully (no metadata changed)"
        
        return jsonify({
            "message": message,
            "drawing_id": drawing.drawing_id,
            "new_revision": drawing.revision_number,
            "files_added": len(attachments),
            "files_deleted": len(files_to_delete)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating drawing/files for ID {drawing_id} in space {space_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update drawing or files"}), 500
    
# Route to create a new drawing
@drawings_bp.route('/post', methods=['POST'])
# @jwt_required()
def create_drawing():
    # space = Spaces.query.get(space_id)
    # if not space:
        # return jsonify({"error": f"Space ID '{space_id}' not found."}), 404
   
    data = request.form
    
    # if not data or 'space_id' not in data or 'drawing_name' or 'description' not  in data:
        # return jsonify({"error": "Missing required fields"}), 400

    required_fields = ['drawing_name', 'description']
    
    # Check if any required field is NOT present in data
    if any(field not in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    # if file and allowed_file(file.filename):
    #  # Secure the filename to prevent directory traversal attacks
    # filename = secure_filename(file.filename)
    # file_path = os.path.join(upload_folder, filename)
    attachments = request.files.getlist("uploads")

    new_drawing = Drawings(
        space_id=data.get('space_id'),
        tags = data.get('tags'),
        drawing_name=data.get('drawing_name'),
        description=data.get('description')
        
    )
    
    try:
        db.session.add(new_drawing)
        db.session.flush()
        # db.session.commit()
        upload_drawing_files(attachments, new_drawing.drawing_id)
        db.session.commit()
        return jsonify({
            "message": "Drawing and file uploaded successfully", 
            "drawing_id": new_drawing.drawing_id,
            "file_location": f"Processed {len(attachments)} file(s)"
            }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating drawing: {e}")
        return jsonify({"error": "Failed to create drawing"}), 500

    
# Route to delete a drawing
@drawings_bp.route('/delete/<string:drawing_id>', methods=['DELETE'])
# @jwt_required()
def delete_drawing(drawing_id):
    """
    Deletes a drawing record from the database.
    """
    drawing = Drawings.query.get(drawing_id)
    if not drawing:
        return jsonify({"error": "Drawing not found"}), 404
    
    try:
        uploads = Upload_Files.query.filter_by(drawing_id=drawing_id).all()
        for upload in uploads:
            db.session.delete(upload)
        db.session.commit()
        db.session.delete(drawing)
        db.session.commit()
        return jsonify({"message": "Drawing deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting drawing: {e}")
        return jsonify({"error": "Failed to delete drawing"}), 500
    

@drawings_bp.route('/update/<string:space_id>', methods=['PUT'])
# @jwt_required()
def update_drawing_by_space_id(space_id):
    """
    Updates a single drawing's metadata and files, identified by a drawing_id 
    in the body, constrained by the space_id in the URL.
    """
    
    # --- 1. Data Retrieval ---
    is_multipart = request.mimetype and 'multipart/form-data' in request.mimetype
    attachments = []
    files_to_delete = []
    data = {}
    drawing_id = None
    
    # ... (Data retrieval logic remains the same) ...
    if is_multipart:
        data = request.form
        drawing_id = data.get('drawing_id')
        attachments = request.files.getlist("uploads")
        
        # Parse files to delete
        files_to_delete_json = data.get('files_to_delete', '[]')
        try:
            files_to_delete = json.loads(files_to_delete_json)
            if not isinstance(files_to_delete, list):
                raise TypeError()
        except (json.JSONDecodeError, TypeError):
            return jsonify({"error": "Invalid format for files_to_delete. Must be a JSON array string."}), 400

    else: # application/json
        try:
            data = request.get_json()
            if data is not None:
                drawing_id = data.get('drawing_id')
        except:
            return jsonify({"error": "Invalid JSON body."}), 400
    
    # --- 2. Validation and Query ---
    if not drawing_id:
        return jsonify({"error": "A 'drawing_id' is required in the request body to identify the drawing to update."}), 400

    # 🚨 DEBUG LINE: Log the exact parameters used for the query
    logger.info(f"Attempting to update Drawing ID: '{drawing_id}' in Space ID: '{space_id}'")

    # 🛑 THE QUERY WHERE THE ERROR OCCURS 🛑
    drawing = Drawings.query.filter_by(drawing_id=drawing_id, space_id=space_id).first()
    
    if not drawing:
        # Returns 404 because the ID pair did not match a record.
        return jsonify({"error": f"Drawing ID '{drawing_id}' not found in Space ID '{space_id}'"}), 404

    # --- 3. Update Logic ---
    fields_updated = ('drawing_name' in data or 'description' in data)
    files_changed = attachments or files_to_delete
    
    # Apply metadata changes
    if 'drawing_name' in data:
        drawing.drawing_name = data['drawing_name']
        
    if 'description' in data:
        drawing.description = data['description']

    try:
        # Check if no changes were requested at all
        if not fields_updated and not files_changed:
            return jsonify({"message": "No metadata or files provided for update."}), 200

        # Handle File/Revision Updates if a file action occurred
        if files_changed:
            # Increment revision number
            drawing.revision_number = (drawing.revision_number or 0) + 1
            
            # Call your file utility function
            update_drawing_files(attachments, drawing.drawing_id, files_to_delete)
        
        # Commit all changes 
        db.session.commit()
        
        # --- 4. Success Response ---
        message = "Drawing updated successfully"
        if fields_updated and files_changed:
             message = "Drawing metadata and files updated successfully"
        elif files_changed:
             message = "Drawing files updated successfully (no metadata changed)"
        
        return jsonify({
            "message": message,
            "drawing_id": drawing.drawing_id,
            "new_revision": drawing.revision_number,
            "files_added": len(attachments),
            "files_deleted": len(files_to_delete)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating drawing/files for ID {drawing_id} in space {space_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update drawing or files"}), 500

@drawings_bp.route('/delete/space/<string:space_id>', methods=['DELETE'])   
# @jwt_required() 
def delete_drawing_by_space_id(space_id):
    """
    Deletes a specific drawing record and its associated file records.
    Identifies the drawing by 'drawing_id' provided in the form-data body,
    constrained by 'space_id' in the URL path.
    """
    try:
        # 🚨 KEY CHANGE: Use request.form to retrieve data sent as form-data
        data = request.form
        drawing_id = data.get('drawing_id')
    except Exception:
        # This generic except block is kept, though request.form is less prone to parsing errors than get_json()
        return jsonify({"error": "Invalid or missing form data."}), 400

    if not drawing_id:
        return jsonify({"error": "A 'drawing_id' is required in the body to identify the drawing to delete."}), 400

    try:
        # 1. Find the drawing using both drawing_id and space_id
        drawing = Drawings.query.filter_by(drawing_id=drawing_id, space_id=space_id).first()
        
        if not drawing:
            # Returns 404 if drawing is not found OR if it doesn't belong to the space
            return jsonify({"error": f"Drawing ID '{drawing_id}' not found in Space ID '{space_id}'"}), 404
        
        # 2. Delete associated file records (Upload_Files)
        uploads = Upload_Files.query.filter_by(drawing_id=drawing_id).all()
        for upload in uploads:
            # NOTE: Include physical file deletion logic here if necessary
            db.session.delete(upload)
            db.session.commit()
            
        # 3. Delete the main Drawing record
        db.session.delete(drawing)
        
        # 4. Commit all deletions (files and drawing) in one transaction
        db.session.commit()
        
        return jsonify({"message": f"Drawing ID {drawing_id} successfully deleted from space {space_id}"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting drawing {drawing_id} in space {space_id}: {e}")
        return jsonify({"error": "Failed to delete drawing"}), 500