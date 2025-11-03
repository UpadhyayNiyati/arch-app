from flask import Blueprint, request, jsonify, current_app
from models import db, Spaces , Upload_Files
from .upload_files_routes import upload_space_files
import logging
import os
from flask_cors import CORS
import json

spaces_bp = Blueprint('Spaces' , __name__)
CORS(spaces_bp)

@spaces_bp.route('/get/spaces', methods=['GET'])
def get_all_spaces():
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
def get_space_by_id(space_id):
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
def create_space():
    data = request.form

    required_fields = ['space_name', 'category']
    if any(field not in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
   
    attachments = request.files.getlist("uploads")

    new_space = Spaces(
        project_id=data['project_id'],
        space_name=data['space_name'],
        description=data.get('description', None),
        space_type=data.get('space_type'),
        category = data.get('category', 'Custom'),
        status=data.get('status', 'To Do')
    )

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
def update_space(space_id):
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
def delete_space(space_id):
    space = Spaces.query.get(space_id)
    if not space:
        return jsonify({"error": "Space not found"}), 404
    
    try:
        uploads = Upload_Files.query.filter_by(space_id=space_id).all()
        for upload in uploads:
            db.session.delete(upload)
        db.session.commit()
        db.session.delete(space)
        db.session.commit()
        return jsonify({"message": "Space and associated files deleted successfully"}), 200 
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting space {space_id}: {e}")
        return jsonify({"error": "Failed to delete space", "details": str(e)}), 500
