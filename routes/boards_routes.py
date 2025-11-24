from flask import Blueprint , jsonify , request
from models import Boards , db , Projects , PinTag ,Pin,Tag,Upload_Files
import uuid
from flask import current_app
import datetime
from flask_cors import CORS
import logging
import json
from .upload_files_routes import upload_board_files , update_board_files

boards_bp = Blueprint('board' , __name__)

CORS(boards_bp)

def allowed_file(filename):
    # This checks the file extension against a set of allowed types.
    # We'll assume a global 'ALLOWED_EXTENSIONS' set is configured.
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})

def _serialize_board(board):
    """Converts a Boards object into a dictionary, including associated files."""
    board_dict = {
        'board_id': board.board_id,
        'project_id': board.project_id,
        'board_name': board.board_name,
        'board_description': board.board_description,
        'created_at': board.created_at.isoformat(),
        'files' : []
    }
    
    # Fetch and append associated files
    # Note: Using board_id here, which is correct for Boards/Upload_Files relationship
    find_uploads = db.session.query(Upload_Files).filter(Upload_Files.board_id == board.board_id).all()
    for file in find_uploads:
        file_dict = {
            "file_id" : file.file_id,
            "filename":file.filename,
            "file_size":file.file_size,
            "file_path":file.file_path
        }
        board_dict["files"].append(file_dict)
    
    return board_dict


# --- GET all boards ---
@boards_bp.route('/boards', methods=['GET'])
def get_all_boards():
    """
    Retrieves a list of all boards, including their associated file details.
    
    ---
    tags:
      - Board Management
    responses:
      200:
        description: A list of boards retrieved successfully.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/BoardDetail'
      500:
        description: An error occurred while fetching boards.
    """
    try:
        all_boards = []
        boards = Boards.query.all()
        result = []
        for board in boards:
            board_dict = {
                'board_id': board.board_id,
                'project_id': board.project_id,
                'board_name': board.board_name,
                'board_description': board.board_description,
                'created_at': board.created_at.isoformat(),
                'files' : []
                # 'image_url': board.image_url
            }
            find_uploads = db.session.query(Upload_Files).filter(Upload_Files.board_id == board.board_id).all()
            print(Upload_Files)
            for file in find_uploads:
                file_dict = {
                    "file_id" : file.file_id,
                    "filename":file.filename,
                    "file_size":file.file_size,
                    "file_path":file.file_path
                }
                board_dict["files"].append(file_dict)
            all_boards.append(board_dict)
        return jsonify(result), 200
    except Exception as e:
        logging.exception("Error fetching boards: %s", str(e))
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- GET a single board by ID ---
@boards_bp.route('/boards/<string:board_id>', methods=['GET'])
def get_board_by_id(board_id):
    """
    Retrieves a single board by ID, including its associated files, pins, and tags.
    
    ---
    tags:
      - Board Management
    parameters:
      - in: path
        name: board_id
        schema:
          type: string
        required: true
        description: The UUID of the board to retrieve.
    responses:
      200:
        description: Board details retrieved successfully.
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BoardFullDetail'
      404:
        description: Board not found.
      500:
        description: An error occurred while fetching the board.
    """
    try:
        board = Boards.query.get_or_404(board_id)
        board_dict = {
            'board_id': board.board_id,
            'project_id': board.project_id,
            'board_name': board.board_name,
            'board_description': board.board_description,
            'created_at': board.created_at.isoformat(),
            'files':[]
            # 'image_url': board.image_url
        }
        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.pin_id == board.board_id).all()

        for file in find_uploads:
            file_dict = {
                "file_id":file.file_id,
                "filename":file.filename,
                "file_path":file.file_path,
                "file_size":file.file_size
            }
            board_dict["files"].append(file_dict)
        return jsonify(board_dict), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# --- POST a new board ---
@boards_bp.route('/boards', methods=['POST'])
def add_board():
    """
    Creates a new board. Supports multipart/form-data for files.
    
    ---
    tags:
      - Board Management
    requestBody:
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              project_id:
                type: string
                description: The ID of the project the board belongs to. (Required)
              board_name:
                type: string
                description: The name of the new board. (Required)
              board_description:
                type: string
                description: A description for the board. (Optional)
              uploads:
                type: array
                items:
                  type: string
                  format: binary
                description: Files to upload and associate with the board. (Optional)
            required:
              - project_id
              - board_name
    responses:
      200:
        description: Board created successfully.
      400:
        description: Missing required fields or invalid input.
      500:
        description: Failed to create the board.
    """
    data = request.json
    required_fields = ['project_id', 'board_name']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "project_id and board_name are required"}), 400
        
    attachments = request.files.getlist("uploads")

    new_board = Boards(
        project_id = data.get('project_id'),
        board_name = data.get('board_name')
    )

    try:
        db.session.add(new_board)
        db.session.flush()
        upload_board_files(attachments,new_board.board_id)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating board: {e}")
        return jsonify({"error": "Failed to create board"}), 500

# --- PUT (update) an existing board ---
@boards_bp.route('/boards/<string:board_id>', methods=['PUT'])
def update_board(board_id):
    """
    Updates an existing board's details and manages file uploads/deletions. Supports multipart/form-data.
    
    ---
    tags:
      - Board Management
    parameters:
      - in: path
        name: board_id
        schema:
          type: string
        required: true
        description: The UUID of the board to update.
    requestBody:
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              board_name:
                type: string
                description: The new name for the board.
              board_description:
                type: string
                description: The new description for the board.
              uploads:
                type: array
                items:
                  type: string
                  format: binary
                description: New files to upload.
              files_to_delete:
                type: string
                description: JSON string of file_ids to delete (e.g., "[1, 2, 3]").
    responses:
      200:
        description: Board updated successfully.
      400:
        description: Invalid files_to_delete format.
      404:
        description: Board not found.
      500:
        description: Failed to update the board.
    """
    board = Boards.query.get_or_404(board_id)
    if not board:
        return jsonify({"error":"Board not found"}),404
    
    is_multipart = request.mimetype and 'multipart/form-data' in request.mimetype

    attachments = []
    files_to_delete = []

    if is_multipart:
        data = request.form
        attachments = request.files.getlist("uploads")

        files_to_delete_json = data.get('files_to_delete' , '[]')
        try:
            files_to_delete = json.loads(files_to_delete_json)
        except Exception as e:
            return jsonify({"error": "Invalid files_to_delete format"}), 400
        
        if 'board_name' in data:
            board.board_name = data['board_name']
        if 'board_description' in data:
            board.board_description = data['board_description']
    else:
        data = request.json
        if 'board_name' in data:
            board.board_name = data['board_name']
        if 'board_description' in data:
            board.board_description = data['board_description']

    try:
        if attachments or files_to_delete:
            if attachments or files_to_delete:
                board.revision_number = (board.revision_number or 0) + 1
            update_board_files(board.board_id, attachments, files_to_delete)
        db.session.commit()
        updated_board = Boards.query.get(board_id)
        if not updated_board:
            # Should theoretically not happen, but a safe check
            return jsonify({"error": "Board disappeared after update!"}), 500
        return jsonify({"message": "Board updated successfully",
                        "board_id":board.board_id,
                        "new_revision":board.revision_number,
                        "files_added":len(attachments),
                        "files_deleted":len(files_to_delete),
                        "board": _serialize_board(updated_board)
                        }), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating board: {e}")
        return jsonify({"error": "Failed to update board"}), 500
    
# --- DELETE a board ---
@boards_bp.route('/boards/<string:board_id>', methods=['DELETE'])
def delete_board(board_id):
    """
    Deletes a board and its associated files.
    
    ---
    tags:
      - Board Management
    parameters:
      - in: path
        name: board_id
        schema:
          type: string
        required: true
        description: The UUID of the board to delete.
    responses:
      200:
        description: Board deleted successfully.
      404:
        description: Board not found.
      500:
        description: Failed to delete the board.
    """
    board = Boards.query.get_or_404(board_id)
    if not board:
        return jsonify({"error":"Board not found"}),404
    try:
        uploads = Upload_Files.query.filter_by(board_id = board_id).all()
        for upload in uploads:
            db.session.delete(upload)
        db.session.commit()
        db.session.delete(board)
        db.session.commit()
        return jsonify({'message': 'Board deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting board: {e}")
        return jsonify({"error": str(e)}), 500

@boards_bp.route('/boards/<string:board_id>', methods=['GET'])
def get_one_board(board_id):
    try:
        board = Boards.query.get_or_404(board_id)

        # Fetch pins for this board
        pins = Pin.query.filter_by(board_id=board.board_id).all()
        pins_data = []
        for pin in pins:
            # Fetch tags for each pin
            pin_tags = PinTag.query.filter_by(pin_id=pin.pin_id).all()
            tags_data = []
            for pt in pin_tags:
                tag = Tag.query.get(pt.tag_id)
                if tag:
                    tags_data.append(tag.tag_name)
            
            pins_data.append({
                'pin_id': pin.pin_id,
                'pin_type': pin.pin_type,
                'content': pin.content,
                'position_x': pin.position_x,
                'position_y': pin.position_y,
                'created_at': pin.created_at.isoformat(),
                'tags': tags_data
            })
            
        result = {
            'board_id': board.board_id,
            'project_id': board.project_id,
            'board_name': board.board_name,
            'board_description': board.board_description,
            'created_at': board.created_at.isoformat(),
            'image_url': board.image_url,
            'pins': pins_data  # Added pins data here
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500