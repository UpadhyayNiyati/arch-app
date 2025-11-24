from flask import Blueprint , jsonify , request , current_app
from models import db , Inspiration , Upload_Files
from .upload_files_routes import upload_inspiration_files , update_inspiration_files
import logging
import json
import os
from datetime import datetime , timedelta
from sqlalchemy.exc import IntegrityError 
from flask_cors import CORS
from werkzeug.datastructures import FileStorage
import requests
import io

inspiration_bp = Blueprint('Inspiration' , __name__)

CORS(inspiration_bp)

def download_url_to_filestorage(url, filename="external_image"):
    """Downloads an image from a URL and converts it into a FileStorage object."""
    # (Implementation copied from previous answer)
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        ext = '.' + content_type.split('/')[-1] if 'image/' in content_type else '.jpg'
        
        file_data = io.BytesIO(response.content)
        
        return FileStorage(
            stream=file_data,
            filename=filename + ext,
            content_type=content_type,
            name='uploads'
        )
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error downloading external URL {url}: {e}")
        return None
    
def _serialize_inspiration(inspiration):
    """Helper function to serialize an Inspiration object into a dictionary, including its files."""
    insp_dict = {
        "inspiration_id": inspiration.inspiration_id,
        "space_id": inspiration.space_id,
        "title": inspiration.title,
        "description": inspiration.description,
        "tags": inspiration.tags.split(',') if inspiration.tags else [],
        "files": []
    }
    
    # Fetch and serialize associated files
    find_uploads = db.session.query(Upload_Files).filter(Upload_Files.inspiration_id == inspiration.inspiration_id).all()
    for file in find_uploads:
        insp_dict["files"].append({
            "file_id": file.file_id,
            "filename": file.filename,
            "file_path": file.file_path,
            "file_size": file.file_size
        })
    return insp_dict

@inspiration_bp.route('/get', methods=['GET'])
def get_all_inspirations():
    """
    Retrieve All Inspirations
    ---
    tags:
      - Inspirations
    responses:
      200:
        description: A list of all inspiration records.
        schema:
          type: array
          items:
            properties:
              inspiration_id: {type: string}
              space_id: {type: string}
              title: {type: string}
              description: {type: string}
              tags: {type: array, items: {type: string}}
              files: 
                type: array
                items:
                  properties:
                    file_id: {type: integer}
                    filename: {type: string}
                    file_path: {type: string}
                    file_size: {type: integer}
      500:
        description: Failed to retrieve inspiration due to server error.
        schema:
          properties:
            error: {type: string}
    """
    try:
        all_insp = []
        inspirations = Inspiration.query.all()

        for insp in inspirations:
            insp_dict = {
                "isnpiration_id":insp.inspiration_id,
                "space_id": insp.space_id,
                "title": insp.title,
                "description": insp.description,
                "tags": insp.tags.split(',') if insp.tags else [],
                "files":[]
            }

            find_uploads = db.session.query(Upload_Files).filter(Upload_Files.inspiration_id == insp.inspiration_id).all()
            for file in find_uploads:
                file_dict = {
                    "file_id":file.file_id , 
                    "filename":file.filename,
                    "file_path":file.file_path,
                    "file_size":file.file_size
                }
                insp_dict["files"].append(file_dict)
            all_insp.append(insp_dict)
        return jsonify(all_insp) , 200
    except Exception as e:
        # db.session.rollback()
        return jsonify({"error": "Failed to retrieve inspiration: " + str(e)}), 500
    


@inspiration_bp.route('/get/<string:inspiration_id>', methods=['GET'])
def get_inspiration_by_id(inspiration_id):
    """
    Get Inspiration by ID
    ---
    tags:
      - Inspirations
    parameters:
      - name: inspiration_id
        in: path
        type: string
        required: true
        description: The ID of the inspiration record to retrieve.
    responses:
      200:
        description: The inspiration record.
        schema:
          properties:
            inspiration_id: {type: string}
            space_id: {type: string}
            title: {type: string}
            description: {type: string}
            tags: {type: array, items: {type: string}}
            files: 
              type: array
              items:
                properties:
                  file_id: {type: integer}
                  filename: {type: string}
                  file_path: {type: string}
                  file_size: {type: integer}
      404:
        description: Inspiration not found.
        schema:
          properties:
            error: {type: string}
      500:
        description: Internal server error.
        schema:
          properties:
            error: {type: string}
    """
    try:
        inspiration = Inspiration.query.filter_by(inspiration_id = inspiration_id).first_or_404(
            description = f"Inspiration with ID {inspiration_id} not found"
        )

        insp_dict = {
                "inspiration_id":inspiration.inspiration_id,
                "space_id": inspiration.space_id,
                "title": inspiration.title,
                "description": inspiration.description,
                "tags": inspiration.tags.split(',') if inspiration.tags else [],
                "files":[]
        } 
        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.inspiration_id == inspiration.inspiration_id).all()

        for file in find_uploads:
            file_dict = {
                "file_id" : file.file_id , 
                "filename" : file.filename , 
                "file_path" : file.file_path , 
                "file_size":file.file_size
            }
            insp_dict["files"].append(file_dict)
        return jsonify(insp_dict) , 200
    except Exception as e:
        return jsonify({"error":"Cannot retrieve by id"}) , 500
    
@inspiration_bp.route('/get/space/<string:space_id>', methods=['GET'])
def get_inspirations_by_space_id(space_id):
    """
    Get Inspirations by Space ID
    ---
    tags:
      - Inspirations
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
        description: The ID of the space to filter inspirations by.
    responses:
      200:
        description: A list of inspiration records for the given space.
        schema:
          type: array
          items:
            properties:
              inspiration_id: {type: string}
              space_id: {type: string}
              title: {type: string}
              description: {type: string}
              tags: {type: array, items: {type: string}}
              files: 
                type: array
                items:
                  properties:
                    file_id: {type: integer}
                    filename: {type: string}
                    file_path: {type: string}
                    file_size: {type: integer}
      404:
        description: No inspiration records found for the space ID.
        schema:
          properties:
            message: {type: string}
      500:
        description: Failed to retrieve inspiration due to server error.
        schema:
          properties:
            error: {type: string}
    """
    try:
        all_insp = []
        # 1. Query by space_id
        inspirations = Inspiration.query.filter_by(space_id=space_id).all()

        if not inspirations:
            return jsonify({"message": f"No inspiration records found for Space ID '{space_id}'"}), 404

        for insp in inspirations:
            insp_dict = {
                "inspiration_id": insp.inspiration_id,
                "space_id": insp.space_id,
                "title": insp.title,
                "description": insp.description,
                "tags": insp.tags.split(',') if insp.tags else [],
                "files": []
            }

            # 2. Fetch associated files
            find_uploads = db.session.query(Upload_Files).filter(Upload_Files.inspiration_id == insp.inspiration_id).all()
            for file in find_uploads:
                insp_dict["files"].append({
                    "file_id": file.file_id,
                    "filename": file.filename,
                    "file_path": file.file_path,
                    "file_size": file.file_size
                })
            all_insp.append(insp_dict)
            
        return jsonify(all_insp), 200
    except Exception as e:
        # current_app.logger.error(f"Error retrieving inspirations for space {space_id}: {e}")
        return jsonify({"error": "Failed to retrieve inspiration: " + str(e)}), 500
    
# The blueprint name is assumed to be defined elsewhere: inspiration_bp = Blueprint('Inspiration', __name__)

@inspiration_bp.route('/post', methods=['POST'])
def create_inspiration():
    """
    Creates a new inspiration entry, stores files, and handles the transaction atomically.
    ---
    tags:
      - Inspirations
    description: Create a new inspiration with optional file uploads or external image URL.
    consumes:
      - multipart/form-data
    parameters:
      - name: space_id
        in: formData
        type: string
        required: true
      - name: title
        in: formData
        type: string
        required: false
      - name: description
        in: formData
        type: string
        required: false
      - name: tags
        in: formData
        type: string
        required: false
        description: Comma-separated tags string or JSON array string.
      - name: uploads
        in: formData
        type: file
        required: false
        description: File attachments.
      - name: url
        in: formData
        type: string
        required: false
        description: External image URL to download.
    responses:
      201:
        description: Inspiration and file uploaded successfully.
      400:
        description: Validation error (missing data or file/URL), or data integrity error.
    """
    data = request.form
    attachments = request.files.getlist("uploads")
    external_url = data.get('url')
    
    # Define fields required from the form data
    required_data_fields = ['space_id']
    
    # 1. FIX VALIDATION: Check required fields AND attachments
    if not all(field in data for field in required_data_fields):
        # Corrected error message to reflect the fields checked
        return jsonify({"error": f"Missing required fields ({', '.join(required_data_fields)}) and/or file attachments"}), 400
    
    has_uploaded_files = bool(attachments) and attachments[0].filename != ''
    has_url = bool(external_url)
    
    if not has_uploaded_files and not has_url:
        return jsonify({"error": "Must provide either file attachments (uploads) OR an external URL."}), 400
    
    
    # 3. Source Processing: Consolidate all images (uploads + download) into one list
    files_to_process = []
    # message_detail = "File uploaded" # Default message

    if has_uploaded_files:
        files_to_process.extend(attachments)
    
    if has_url:
        downloaded_file = download_url_to_filestorage(
            external_url, 
            filename=data.get('title', 'external_insp')
        )
        if downloaded_file:
            files_to_process.append(downloaded_file)
            # message_detail = f"URL downloaded and stored ({external_url})"
        else:
            return jsonify({"error": "Failed to download image from the provided URL."}), 400

    # 2. FIX TAGS DATA TYPE: Form data comes as strings.
    # If the database expects a comma-separated string, we can use the form data directly.
    tags_str = data.get('tags')
    
    # 3. FIX MODEL: 'url' is assumed to be nullable since it's not provided
    new_inspiration = Inspiration(
        space_id = data.get('space_id'),
        title = data.get('title'),
        # url is omitted, requires DB schema to be nullable
        description=data.get('description'),
        tags=tags_str
    )

    try:
        db.session.add(new_inspiration)
        
        # ✅ FIX: Use FLUSH to get the ID without committing the transaction.
        db.session.flush() 
        
        # Now the helper can safely use new_inspiration.inspiration_id
        # Assuming upload_inspiration_files is defined and handles child record creation
        upload_inspiration_files(files_to_process, new_inspiration.inspiration_id)
        
        # ✅ FIX: Perform ONE single, atomic commit for both the Inspiration record and file records.
        db.session.commit()
        
        return jsonify({
            "message": "Inspiration and file uploaded successfully",
            "inspiration_id": new_inspiration.inspiration_id,
            "file_location": f"Processed {len(attachments)} file(s)"
        }), 201
        
    except IntegrityError:
        # Catch database constraints failure (e.g., NOT NULL violation on 'url' or invalid 'space_id')
        db.session.rollback()
        return jsonify({"error": "Data integrity error: Check database constraints (e.g., space_id or nullable fields)"}), 400
    except Exception as e:
        db.session.rollback()
        # Log the detailed error (e.g., I/O error during file upload) for server-side debugging
        # current_app.logger.error(f"Error creating inspiration: {e}") 
        current_app.logger.error(f"Error creating inspiration: {e}", exc_info=True) 
        return jsonify({"error": "Failed to create inspiration"}), 500
        # return jsonify({"error": "Failed to create inspiration"}), 500
    
# @inspiration_bp.route('/update_inspirations/<string:inspiration_id>', methods=['PUT'])
# def update_inspiration(inspiration_id):
#     inspiration = Inspiration.query.get(inspiration_id)
#     if not inspiration:
#         return jsonify({"error": "Inspiration not found"}), 404

#     # --- 1. HANDLE REQUEST DATA ---
#     # Expect text fields via request.form and files via request.files
#     data = request.form
#     files = request.files.getlist('uploads')  # Assuming file input name is 'files'
    
#     # Files to delete are usually sent as a JSON string within the form data
#     files_to_delete_json = data.get('files_to_delete', '[]')
#     try:
#         files_to_delete = json.loads(files_to_delete_json)
#     except json.JSONDecodeError:
#         return jsonify({"error": "files_to_delete must be a valid JSON array string."}), 400

#     # --- 2. UPDATE INSPIRATION METADATA (Title, Description, Tags) ---
#     updated_fields = {}
#     tags_str = None
#     if 'tags' in data:
#         # Assuming 'tags' is sent as a comma-separated string or a JSON array string
#         if isinstance(data['tags'], str):
#             # Try to parse as JSON list, fallback to raw string
#             try:
#                 tags_list = json.loads(data['tags'])
#                 if isinstance(tags_list, list):
#                     tags_str = ','.join(tags_list)
#                 else:
#                     tags_str = data['tags']
#             except json.JSONDecodeError:
#                 tags_str = data['tags']

#     try:
#         # Update text fields (Title, Description)
#         # inspiration.title = data.get('title', inspiration.title)
#         # inspiration.description = data.get('description', inspiration.description)
#         # inspiration.tags = tags_str if tags_str is not None else inspiration.tags

#         if 'title' in data and data['title'] != inspiration.title:
#             updated_fields['title'] = {
#                 'old': inspiration.title,
#                 'new': data['title']
#             }
#             inspiration.title = data['title']

#         # Update Description, tracking changes
#         if 'description' in data and data['description'] != inspiration.description:
#             updated_fields['description'] = {
#                 'old': inspiration.description,
#                 'new': data['description']
#             }
#             inspiration.description = data['description']

#         # Update Tags, tracking changes
#         if tags_str is not None and tags_str != inspiration.tags:
#             # Prepare old and new tag lists for cleaner response
#             old_tags = inspiration.tags.split(',') if inspiration.tags else []
#             new_tags = tags_str.split(',') if tags_str else []
            
#             updated_fields['tags'] = {
#                 'old': old_tags,
#                 'new': new_tags
#             }
#             inspiration.tags = tags_str

#         file_change_summary = {}

#         if files or files_to_delete:
#             # Assumes update_inspiration_files handles I/O and DB commits for files
#             update_inspiration_files(files, inspiration_id, files_to_delete)
            
#             # Populate file change summary
#             if files:
#                 file_change_summary['files_added'] = len(files)
#             if files_to_delete:
#                 file_change_summary['files_deleted_ids'] = files_to_delete

#         # Update Tags, tracking changes
#         # if tags_str is not None and tags_str != inspiration.tags:
#         #     inspiration.tags = tags_str
#         #     # Store tags as a list in the response for client convenience
#         #     updated_fields['tags'] = tags_str.split(',') if tags_str else []

#         if files or files_to_delete:
#             # Assumes update_inspiration_files handles I/O and DB commits for files
#             update_inspiration_files(files, inspiration_id, files_to_delete)
            
#             # Populate file change summary
#             if files:
#                 file_change_summary['files_added'] = len(files)
#             if files_to_delete:
#                 file_change_summary['files_deleted_ids'] = files_to_delete

        
#         # --- 3. CALL FILE UPDATE HANDLER ---
#         # The update_inspiration_files function handles DB session/commit/rollback for files
#         # update_inspiration_files(files, inspiration_id, files_to_delete)
        
#         # We need a final commit for the text changes if update_inspiration_files didn't commit everything
#         # Since update_inspiration_files commits at the end, we can assume the session is clean/committed.
        
#         # If the file handler succeeds and commits, we commit text changes here too (safe practice)
#         db.session.commit()
#         # updated_inspiration = Inspiration.query.get(inspiration_id)
        
#         # return jsonify({"inspiration_id": str(inspiration_id),
#                         # "message": "Inspiration updated successfully.",
#                         # "metadata_changes": updated_fields
#                         # }), 200

#         response_data = {
#             "inspiration_id": str(inspiration_id),
#             "message": "Inspiration updated successfully.",
#             "metadata_changes": updated_fields # Only includes fields that were actually changed
#         }
        
#         # Add file change summary if any file action occurred
#         if file_change_summary:
#             response_data['file_changes'] = file_change_summary
        
#         # If no changes were requested or detected, change the message
#         if not updated_fields and not file_change_summary:
#              response_data["message"] = "Inspiration found, but no changes were applied."

#         # Return the concise response
#         return jsonify(response_data), 200
        
#     except Exception as e:
#         # Since file update might raise an exception, we catch it here.
#         db.session.rollback()
#         logging.exception(f"Failed to update inspiration {inspiration_id}: {str(e)}")
#         return jsonify({"error": f"Failed to update inspiration: {str(e)}"}), 500


@inspiration_bp.route('/update_inspirations/<string:inspiration_id>', methods=['PUT'])
def update_inspiration(inspiration_id):
    """
    Updates a single inspiration record (metadata and/or files) by its ID.
    ---
    tags:
        - Inspirations
    parameters:
      - name: inspiration_id
        in: path
        type: string
        required: true
      - name: title
        in: formData
        type: string
        required: false
      - name: description
        in: formData
        type: string
        required: false
      - name: tags
        in: formData
        type: string
        required: false
      - name: uploads
        in: formData
        type: file
        required: false
      - name: files_to_delete
        in: formData
        type: string
        required: false
        description: JSON array string of file_ids to delete (e.g., "[1, 2, 3]").
    responses:
      200:
        description: Inspiration updated successfully.
      400:
        description: Invalid JSON for files_to_delete.
      404:
        description: Inspiration not found.
    """
    inspiration = Inspiration.query.get(inspiration_id)
    if not inspiration:
        return jsonify({"error": "Inspiration not found"}), 404

    # --- 1. HANDLE REQUEST DATA ---
    data = request.form
    files = request.files.getlist('uploads') 
    
    files_to_delete_json = data.get('files_to_delete', '[]')
    try:
        files_to_delete = json.loads(files_to_delete_json)
        if not isinstance(files_to_delete, list):
             raise TypeError("Files to delete must be a list.")
    except (json.JSONDecodeError, TypeError):
        return jsonify({"error": "files_to_delete must be a valid JSON array string containing a list."}), 400

    # --- 2. UPDATE INSPIRATION METADATA (Title, Description, Tags) ---
    metadata_was_changed = False 
    tags_str = None
    
    if 'tags' in data:
        if isinstance(data['tags'], str):
            try:
                tags_list = json.loads(data['tags'])
                if isinstance(tags_list, list):
                    tags_str = ','.join(tags_list)
                else:
                    tags_str = data['tags']
            except json.JSONDecodeError:
                tags_str = data['tags']

    try:
        # --- A. Track and Apply Metadata Changes ---
        if 'title' in data and data['title'] != inspiration.title:
            inspiration.title = data['title']
            metadata_was_changed = True
        
        if 'description' in data and data['description'] != inspiration.description:
            inspiration.description = data['description']
            metadata_was_changed = True
        
        if tags_str is not None and tags_str != inspiration.tags:
            inspiration.tags = tags_str
            metadata_was_changed = True
            
        
        # --- B. Handle File Changes ---
        file_action_requested = files or files_to_delete
        
        if file_action_requested:
            # Call the helper function to handle I/O and DB updates for files
            update_inspiration_files(files, inspiration_id, files_to_delete) 

        
        # --- C. Commit & Full Response ---
        # Commit the metadata changes (file changes are typically committed inside the helper)
        db.session.commit()
        
        # 🔑 FIX: Re-read the object to get the latest file relationships
        updated_inspiration = Inspiration.query.get(inspiration_id) 
        
        response_data = {
            "message": "Inspiration updated successfully.",
            "inspiration": _serialize_inspiration(updated_inspiration) # Returns the full data of the SINGLE updated record
        }
        
        if not metadata_was_changed and not file_action_requested:
            response_data["message"] = "Inspiration found, but no changes were applied."

        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        logging.exception(f"Failed to update inspiration {inspiration_id}: {str(e)}")
        return jsonify({"error": f"Failed to update inspiration: {str(e)}"}), 500

 
    
@inspiration_bp.route('/update/space/<string:space_id>', methods=['PUT'])
def update_inspirations_by_space_id_with_files(space_id):
    """
    Updates metadata for ALL inspiration records associated with a space_id
    and/or updates files for a SINGLE specified inspiration_id within that space.
    ---
    tags:
        - Inspirations
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
      - name: title
        in: formData
        type: string
        required: false
        description: Bulk update for all inspirations in the space.
      - name: inspiration_id
        in: formData
        type: string
        required: false
        description: REQUIRED if 'uploads' or 'files_to_delete' are provided.
    responses:
      200:
        description: Update successful.
    """
    data = request.form
    files = request.files.getlist('uploads')
    
    # Get the specific inspiration_id for file handling
    inspiration_id = data.get('inspiration_id')

    # Files to delete handling (same as before)
    files_to_delete_json = data.get('files_to_delete', '[]')
    try:
        files_to_delete = json.loads(files_to_delete_json)
        if not isinstance(files_to_delete, list):
             raise TypeError("Files to delete must be a list.")
    except (json.JSONDecodeError, TypeError):
        return jsonify({"error": "files_to_delete must be a valid JSON array string."}), 400

    # Define fields for bulk metadata update
    updatable_metadata_fields = ['title', 'description', 'tags']
    updates_received = {field: data[field] for field in updatable_metadata_fields if field in data}

    # Determine if a file action is requested
    file_action_requested = files or files_to_delete

    if not updates_received and not file_action_requested:
        return jsonify({"message": "No valid fields or file actions provided for update."}), 200

    try:
        # 1. Query ALL inspirations for the space ID
        inspirations = Inspiration.query.filter_by(space_id=space_id).all()
        
        if not inspirations:
            return jsonify({"message": f"No inspiration records found for Space ID '{space_id}'"}), 404

        # --- A. BULK METADATA UPDATE ---
        inspirations_updated_count = 0
        if updates_received:
            # Apply bulk metadata updates (logic remains the same)
            for insp in inspirations:
                for key, value in updates_received.items():
                    if key == 'tags' and isinstance(value, str):
                        setattr(insp, key, value) 
                    else:
                        setattr(insp, key, value)
                inspirations_updated_count += 1

        # --- B. SPECIFIC FILE UPDATE ---
        files_action_message = ""
        if file_action_requested:
            if not inspiration_id:
                 return jsonify({"error": "File operations require a specific 'inspiration_id' in the form data."}), 400
            
            target_inspiration = next((i for i in inspirations if str(i.inspiration_id) == inspiration_id), None)
            
            if not target_inspiration:
                return jsonify({"error": f"Inspiration ID '{inspiration_id}' not found in Space ID '{space_id}'."}), 404
            
            # Call the dedicated file update handler
            update_inspiration_files(files, inspiration_id, files_to_delete)
            
            files_action_message = f"File changes applied to Inspiration ID {inspiration_id} ({len(files)} new file(s), {len(files_to_delete)} deleted)."

        # 3. Commit the changes
        db.session.commit()
        updated_inspirations = Inspiration.query.filter_by(space_id=space_id).all()
        serialized_inspirations = [_serialize_inspiration(insp) for insp in updated_inspirations]
        
        # 🚨 KEY CHANGE: Update the success message based on what was actually updated.
        if inspirations_updated_count == 0 and file_action_requested:
             # Case: Only files were updated
             final_message = f'Files updated successfully.' + files_action_message
        elif inspirations_updated_count > 0 and not file_action_requested:
             # Case: Only metadata was updated
             final_message = f'Metadata updated for {inspirations_updated_count} inspirations.'
        else:
             # Case: Both metadata and files were updated
             final_message = f'Metadata updated for {inspirations_updated_count} inspirations. ' + files_action_message

        return jsonify({
            'message': final_message,
            'inspirations_updated': inspirations_updated_count,
            'files_action_target_id': inspiration_id if file_action_requested else None , 
            'inspirations' : serialized_inspirations
        }), 200

    except Exception as e:
        db.session.rollback()
        # logging.exception(f"Error updating inspirations for space {space_id}: {e}")
        return jsonify({"error": f"A database error occurred during the update: {str(e)}"}), 500
    
@inspiration_bp.route('/del_inspirations/<string:inspiration_id>', methods=['DELETE'])
def delete_inspiration(inspiration_id):
    """
    Deletes a single inspiration record and its associated files by ID.
    ---
    tags : 
        - Inspirations
    parameters:
      - name: inspiration_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Inspiration and associated files deleted successfully.
      404:
        description: Inspiration not found.
    """
    inspiration = Inspiration.query.get(inspiration_id) 
    if not inspiration:
        return jsonify({"error": "Inspiration not found"}), 404
    try:
        uploads = Upload_Files.query.filter_by(inspiration_id=inspiration_id).all()
        for upload in uploads:
            db.session.delete(upload)
        db.session.commit()
        db.session.delete(inspiration)
        db.session.commit()
        return jsonify({"message": "Inspiration and associated files deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting inspiration {inspiration_id}: {e}")
        return jsonify({"error": "Failed to delete inspiration"}), 500   
    
@inspiration_bp.route('/delete/space/<string:space_id>', methods=['DELETE'])
def delete_inspirations_by_space_id(space_id):
    """
    Deletes all inspiration records and their associated files for a given space_id.
    ---
    tags:
        - Inspirations
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Successful deletion summary.
      404:
        description: No inspiration records found for the space ID.
    """
    try:
        inspirations = Inspiration.query.filter_by(space_id=space_id).all()
        
        if not inspirations:
            return jsonify({"message": f"No inspiration records found for Space ID '{space_id}' to delete."}), 404

        insp_deleted_count = 0
        files_deleted_count = 0
        
        for insp in inspirations:
            insp_id = insp.inspiration_id
            
            # 2a. Delete associated file records and physical files FIRST
            uploads = Upload_Files.query.filter_by(inspiration_id=insp_id).all()
            
            for upload in uploads:
                # --- START Physical File Deletion Logic ---
                file_path = upload.file_path # Assuming file_path stores the full path or relative path
                
                # Construct the full path if file_path is relative
                # full_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path) 
                
                # Assuming file_path is the correct server path for demonstration:
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Catch case where file is already gone but record exists
                # NOTE: You may need a logger here to track failures
                # --- END Physical File Deletion Logic ---
                
                db.session.delete(upload)
                db.session.commit()
                files_deleted_count += 1
            
            # 2b. Delete the main Inspiration record
            db.session.delete(insp)
            insp_deleted_count += 1
            
        # 3. Commit all staged deletions in one transaction
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully deleted {insp_deleted_count} inspiration(s) and {files_deleted_count} associated file record(s) from space {space_id}.",
            "inspirations_deleted": insp_deleted_count,
            "files_records_deleted": files_deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        # Log the error for debugging
        # current_app.logger.error(f"Error deleting inspirations in space {space_id}: {e}", exc_info=True)
        return jsonify({"error": f"A server error occurred during deletion: {str(e)}"}), 500