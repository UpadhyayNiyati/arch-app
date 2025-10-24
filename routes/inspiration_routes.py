from flask import Blueprint , jsonify , request , current_app
from models import db , Inspiration , Upload_Files
from .upload_files_routes import upload_inspiration_files , update_inspiration_files
import logging
import json
import os
from datetime import datetime , timedelta
from sqlalchemy.exc import IntegrityError 

inspiration_bp = Blueprint('Inspiration' , __name__)

@inspiration_bp.route('/get', methods=['GET'])
def get_all_inspirations():
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

    # return jsonify([
    #     {
    #         "inspiration_id": insp.inspiration_id,
    #         "space_id": insp.space_id,
    #         "title": insp.title,
    #         # "url": insp.url,
    #         "description": insp.description,
    #         "tags": insp.tags.split(',') if insp.tags else []
    #     } for insp in inspirations
    # ]), 200

@inspiration_bp.route('/get/<string:inspiration_id>', methods=['GET'])
def get_inspiration_by_id(inspiration_id):
    # inspiration = Inspiration.query.get(inspiration_id)
    # if inspiration:
    #     return jsonify({
    #         "inspiration_id": inspiration.inspiration_id,
    #         "space_id": inspiration.space_id,
    #         "title": inspiration.title,
    #         # "url": inspiration.url,
    #         "description": inspiration.description,
    #         "tags": inspiration.tags.split(',') if inspiration.tags else []
    #     }), 200
    # return jsonify({"error": "Inspiration not found"}), 404
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
    
# @inspiration_bp.route('/post', methods=['POST'])
# def create_inspiration():
#     data = request.form
#     if not data or 'space_id' not in data or 'title' not in data or 'description' not in data or 'tags' not in data:
#         return jsonify({"error": "Missing required fields (space_id, title, url)"}), 400

#     # tags_str = ','.join(data.get('tags', [])) if isinstance(data.get('tags'), list) else data.get('tags', None)

#     # new_inspiration = Inspiration(
#     #     space_id=data['space_id'],
#     #     title=data['title'],
#     #     # url=data['url'],
#     #     description=data.get('description'),
#     #     tags=tags_str
#     # )
#     attachments = request.files.getlist("uploads")

#     new_inspiration = Inspiration(
#         space_id = data.get('space_id'),
#         title = data.get('title'),
#         description=data.get('description'),
#         tags=data.get('tags')
#     )

#     try:
#         db.session.add(new_inspiration)
#         db.session.flush() 
#         # db.session.commit()
#         upload_inspiration_files(attachments , new_inspiration.inspiration_id , )
#         db.session.commit()
#         return jsonify({
#             "message":"Inspiration and file uploaded successfully",
#             "inspiration_id":new_inspiration.inspiration_id , 
#             "file_location": f"Processed {len(attachments)} file(s)"
#         }) , 201
#         # return jsonify({"message": "Inspiration created successfully", "inspiration_id": new_inspiration.inspiration_id}), 201
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": "Failed to create inspiration"}), 500



# The blueprint name is assumed to be defined elsewhere: inspiration_bp = Blueprint('Inspiration', __name__)

@inspiration_bp.route('/post', methods=['POST'])
def create_inspiration():
    """
    Creates a new inspiration entry, stores files, and handles the transaction atomically.
    """
    data = request.form
    attachments = request.files.getlist("uploads")
    
    # Define fields required from the form data
    required_data_fields = ['space_id', 'title', 'description', 'tags']
    
    # 1. FIX VALIDATION: Check required fields AND attachments
    if not all(field in data for field in required_data_fields) or not attachments:
        # Corrected error message to reflect the fields checked
        return jsonify({"error": f"Missing required fields ({', '.join(required_data_fields)}) and/or file attachments"}), 400

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
        upload_inspiration_files(attachments, new_inspiration.inspiration_id)
        
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
    
@inspiration_bp.route('/update_inspirations/<string:inspiration_id>', methods=['PUT'])
# def update_inspiration(inspiration_id):
#     inspiration = Inspiration.query.get(inspiration_id)
#     if not inspiration:
#         return jsonify({"error": "Inspiration not found"}), 404

#     data = request.get_json()

#     tags_str = ','.join(data.get('tags', [])) if isinstance(data.get('tags'), list) else data.get('tags', None)

#     try:
#         inspiration.title = data.get('title', inspiration.title)
#         inspiration.url = data.get('url', inspiration.url)
#         inspiration.description = data.get('description', inspiration.description)
#         inspiration.tags = tags_str if tags_str is not None else inspiration.tags

#         db.session.commit()
#         return jsonify({"message": "Inspiration updated successfully"}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": "Failed to update inspiration"}), 500

def update_inspiration(inspiration_id):
    inspiration = Inspiration.query.get(inspiration_id)
    if not inspiration:
        return jsonify({"error": "Inspiration not found"}), 404

    # --- 1. HANDLE REQUEST DATA ---
    # Expect text fields via request.form and files via request.files
    data = request.form
    files = request.files.getlist('uploads')  # Assuming file input name is 'files'
    
    # Files to delete are usually sent as a JSON string within the form data
    files_to_delete_json = data.get('files_to_delete', '[]')
    try:
        files_to_delete = json.loads(files_to_delete_json)
    except json.JSONDecodeError:
        return jsonify({"error": "files_to_delete must be a valid JSON array string."}), 400

    # --- 2. UPDATE INSPIRATION METADATA (Title, Description, Tags) ---
    tags_str = None
    if 'tags' in data:
        # Assuming 'tags' is sent as a comma-separated string or a JSON array string
        if isinstance(data['tags'], str):
            # Try to parse as JSON list, fallback to raw string
            try:
                tags_list = json.loads(data['tags'])
                if isinstance(tags_list, list):
                    tags_str = ','.join(tags_list)
                else:
                    tags_str = data['tags']
            except json.JSONDecodeError:
                tags_str = data['tags']

    try:
        # Update text fields (Title, Description)
        inspiration.title = data.get('title', inspiration.title)
        inspiration.description = data.get('description', inspiration.description)
        inspiration.tags = tags_str if tags_str is not None else inspiration.tags
        
        # --- 3. CALL FILE UPDATE HANDLER ---
        # The update_inspiration_files function handles DB session/commit/rollback for files
        update_inspiration_files(files, inspiration_id, files_to_delete)
        
        # We need a final commit for the text changes if update_inspiration_files didn't commit everything
        # Since update_inspiration_files commits at the end, we can assume the session is clean/committed.
        
        # If the file handler succeeds and commits, we commit text changes here too (safe practice)
        db.session.commit()
        
        return jsonify({"message": "Inspiration and files updated successfully"}), 200
        
    except Exception as e:
        # Since file update might raise an exception, we catch it here.
        db.session.rollback()
        logging.exception(f"Failed to update inspiration {inspiration_id}: {str(e)}")
        return jsonify({"error": f"Failed to update inspiration: {str(e)}"}), 500
    
@inspiration_bp.route('/del_inspirations/<string:inspiration_id>', methods=['DELETE'])
def delete_inspiration(inspiration_id):
    inspiration = Inspiration.query.get(inspiration_id)
    if not inspiration:
        return jsonify({"error": "Inspiration not found"}), 404

    try:
        db.session.delete(inspiration)
        db.session.commit()
        return jsonify({"message": "Inspiration deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete inspiration"}), 500