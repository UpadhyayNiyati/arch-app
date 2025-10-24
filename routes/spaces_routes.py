from flask import Blueprint, request, jsonify, current_app
from models import db, Spaces , Upload_Files
from .upload_files_routes import upload_space_files
import logging
import os

spaces_bp = Blueprint('Spaces' , __name__)

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
    if not data or 'project_id' not in data or 'space_name' not in data or 'space_type' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    attachments = request.files.getlist("uploads")

    new_space = Spaces(
        project_id=data['project_id'],
        space_name=data['space_name'],
        description=data.get('description', None),
        space_type=data['space_type'],
        category = data.get('category', 'Custom'),
        status=data.get('status', 'To Do')
    )

    try:
        db.session.add(new_space)
        db.session.flush()
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
        db.session.delete(space)
        db.session.commit()
        return jsonify({"message": "Space deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete space"}), 500