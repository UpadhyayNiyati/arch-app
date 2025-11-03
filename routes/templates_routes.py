from flask import Blueprint , jsonify , request , current_app
from models import Templates , db , Upload_Files  , TemplateCards , Tag
from .upload_files_routes import upload_template_files , update_template_files , delete_selected_files
import datetime
from flask import current_app
import logging
import uuid
import json
from flask_cors import CORS

templates_bp = Blueprint('templates', __name__)
CORS(templates_bp)

#get all templates
@templates_bp.route('/templates' , methods = ['GET'])
def get_all_templates():
    try:
        all_templates = []  # <--- 1. Initialize an empty list
        templates = Templates.query.all()
        
        for template in templates:
            template_dict = {
                'template_id': template.template_id, 
                'template_name': template.template_name,
                'description': template.description,
                'created_at': template.created_at,
                'files': []
            }

            find_uploads = db.session.query(Upload_Files).filter(Upload_Files.template_id == template.template_id).all()
            
            for file in find_uploads:
                file_dict = {
                    "file_id": file.file_id,
                    "filename": file.filename, 
                    "file_path": file.file_path, 
                    "file_size": file.file_size
                }
                template_dict['files'].append(file_dict)
            
            all_templates.append(template_dict) # <--- 2. Append the current template to the list
            
        # 3. Return the entire list AFTER the loop is complete
        # It's good practice to wrap the list in an object, but returning the list works too.
        return jsonify(all_templates), 200 
        # OR: return jsonify({"templates": all_templates}), 200 
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#get single template by id
@templates_bp.route('/templates/<string:template_id>' , methods = ['GET'])
def get_template_by_id(template_id):
    template = Templates.query.get_or_404(template_id)
    if not template:
        return jsonify({"message":"Template not found"}) , 404
    template_dict = {
        'template_id' : template.template_id , 
        'template_name' : template.template_name , 
        'description' : template.description , 
        'created_at' : template.created_at , 
        'files' : []

        # 'image_url' : template.image_url
    }
    find_uploads = db.session.query(Upload_Files).filter(Upload_Files.template_id == template.template_id).all()

    for file in find_uploads:
        file_dict = {
            "file_id":file.file_id ,
            "filename":file.filename , 
            "file_path":file.file_path , 
            "file_size":file.file_size
        }
        template_dict['files'].append(file_dict)
    return jsonify(template_dict) , 200

# @templates_bp.route('/templates/<string:template_id>' , methods = ['GET'])
# def get_template_by_id(template_id):
#     # 1. Fetch the main template data
#     template = Templates.query.get_or_404(template_id)
#     # The get_or_404 handles the "Template not found" case.
    
#     # 2. Fetch related data: Tags and Included Cards
    
#     # --- FIX FOR 'AttributeError: ... tags' ---
#     # Assuming 'TemplateTags' is your tag model and it's linked via an association table 
#     # (or a ForeignKey on TemplateTags) to the Templates ID.
#     # Replace the failing line with an explicit query:
#     tag_records = db.session.query(Tag).filter(
#         # Assuming a join table or a filter criteria that links tag_id to template_id
#         Tag.template_id == template.template_id # This filter must match your DB structure!
#     ).all()
    
#     # Extract the tag names from the retrieved records
#     tags = [tag.tag_name for tag in tag_records]

#     # ------------------------------------------

#     # Assuming 'cards' relationship is also missing, this will likely cause a similar error.
#     # If template.cards also causes an AttributeError, you must fix it the same way.
#     try:
#         included_cards_preview = [{
#             'type': card.card_type, 
#             'title': card.card_title,
#             'subtitle': card.card_subtitle
#         } for card in template.cards]
#     except AttributeError:
#         # If 'cards' relationship is missing, perform an explicit query here too
#         card_records = db.session.query(TemplateCards).filter(TemplateCards.template_id == template.template_id).all()
#         included_cards_preview = [{
#             'type': card.card_type, 
#             'title': card.card_title,
#             'subtitle': card.card_subtitle
#         } for card in card_records]

#     # 3. Construct the response dictionary
#     template_dict = {
#         # ... (rest of the dictionary construction remains the same)
#         'tags': tags, # Now uses the explicitly queried tags list
#         'included_cards': included_cards_preview,
#         # ...
#     }
    
    # # 4. Fetch uploaded files (kept from your original code)
    # # ... (code for find_uploads remains the same)
        
    # return jsonify(template_dict), 200

#post template
@templates_bp.route('/templates' , methods = ['POST'])
def add_templates():
    data = request.form
    required_fields = ['template_name' , 'description' ]
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"'{field}' is required"}), 400
    attachments = request.files.getlist('uploads')

    new_templates = Templates(
        template_name = data.get('template_name') ,
        description = data.get('description') 
    )
    db.session.add(new_templates)
    db.session.commit()
    # if attachments:
    #     upload_template_files(attachments , new_templates.template_id)
    try:
        db.session.add(new_templates)
        db.session.flush()
        upload_template_files(attachments, new_templates.template_id)
        db.session.commit()
        return jsonify({
            "message" : "Templates and files uploaded successfully",
            "template_id":new_templates.template_id , 
            "file_location" : f"Processed {len(attachments)}",
        }) , 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating template: {e}")
        return jsonify({"message":"Failed to create template" , "error": str(e)}) , 400
    

# --- UPDATE TEMPLATE AND ASSOCIATED FILES ---
@templates_bp.route('/templates/<string:template_id>' , methods = ['PUT'])
def update_template(template_id):
    # Use request.form to handle both form data (template_name, description, files_to_delete) 
    # and uploaded files (new_uploads) via multipart/form-data.
    data = request.form
    template = Templates.query.get_or_404(template_id)
    
    if not template:
        return jsonify({"message":"Template not found"}) , 404

    try:
        # 1. Update Template Metadata
        if 'template_name' in data:
            template.template_name = data['template_name']
        if 'description' in data:
            template.description = data['description']
        
        # 2. Handle File Updates (Upload new and delete old)
        attachments_to_add = request.files.getlist('new_uploads')
        
        # Get list of file_ids to delete (expected as a JSON string in the form data)
        files_to_delete_str = data.get('files_to_delete', '[]')
        files_to_delete = json.loads(files_to_delete_str)
        
        # Call the utility function to handle file upload and deletion in one logical step
        # Note: The utility function `update_template_files` handles its own commit/rollback 
        # according to your original code's pattern.
        if attachments_to_add or files_to_delete:
             # update_template_files(files, template_id, files_to_delete) - uses corrected signature
            update_template_files(attachments_to_add, template_id, files_to_delete)


        # 3. Commit Template Metadata changes (File changes were committed inside the utility function)
        db.session.commit() 
        
        # 4. Prepare Response
        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.template_id == template.template_id).all()
        files_list = [{
            "file_id": file.file_id,
            "filename": file.filename, 
            "file_path": file.file_path, 
            "file_size": file.file_size
        } for file in find_uploads]

        result = {
            'template_id' : template.template_id , 
            'template_name' : template.template_name , 
            'description' : template.description , 
            'created_at' : template.created_at ,
            'files' : files_list
        }

        return jsonify(result) , 200
    
    except Exception as e:
        # Ensure rollback if metadata update failed, even if file update succeeded/failed
        db.session.rollback()
        current_app.logger.error(f"Error updating template {template_id}: {e}")
        return jsonify({"message": "Failed to update template", "error": str(e)}), 400
    

# --- DELETE SINGLE UPLOADED FILE ---
@templates_bp.route('/templates/files/<string:template_id>' , methods = ['DELETE'])
def delete_template_file(template_id):
    """Deletes a single file record from the DB and the corresponding file from disk."""
    template = Templates.query.get_or_404(template_id)
    if not template:
        return jsonify({"message":"Template not found"}) , 404
    try:
        uploads = Upload_Files.query.filter_by(template_id = template_id).all()
        for upload in uploads:
            db.session.delete(upload)
        db.session.commit()
        db.session.delete(template)
        db.session.commit()
        return jsonify({'message': 'File deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting file: {e}")
        return jsonify({"error": str(e)}), 500
    