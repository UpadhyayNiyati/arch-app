from flask import Blueprint, request, jsonify, current_app
from models import Upload_Files, db, Drawings  # Assuming your models are in 'your_app_module'
import logging
from .upload_files_routes import upload_drawing_files , update_drawing_files
from datetime import datetime , timedelta
import os

drawings_bp = Blueprint('drawings_bp', __name__)

# Route to get all drawings
@drawings_bp.route('/get', methods=['GET'])
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

# @drawings_bp.route('/get_by_id', methods=['GET'])
# def get_drawings_by_id():
#     """
#     Retrieves all drawings from the database, with their associated file details.
#     """
#     try:
#         all_drawings = []  # The final list to hold all unique drawing objects
#         drawings = Drawings.query.all()
        
#         for drawing in drawings:
#             # Create a dictionary for the current drawing
#             drawing_dict = {
#                 "drawing_id": drawing.drawing_id,
#                 "space_id": drawing.space_id,
#                 "drawing_name": drawing.drawing_name,
#                 "revision_number": drawing.revision_number,
#                 "uploaded_at": drawing.uploaded_at.isoformat(),
#                 "files": []  # Initialize a list to hold the files for THIS drawing
#             }
            
#             # Query for the files associated with the current drawing ID
#             find_uploads = db.session.query(Upload_Files).filter(Upload_Files.drawing_id == drawing.drawing_id).all()
            
#             # Loop through the files found for this drawing
#             for file in find_uploads:
#                 file_dict = {
#                     "file_id": file.file_id,
#                     "filename": file.filename,
#                     "file_path": file.file_path,
#                     "file_size": file.file_size,
#                     "recorded_at_timezone": file.record_time_according_to_timezone.strftime("%a, %d %b %Y %H:%M:%S %Z") if file.record_time_according_to_timezone else None
#                 }
                
#                 drawing_dict.append({"file":file_dict}) # Append the file to the drawing's file list
                
            
#             # CRITICAL FIX: Append the completed drawing dictionary to the main list
#             # only after the inner loop is finished.
#             all_drawings.append(drawing_dict)
            
#         return jsonify(all_drawings), 200
        
#     except Exception as e:
#         logging.exception(f"Error retrieving drawings: {e}")
#         return jsonify({"error": str(e)}), 500

# Route to get a single drawing by ID
# @drawings_bp.route('get/<string:drawing_id>', methods=['GET'])
# def get_drawing(drawing_id):
#     """
#     Retrieves a single drawing by its drawing_id.
#     """
#     drawing = Drawings.query.get(drawing_id)
#     if drawing:
#         return jsonify({
#             "drawing_id": drawing.drawing_id,
#             "space_id": drawing.space_id,
#             "drawing_name": drawing.drawing_name,
#             # "drawing_url": drawing.drawing_url,
#             "revision_number": drawing.revision_number,
#             "uploaded_at": drawing.uploaded_at.isoformat(),
#             'files' : []
#         }), 200
    

#     return jsonify({"error": "Drawing not found"}), 404
@drawings_bp.route('/get/<string:drawing_id>', methods=['GET'])
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

# Route to create a new drawing
@drawings_bp.route('/post', methods=['POST'])
def create_drawing():
    """
    Creates a new drawing entry in the database.
    """
    data = request.form
    
    if not data or 'space_id' not in data or 'drawing_name' not  in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    # if file and allowed_file(file.filename):
    #  # Secure the filename to prevent directory traversal attacks
    # filename = secure_filename(file.filename)
    # file_path = os.path.join(upload_folder, filename)
    attachments = request.files.getlist("uploads")

    new_drawing = Drawings(
        space_id=data.get('space_id'),
        drawing_name=data.get('drawing_name'),
        
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

# Route to update an existing drawing
# @drawings_bp.route('/api/drawings/<string:drawing_id>', methods=['PUT'])
# def update_drawing(drawing_id):
#     """
#     Updates the drawing_url and increments the revision_number for a drawing.
#     """
#     drawing = Drawings.query.get(drawing_id)
#     if not drawing:
#         return jsonify({"error": "Drawing not found"}), 404
    
#     data = request.get_json()
#     if not data or 'drawing_url' not in data:
#         return jsonify({"error": "Missing required 'drawing_url' field"}), 400

#     try:
#         # Update the drawing_url and increment revision_number
#         drawing.drawing_url = data['drawing_url']
#         drawing.revision_number += 1
#         db.session.commit()
#         return jsonify({
#             "message": "Drawing updated successfully",
#             "drawing_id": drawing.drawing_id,
#             "new_revision": drawing.revision_number
#         }), 200
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error updating drawing: {e}")
#         return jsonify({"error": "Failed to update drawing"}), 500

# Route to update an existing drawing AND its associated files
from flask import jsonify, request, current_app
from datetime import datetime
import json
# Assuming 'db' is your SQLAlchemy object and 'Drawings' is your model
# from . import db # Adjust import based on your app structure
# from .models import Drawings # Adjust import based on your app structure
# Assuming update_drawing_files is defined elsewhere

# @drawings_bp.route('/update/<string:drawing_id>', methods=['PUT'])
# def update_drawing(drawing_id):
#     """
#     Updates a drawing's metadata and optionally updates its associated files.
#     The request can be multipart/form-data for file uploads or application/json for metadata updates.
#     """
#     drawing = Drawings.query.get(drawing_id)
#     if not drawing:
#         return jsonify({"error": "Drawing not found"}), 404

#     # Determine if it's a file update (multipart/form-data) or a metadata update (application/json)
#     is_multipart = request.mimetype and 'multipart/form-data' in request.mimetype
    
#     attachments = []
#     files_to_delete = []
    
#     if is_multipart:
#         data = request.form
#         attachments = request.files.getlist("uploads")
        
#         # files_to_delete should be a JSON array in the form data
#         files_to_delete_json = data.get('files_to_delete', '[]')
#         try:
#             # Safely parse the JSON array of file IDs to delete
#             files_to_delete = json.loads(files_to_delete_json)
#         except json.JSONDecodeError:
#             return jsonify({"error": "Invalid format for files_to_delete"}), 400

#         # Optional: Update drawing metadata from form data if provided
#         if 'drawing_name' in data:
#             drawing.drawing_name = data['drawing_name']

#     else: # application/json for metadata updates only
#         data = request.get_json()
        
#         # In a JSON-only update, we only check for drawing_name metadata
#         if data and 'drawing_name' in data:
#             drawing.drawing_name = data['drawing_name']
            
#         # JSON requests are not expected to contain files for upload/delete
#         # If you need to handle file deletions via JSON, you'd add that logic here, 
#         # but files_to_delete must be initialized correctly.

#     try:
#         # --- Metadata Update (handled above based on request type) ---

#         # 1. Handle File Updates (Delete old, Upload new)
#         # This block now handles file changes from the multipart request.
#         if attachments or files_to_delete:
            
#             # If files are added or deleted, it usually signifies a new revision of the main drawing.
#             # We move the revision increment here, as it's directly tied to a file change.
#             if attachments or files_to_delete:
#                  drawing.revision_number = (drawing.revision_number or 0) + 1
            
#             # Assuming a simple UTC time for the file record update.
#             # localized_time = datetime.utcnow() 
#             update_drawing_files(attachments, drawing_id, files_to_delete)
        
#         # 2. Commit Drawing Metadata and File record changes
#         db.session.commit()
        
#         return jsonify({
#             "message": "Drawing updated successfully",
#             "drawing_id": drawing.drawing_id,
#             "new_revision": drawing.revision_number,
#             "files_added": len(attachments),
#             "files_deleted": len(files_to_delete)
#         }), 200
        
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error updating drawing/files: {e}")
#         return jsonify({"error": "Failed to update drawing or files"}), 500


    
# Route to delete a drawing
# @drawings_bp.route('/delete/<string:drawing_id>', methods=['DELETE'])
# def delete_drawing(drawing_id):
#     """
#     Deletes a drawing record from the database.
#     """
#     drawing = Drawings.query.get(drawing_id)
#     if not drawing:
#         return jsonify({"error": "Drawing not found"}), 404
    
#     try:
#         db.session.delete(drawing)
#         db.session.commit()
#         return jsonify({"message": "Drawing deleted successfully"}), 200
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error deleting drawing: {e}")
#         return jsonify({"error": "Failed to delete drawing"}), 500
    



# @drawings_bp.route('/delete/<string:drawing_id>', methods=['DELETE'])
# def delete_drawing(drawing_id):
#     drawing = Drawings.query.get(drawing_id)
#     if not drawing:
#         return jsonify({"error": "Drawing not found"}), 404
    
#     try:
#         # 1. FIND ALL CHILD RECORDS
#         files_to_delete = Upload_Files.query.filter_by(drawing_id=drawing_id).all()
        
#         for file_record in files_to_delete:
#             # 2. DELETE PHYSICAL FILE (IMPORTANT: Implement/import this helper)
#             # You need a function like this for disk cleanup
#             # delete_physical_file_by_path(file_record.file_path)
            
#             # 3. DELETE CHILD RECORD FROM DB
#             db.session.delete(file_record)
            
#         # 4. DELETE PARENT RECORD ONLY AFTER ALL CHILDREN ARE GONE
#         db.session.delete(drawing)
        
#         # 5. COMMIT THE TRANSACTION
#         db.session.commit()
        
#         return jsonify({"message": "Drawing and associated files deleted successfully"}), 200
        
#     except Exception as e:
#         # Rollback ensures no partial deletions occur if any step fails
#         db.session.rollback()
#         current_app.logger.error(f"Error deleting drawing and files for ID {drawing_id}: {e}")
#         return jsonify({"error": "Failed to delete drawing and associated files"}), 500

# @drawings_bp.route('/delete/<string:drawing_id>', methods=['DELETE'])
# def delete_drawing(drawing_id):
#     # ... (Drawing not found check remains the same) ...
#     drawing = Drawings.query.get(drawing_id)
#     if not drawing:
#         return jsonify({"error": "Drawing not found"}), 404
        
#     deleted_files_count = 0
    
#     try:
#         # 1. DELETE RECORDS FROM ALL DIRECT CHILD TABLES (including upload_files)
        
#         # --- A. Delete from Upload_Files (Your existing logic) ---
#         files_to_delete = Upload_Files.query.filter_by(drawing_id=drawing_id).all()
#         for file_record in files_to_delete:
#             # Delete physical file
#             try:
#                 if os.path.exists(file_record.file_path):
#                     os.remove(file_record.file_path)
#             except OSError as e:
#                 current_app.logger.warning(f"Warning: Could not delete physical file {file_record.file_path}: {e}")
            
#             # Delete DB record
#             db.session.delete(file_record)
#             deleted_files_count += 1
            
#         # --- B. DELETE RECORDS FROM THIRD CHILD TABLE (e.g., Drawing_Revisions) ---
#         # ⚠️ This is the likely missing step causing your error ⚠️
        
#         # Hypothetical model: Drawing_Revisions
#         revisions_to_delete = Drawing_Revisions.query.filter_by(drawing_id=drawing_id).all()
#         for revision in revisions_to_delete:
#              db.session.delete(revision)
#              current_app.logger.info(f"Deleted related revision record: {revision.id}")

#         # 2. DELETE PARENT DRAWING RECORD 
#         db.session.delete(drawing)
        
#         # 3. COMMIT THE TRANSACTION
#         db.session.commit()
        
#         return jsonify({
#             "message": "Drawing and associated data deleted successfully",
#             "files_deleted": deleted_files_count
#         }), 200
        
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error deleting drawing and files for ID {drawing_id}: {e}")
#         return jsonify({"error": "Failed to delete drawing and associated files"}), 500