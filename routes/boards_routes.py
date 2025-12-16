from flask import Blueprint , jsonify , request
from models import Boards , db , Projects , PinTag ,Pin,Tag,Upload_Files , Pinterest
import uuid
from flask import current_app
import datetime
from datetime import datetime , timedelta
from flask_cors import CORS
import logging
import json
from .upload_files_routes import upload_board_files , update_board_files
from auth.authhelpers import jwt_required
import requests

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
    

# @boards_bp.route("/import_board", methods=["POST"])
# @jwt_required
# def import_board():
#     user_id = request.current_user_id

#     # 1. Read request body
#     data = request.get_json()
#     pinterest_board_id = data.get("pinterest_board_id")
#     board_name = data.get("board_name")
#     project_id = data.get("project_id")
#     company_id = data.get("company_id")
#     board_description = data.get("board_description", "")

#     if not pinterest_board_id:
#         return jsonify({"error": "pinterest_board_id is required"}), 400

#     # 2. Fetch the user's Pinterest access token
#     pinterest_data = Pinterest.query.filter_by(user_id=user_id).first()
#     if not pinterest_data:
#         return jsonify({"error": "Pinterest account not connected"}), 400

#     ACCESS_TOKEN = pinterest_data.access_token
#     if not ACCESS_TOKEN:
#         return jsonify({"error": "Pinterest Access Token is missing"}), 500
#     headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

#     # 3. Check if board already imported
#     existing_board = Boards.query.filter_by(
#         user_id=user_id,
#         pinterest_board_id=pinterest_board_id,
#         source_type="pinterest"
#     ).first()

#     if existing_board:
#         # FIX: Fetch the actual count of pins for the existing board
#         try:
#             # Assuming Pin model has a 'board_id' foreign key
#             total_pins_count = Pin.query.filter_by(board_id=existing_board.board_id).count()
#         except Exception as e:
#             current_app.logger.error(f"Error fetching pin count for existing board: {str(e)}")
#             total_pins_count = 0 # Default to 0 on error

#     if existing_board:
#         return jsonify({
#             "message": "Board already imported",
#             "board_id": existing_board.board_id,
#             "board_name": existing_board.board_name,
#             "board_description": existing_board.board_description,
#             "board_url": existing_board.board_url,
#             "is_imported": existing_board.is_imported,
#             "source_type": existing_board.source_type,
#             "created_at": existing_board.created_at.isoformat(),
#             "company_id": existing_board.company_id,
#             "project_id": existing_board.project_id,
#             "total_pins": total_pins_count
#         }), 200

#     # 4. Fetch board details (optional)
#     board_url = f"https://www.pinterest.com/pin/{pinterest_board_id}"
#     try:
#         board_details_response = requests.get(
#             f"https://api.pinterest.com/v5/boards/{pinterest_board_id}",
#             headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
#         )

#         if board_details_response.status_code == 200:
#             board_details = board_details_response.json()

#             board_name = board_name or board_details.get("name", "Imported Pinterest Board")
#             board_description = board_description or board_details.get("description", "")
#             board_url = board_details.get("url", board_url)

#     except Exception as e:
#         current_app.logger.error(f"Error fetching board details: {str(e)}")

#     all_pins_data = []
#     bookmark = None
#     base_url = f"https://api.pinterest.com/v5/boards/{pinterest_board_id}/pins"

#     while True:
#           params = {}
#           if bookmark:
#               params['bookmark'] = bookmark

    

#     # 5. Fetch pins from Pinterest
#     try:
#         pins_response = requests.get(base_url, headers=headers, params=params)
#         pins_response = requests.get(
#             f"https://api.pinterest.com/v5/boards/{pinterest_board_id}/pins",
#             headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
#         )

#         if pins_response.status_code != 200:
#             return jsonify({
#                 "error": "Failed to fetch pins",
#                 "details": pins_response.text
#             }), 400

#         # pins_data = pins_response.json().get("items", [])
#         all_pins_data.extend(pins_response_json.get("items", []))
#         bookmark = pins_response_json.get("bookmark")
                
#                 # Stop if no bookmark is returned or if the bookmark is an empty string
#         if not bookmark:
#             break

#     except requests.exceptions.RequestException as e:
#         # return jsonify({"error": f"Network error: {str(e)}"}), 500
#         return jsonify({"error": f"Network error during pin fetching: {str(e)}"}), 500
    
#     pins_data = all_pins_data

#     # 6. Save board in DB
#     try:
#         new_board = Boards(
#             user_id=user_id,
#             company_id=company_id,
#             project_id=project_id,
#             board_name=board_name,
#             board_description=board_description,
#             pinterest_board_id=pinterest_board_id,
#             board_url=board_url,
#             source_type="pinterest",
#             is_imported=True,
#             created_at=datetime.utcnow()
#         )

#         db.session.add(new_board)
#         db.session.commit()

#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error saving board: {e}")
#         return jsonify({"error": "Database error while saving board"}), 500

#     # 7. Save pins
#     try:
#         pins_to_add = []
#         for pin in pins_data:
#             media = pin.get("media", {})
#             image_obj = media.get("images", {}).get("original", {})
#             image_url = image_obj.get("url")

#             if not image_url:
#                 continue

#             pins_to_add.append(Pin(
#                 board_id=new_board.board_id,
#                 pinterest_pin_id=pin.get("id"),
#                 image_url=image_url,
#                 title=pin.get("title") or pin.get("alt_text", ""),
#                 link=pin.get("link", ""),
#                 created_at=datetime.utcnow()
#             ))

#         if pins_to_add:
#             db.session.add_all(pins_to_add)

#         db.session.commit()

#         final_total_pins = len(pins_to_add)

#         return jsonify({
#             "message": "Board and pins imported successfully",
#             "board_id": new_board.board_id,
#             "total_pins": final_total_pins,
#             "board_name": new_board.board_name,
#             "board_description": new_board.board_description,
#             "board_url": new_board.board_url,
#             "is_imported": new_board.is_imported,
#             "source_type": new_board.source_type,
#             "created_at": new_board.created_at.isoformat(),
#             "company_id": new_board.company_id,
#             "project_id": new_board.project_id
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error saving pins: {e}")
#         return jsonify({"error": "Database error while saving pins"}), 500


# @boards_bp.route("/import_board", methods=["POST"])
# @jwt_required
# def import_board():
#     """
#     Imports a Pinterest board and all its pins, handling API pagination.
#     """
#     try:
#         # User ID is assumed to be set by the @jwt_required decorator
#         user_id = request.current_user_id

#         # 1. Read request body
#         data = request.get_json()
#         pinterest_board_id = data.get("pinterest_board_id")
#         board_name = data.get("board_name")
#         project_id = data.get("project_id")
#         company_id = data.get("company_id")
#         board_description = data.get("board_description", "")
#         space_id = data.get("space_id")

#         if not pinterest_board_id:
#             return jsonify({"error": "pinterest_board_id is required"}), 400

#         # 2. Fetch the user's Pinterest access token
#         pinterest_data = Pinterest.query.filter_by(user_id=user_id).first()
#         if not pinterest_data:
#             return jsonify({"error": "Pinterest account not connected"}), 400

#         ACCESS_TOKEN = pinterest_data.access_token
#         if not ACCESS_TOKEN:
#             return jsonify({"error": "Pinterest Access Token is missing"}), 500
        
#         headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

#         # 3. Check if board already imported
#         existing_board = Boards.query.filter_by(
#             user_id=user_id,
#             pinterest_board_id=pinterest_board_id,
#             source_type="pinterest"
#         ).first()

#         if existing_board:
#             # Fetch the actual count of pins for the existing board
#             try:
#                 # Assuming Pin model has a 'board_id' foreign key
#                 total_pins_count = Pin.query.filter_by(board_id=existing_board.board_id).count()
#             except Exception as e:
#                 current_app.logger.error(f"Error fetching pin count for existing board: {str(e)}")
#                 # total_pins_count = 0 # Default to 0 on error

#             return jsonify({
#                 "message": "Board already imported",
#                 "board_id": existing_board.board_id,
#                 "total_pins": total_pins_count,
#                 "board_name": existing_board.board_name,
#                 "board_description": existing_board.board_description,
#                 "board_url": existing_board.board_url,
#                 "is_imported": existing_board.is_imported,
#                 "source_type": existing_board.source_type,
#                 "created_at": existing_board.created_at.isoformat(),
#                 "company_id": existing_board.company_id,
#                 "project_id": existing_board.project_id,
#                 "space_id": space_id
#             }), 200

#         # 4. Fetch board details (optional, but good for name/description)
#         board_url = f"https://www.pinterest.com/pin/{pinterest_board_id}"
#         try:
#             board_details_response = requests.get(
#                 f"https://api.pinterest.com/v5/boards/{pinterest_board_id}",
#                 headers=headers
#             )

#             if board_details_response.status_code == 200:
#                 board_details = board_details_response.json().get('data', {}) # Use .get('data', {}) as per Pinterest API structure

#                 board_name = board_name or board_details.get("name", "Imported Pinterest Board")
#                 board_description = board_description or board_details.get("description", "")
#                 board_url = board_details.get("url", board_url) # 'url' is preferred if available
#             else:
#                  current_app.logger.warning(f"Failed to fetch board details: {board_details_response.status_code} - {board_details_response.text}")


#         except Exception as e:
#             current_app.logger.error(f"Error fetching board details: {str(e)}")

#         # 5. Fetch ALL pins from Pinterest - **WITH PAGINATION**
#         all_pins_data = []
#         bookmark = None
#         base_url = f"https://api.pinterest.com/v5/boards/{pinterest_board_id}/pins"

#         while True:
#             params = {}
#             if bookmark:
#                 params['bookmark'] = bookmark
            
#             # The Pinterest API defaults to a page size (limit) of 25. You can add params['limit'] = 100 
#             # if you want to increase the page size (max 100).

#             try:
#                 page_count += 1
#                 pins_response = requests.get(base_url, headers=headers, params=params)

#                 if pins_response.status_code != 200:
#                     current_app.logger.error(f"Pinterest API error on page {page_count}: {pins_response.status_code} - {pins_response.text}")
#                     return jsonify({
#                         "error": "Failed to fetch pins (Pinterest API Error)",
#                         "details": pins_response.json().get('message', 'Unknown API Error')
#                     }), 400
#                 pins_response = requests.get(base_url, headers=headers, params=params)

#                 if pins_response.status_code != 200:
#                     # Handle API errors during pagination
#                     return jsonify({
#                         "error": "Failed to fetch pins (during pagination)",
#                         "details": pins_response.text
#                     }), 400

#                 pins_response_json = pins_response.json()

#                 pins_for_page = pins_response_json.get("data", pins_response_json.get("items", []))

#                 if not pins_for_page and page_count == 1:
#                     # Logs the full response if no pins are found on the first page for debugging the key
#                     current_app.logger.info(f"Pinterest API Response (Page 1) shows 0 pins. Full response: {pins_response_json}")
#                     current_app.logger.warning("No pins found in the first Pinterest API response. Check 'data' or 'items' keys for pins list.")
                
#                 # Extend the list with pins from the current page
#                 # Pins are usually in the 'items' key of the response, check API docs
#                 all_pins_data.extend(pins_response_json.get("items", []))
                
#                 # Get the bookmark for the next page
#                 bookmark = pins_response_json.get("bookmark")
                
#                 # Stop if no bookmark is returned or if the bookmark is an empty string
#                 if not bookmark:
#                     break

#             except requests.exceptions.RequestException as e:
#                 # Network error during the fetching loop
#                 return jsonify({"error": f"Network error during pin fetching: {str(e)}"}), 500

#         pins_data = all_pins_data
        
#         if not pins_data and not existing_board:
#             # Decide if you want to allow importing an empty board
#              current_app.logger.warning(f"No pins found for board {pinterest_board_id}")
#              # You might want to continue or return an error here. Continuing to save the board: pass
        
#         # 6. Save board in DB
#         try:
#             new_board = Boards(
#                 user_id=user_id,
#                 company_id=company_id,
#                 project_id=project_id,
#                 board_name=board_name,
#                 board_description=board_description,
#                 pinterest_board_id=pinterest_board_id,
#                 board_url=board_url,
#                 source_type="pinterest",
#                 is_imported=True,
#                 created_at=datetime.utcnow(),
#                 space_id=space_id
#             )

#             db.session.add(new_board)
#             db.session.flush() # Flush to get new_board.board_id before pin saving

#         except Exception as e:
#             db.session.rollback()
#             current_app.logger.error(f"Error saving board: {e}")
#             return jsonify({"error": "Database error while saving board"}), 500

#         # 7. Save pins
#         pins_to_add = []
#         try:
#             for pin in pins_data:
#                 media = pin.get("media", {})
#                 # Access 'original' image size or choose another size (e.g., '237x', '736x')
#                 image_obj = media.get("images", {}).get("original", {}) 
#                 image_url = image_obj.get("url")

#                 if not image_url:
#                     continue # Skip pins without a main image URL

#                 pins_to_add.append(Pin(
#                     board_id=new_board.board_id,
#                     pinterest_pin_id=pin.get("id"),
#                     image_url=image_url,
#                     title=pin.get("title") or pin.get("alt_text", ""),
#                     link=pin.get("link", ""),
#                     created_at=datetime.utcnow()
#                 ))

#             if pins_to_add:
#                 db.session.add_all(pins_to_add)

#             db.session.commit()

#             final_total_pins = len(pins_to_add)
#             # --- DEBUGGING LOG HERE ---
#             current_app.logger.info(f"Successfully processed {len(pins_data)} pins from API, saved {final_total_pins} pins to DB.")


#             return jsonify({
#                 "message": "Board and pins imported successfully",
#                 "board_id": new_board.board_id,
#                 "total_pins": final_total_pins,
#                 "board_name": new_board.board_name,
#                 "board_description": new_board.board_description,
#                 "board_url": new_board.board_url,
#                 "is_imported": new_board.is_imported,
#                 "source_type": new_board.source_type,
#                 "created_at": new_board.created_at.isoformat(),
#                 "company_id": new_board.company_id,
#                 "space_id": space_id,
#                 "project_id": new_board.project_id
#             }), 201

#         except Exception as e:
#             db.session.rollback()
#             current_app.logger.error(f"Error saving pins: {e}")
#             # Consider deleting the board if pin saving failed? 
#             # For simplicity, we just return an error here.
#             return jsonify({"error": "Database error while saving pins"}), 500
            
#     except Exception as e:
#         # Catch any unexpected errors outside the main logic blocks
#         current_app.logger.error(f"Unexpected error in import_board: {e}")
#         return jsonify({"error": "An unexpected server error occurred"}), 500
    

# @boards_bp.route("/inspiration", methods=["GET"])
# @jwt_required
# def get_inspiration():
#     user_id = request.current_user_id
#     boards = Boards.query.filter_by(user_id=user_id).all()
    
#     all_pins = []
#     for board in boards:
#         pins = Pin.query.filter_by(board_id=board.board_id).all()
#         for pin in pins:
#             all_pins.append({
#                 "pin_id": pin.pin_id,
#                 "board_name": board.board_name,
#                 "image_url": pin.image_url,
#                 "title": pin.title,
#                 "link": pin.link
#             })
    
#     return jsonify({"pins": all_pins})


# @boards_bp.route("/import_board", methods=["POST"])
# @jwt_required
# def import_board():
#     """
#     Imports a Pinterest board and all its pins, handling API pagination.
#     """
#     try:
#         # User ID is assumed to be set by the @jwt_required decorator
#         user_id = request.current_user_id

#         # 1. Read request body
#         data = request.get_json()
#         pinterest_board_id = data.get("pinterest_board_id")
#         board_name = data.get("board_name")
#         project_id = data.get("project_id")
#         company_id = data.get("company_id")
#         board_description = data.get("board_description", "")
#         space_id = data.get("space_id")

#         if not pinterest_board_id:
#             return jsonify({"error": "pinterest_board_id is required"}), 400

#         # 2. Fetch the user's Pinterest access token
#         pinterest_data = Pinterest.query.filter_by(user_id=user_id).first()
#         if not pinterest_data:
#             return jsonify({"error": "Pinterest account not connected"}), 400

#         ACCESS_TOKEN = pinterest_data.access_token
#         if not ACCESS_TOKEN:
#             return jsonify({"error": "Pinterest Access Token is missing"}), 500
        
#         headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

#         # 3. Check if board already imported
#         existing_board = Boards.query.filter_by(
#             user_id=user_id,
#             pinterest_board_id=pinterest_board_id,
#             source_type="pinterest"
#         ).first()

#         if existing_board:
#             # Fetch the actual count of pins for the existing board
#             try:
#                 # Assuming Pin model has a 'board_id' foreign key
#                 total_pins_count = Pin.query.filter_by(board_id=existing_board.board_id).count()
#             except Exception as e:
#                 current_app.logger.error(f"Error fetching pin count for existing board: {str(e)}")
#                 # The original issue of zero pins in the *existing* check will be resolved 
#                 # once the underlying DB/ORM issue is fixed, as total_pins_count is uninitialized here if it fails.
#                 # To prevent UnboundLocalError here, it should be initialized if the `try` block fails:
#                 total_pins_count = 0 

#             return jsonify({
#                 "message": "Board already imported",
#                 "board_id": existing_board.board_id,
#                 "total_pins": total_pins_count,
#                 "board_name": existing_board.board_name,
#                 "board_description": existing_board.board_description,
#                 "board_url": existing_board.board_url,
#                 "is_imported": existing_board.is_imported,
#                 "source_type": existing_board.source_type,
#                 "created_at": existing_board.created_at.isoformat(),
#                 "company_id": existing_board.company_id,
#                 "project_id": existing_board.project_id,
#                 "space_id": space_id
#             }), 200

#         # 4. Fetch board details (optional, but good for name/description)
#         board_url = f"https://www.pinterest.com/pin/{pinterest_board_id}"
#         try:
#             board_details_response = requests.get(
#                 f"https://api.pinterest.com/v5/boards/{pinterest_board_id}",
#                 headers=headers
#             )

#             if board_details_response.status_code == 200:
#                 board_details = board_details_response.json().get('data', {}) # Use .get('data', {}) as per Pinterest API structure

#                 board_name = board_name or board_details.get("name", "Imported Pinterest Board")
#                 board_description = board_description or board_details.get("description", "")
#                 board_url = board_details.get("url", board_url) # 'url' is preferred if available
#             else:
#                 current_app.logger.warning(f"Failed to fetch board details: {board_details_response.status_code} - {board_details_response.text}")

#         except Exception as e:
#             current_app.logger.error(f"Error fetching board details: {str(e)}")

#         # 5. Fetch ALL pins from Pinterest - **WITH PAGINATION**
#         all_pins_data = []
#         bookmark = None
#         base_url = f"https://api.pinterest.com/v5/boards/{pinterest_board_id}/pins"

#         # **FIX:** Initialize page_count before the loop to prevent UnboundLocalError
#         page_count = 0 

#         while True:
#             params = {}
#             if bookmark:
#                 params['bookmark'] = bookmark
            
#             # The Pinterest API defaults to a page size (limit) of 25. You can add params['limit'] = 100 
#             # if you want to increase the page size (max 100).

#             try:
#                 pins_response = requests.get(base_url, headers=headers, params=params)

#                 if pins_response.status_code != 200:
#                     current_app.logger.error(f"Pinterest API error on page {page_count + 1}: {pins_response.status_code} - {pins_response.text}")
#                     # Handle API errors during pagination
#                     return jsonify({
#                         "error": "Failed to fetch pins (during pagination)",
#                         "details": pins_response.text
#                     }), 400

#                 pins_response_json = pins_response.json()
                
#                 # Increment page_count after successful fetch
#                 page_count += 1
                
#                 # Use the pins_for_page variable to ensure we capture the data correctly
#                 pins_for_page = pins_response_json.get("data", pins_response_json.get("items", []))

#                 if not pins_for_page and page_count == 1:
#                     # Logs the full response if no pins are found on the first page for debugging the key
#                     current_app.logger.info(f"Pinterest API Response (Page 1) shows 0 pins. Full response: {pins_response_json}")
#                     current_app.logger.warning("No pins found in the first Pinterest API response. Check 'data' or 'items' keys for pins list.")
                
#                 # Extend the list with pins from the current page
#                 all_pins_data.extend(pins_for_page) 
                
#                 # Get the bookmark for the next page
#                 bookmark = pins_response_json.get("bookmark")
                
#                 # Stop if no bookmark is returned or if the bookmark is an empty string
#                 if not bookmark:
#                     break

#             except requests.exceptions.RequestException as e:
#                 # Network error during the fetching loop
#                 return jsonify({"error": f"Network error during pin fetching: {str(e)}"}), 500

#         pins_data = all_pins_data
        
#         if not pins_data and not existing_board:
#             # Decide if you want to allow importing an empty board
#              current_app.logger.warning(f"No pins found for board {pinterest_board_id}")
#              # You might want to continue or return an error here. Continuing to save the board: pass
        
#         # 6. Save board in DB
#         try:
#             new_board = Boards(
#                 user_id=user_id,
#                 company_id=company_id,
#                 project_id=project_id,
#                 board_name=board_name,
#                 board_description=board_description,
#                 pinterest_board_id=pinterest_board_id,
#                 board_url=board_url,
#                 source_type="pinterest",
#                 is_imported=True,
#                 created_at=datetime.utcnow(),
#                 space_id=space_id
#             )

#             db.session.add(new_board)
#             db.session.flush() # Flush to get new_board.board_id before pin saving

#         except Exception as e:
#             db.session.rollback()
#             current_app.logger.error(f"Error saving board: {e}")
#             return jsonify({"error": "Database error while saving board"}), 500

#         # 7. Save pins
#         pins_to_add = []
#         try:
#             for pin in pins_data:
#                 media = pin.get("media", {})
#                 # Access 'original' image size or choose another size (e.g., '237x', '736x')
#                 image_obj = media.get("images", {}).get("original", {}) 
#                 image_url = image_obj.get("url")

#                 if not image_url:
#                     continue # Skip pins without a main image URL

#                 pins_to_add.append(Pin(
#                     board_id=new_board.board_id,
#                     pinterest_pin_id=pin.get("id"),
#                     image_url=image_url,
#                     title=pin.get("title") or pin.get("alt_text", ""),
#                     link=pin.get("link", ""),
#                     created_at=datetime.utcnow()
#                 ))

#             if pins_to_add:
#                 db.session.add_all(pins_to_add)

#             db.session.commit()

#             final_total_pins = len(pins_to_add)
#             current_app.logger.info(f"Successfully processed {len(pins_data)} pins from API, saved {final_total_pins} pins to DB.")


#             return jsonify({
#                 "message": "Board and pins imported successfully",
#                 "board_id": new_board.board_id,
#                 "total_pins": final_total_pins,
#                 "board_name": new_board.board_name,
#                 "board_description": new_board.board_description,
#                 "board_url": new_board.board_url,
#                 "is_imported": new_board.is_imported,
#                 "source_type": new_board.source_type,
#                 "created_at": new_board.created_at.isoformat(),
#                 "company_id": new_board.company_id,
#                 "space_id": space_id,
#                 "project_id": new_board.project_id
#             }), 201

#         except Exception as e:
#             db.session.rollback()
#             current_app.logger.error(f"Error saving pins: {e}")
#             # Consider deleting the board if pin saving failed? 
#             # For simplicity, we just return an error here.
#             return jsonify({"error": "Database error while saving pins"}), 500
            
#     except Exception as e:
#         # Catch any unexpected errors outside the main logic blocks
#         current_app.logger.error(f"Unexpected error in import_board: {e}")
#         return jsonify({"error": "An unexpected server error occurred"}), 500