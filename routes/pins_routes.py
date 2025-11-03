from flask import Blueprint , jsonify , request , current_app
import uuid
from datetime import datetime
from models import Pin, Boards, db , Upload_Files 
from .upload_files_routes import upload_pin_files,update_pin_files
import os
from sqlalchemy.exc import IntegrityError 
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import os
import json


load_dotenv()
pins_bp = Blueprint("pins" , __name__)

CORS(pins_bp)

@pins_bp.route('/test_pinterest_token', methods=['GET'])
def test_pinterest_token():
    # 1. Get the Pinterest Access Token securely from environment variables
    # NOTE: You MUST have PINTEREST_TOKEN set in your .env file
    PINTEREST_TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN")

    if not PINTEREST_TOKEN:
        return jsonify({
            "error": "Internal Server Error",
            "message": "PINTEREST_TOKEN not found in environment variables."
        }), 500

    # 2. Define the Request Parameters for the Pinterest API
    PINTEREST_TEST_URL = "https://api.pinterest.com/v5/pins/user_account"
    HEADERS = {
        "Authorization": f"Bearer {PINTEREST_TOKEN}",
        "Accept": "application/json"
    }

    try:
        # 3. Send the GET request to Pinterest
        # The timeout is good practice to prevent requests from hanging indefinitely
        response = requests.get(PINTEREST_TEST_URL, headers=HEADERS, timeout=10)
        
        # 4. Handle the Response from Pinterest
        if response.status_code == 200:
            # Token works! Return the user data received from Pinterest
            user_data = response.json()
            return jsonify({
                "message": "Pinterest Access Token is VALID and working!",
                "user_info": user_data
            }), 200
        
        else:
            # Token failed (e.g., 401 Unauthorized, 403 Forbidden)
            error_data = response.json()
            return jsonify({
                "error": "Pinterest API Error",
                "status_code": response.status_code,
                "pinterest_response": error_data,
                "message": "Token failed to authenticate or authorize with Pinterest."
            }), response.status_code

    except requests.exceptions.RequestException as e:
        # Handle network or connection errors (e.g., timeout, DNS error)
        current_app.logger.error(f"Network error accessing Pinterest API: {e}", exc_info=True)
        return jsonify({
            "error": "Network/Connection Error",
            "message": "Could not connect to the Pinterest API endpoint."
        }), 503

# --- GET all pins ---
@pins_bp.route('/get', methods=['GET'])
def get_all_pins():
    try:
        pins = Pin.query.all()
        all_pins = []
        for pin in pins:
            # result.append({
            #     'pin_id': pin.pin_id,
            #     'board_id': pin.board_id,
            #     'pin_type': pin.pin_type,
            #     'content': pin.content,
            #     'position_x': pin.position_x,
            #     'position_y': pin.position_y,
            #     'created_at': pin.created_at.isoformat()
            # })
            pin_dict = {
                "pin_id":pin.pin_id , 
                "board_id" : pin.board_id,
                "pin_type":pin.pin_type,
                'content':pin.content,
                'position_x':pin.position_x,
                'position_y':pin.position_y,
                'created_at':pin.created_at.isoformat(),
                "files":[]
            }
            find_uploads = db.session.query(Upload_Files).filter(Upload_Files.pin_id == pin.pin_id).all()
            for file in find_uploads:
                file_dict = {
                    "file_id":file.file_id , 
                    "filename":file.filename , 
                    "file_path":file.file_path , 
                    "file_size":file.file_size
                }
                pin_dict['files'].append(file_dict)
            all_pins.append(pin_dict)
        return jsonify(all_pins),200

        # file_uploads = db.session.query()
        # return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GET a single pin by ID ---
@pins_bp.route('/pins/<string:pin_id>', methods=['GET'])
def get_one_pin(pin_id):
    try:
        # pin = Pin.query.get_or_404(pin_id)
        pin = Pin.query.filter_by(pin_id = pin_id).first_or_404(
            description = f'Pin with ID {pin_id} not found'
        )

        pin_dict = {
            'pin_id': pin.pin_id,
            'board_id': pin.board_id,
            'pin_type': pin.pin_type,
            'content': pin.content,
            'position_x': pin.position_x,
            'position_y': pin.position_y,
            'created_at': pin.created_at.isoformat(),
            'files':[]
        }
        # return jsonify(result), 200
        find_uploads = db.session.query(Upload_Files).filter(Upload_Files.pin_id == pin.pin_id).all()
        for file in find_uploads:
            file_dict = {
                "file_id":file.file_id , 
                "filename":file.filename , 
                "file_path":file.file_path , 
                "file_size":file.file_size
            }
            pin_dict["files"].append(file_dict)
        return jsonify(pin_dict),200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new pin ---
@pins_bp.route('/post', methods=['POST'])
def add_pin():
    data = request.form
    required_fields = ['board_id', 'pin_type', 'content']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "board_id, pin_type, and content are required"}), 400
    
    attachments = request.files.getlist("uploads")

    new_pin = Pin(
        board_id = data.get('board_id'),
        pin_type = data.get('pin_type'),
        content=data.get('content'),
        position_x = data.get('position_x'),
        position_y = data.get('position_y')
    )
        
    try:
        # Check if the parent board exists
        # if not Boards.query.get(data['board_id']):
        #     return jsonify({"error": "Board not found"}), 404

        # new_pin = Pin(
        #     board_id=data['board_id'],
        #     pin_type=data['pin_type'],
        #     content=data['content'],
        #     position_x=data.get('position_x'),
        #     position_y=data.get('position_y')
        # )
        db.session.add(new_pin)
        db.session.flush()
        upload_pin_files(attachments , new_pin.pin_id)
        db.session.commit()
        return jsonify({'message': 'Pin added successfully', 'pin_id': new_pin.pin_id , 
                        'file_location' : f"Processed {len(attachments)} file(s)"
                    }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PUT (update) an existing pin ---
@pins_bp.route('/pins/<string:pin_id>', methods=['PUT'])
def update_pin(pin_id):
    pin = Pin.query.get(pin_id)
    if not pin:
        return jsonify({"error":"Pin not found"}) , 404
    
    is_multipart = request.mimetype and 'multipart/form-data' in request.mimetype

    attachments = []
    files_to_delete = []

    if is_multipart:
        data = request.form
        attachments  = request.files.getlist("uploads")

        files_to_delete_json = data.get('files_to_delete' , '[]')
        try:
            files_to_delete = json.loads(files_to_delete_json)
        except json.JSONDecodeError:
            return jsonify({"error":"Invalid format for files_to_delete"}),400
        
        if 'pin_type' in data:
            pin.pint_type = data['pin_type']
        if 'content' in data:
            pin.content = data['content']
        if 'position_x' in data:
            pin.position_x = int(data['position_x'])
        if 'position_y' in data:
            pin.position_y = int(data['position_y'])

    else:
        data = request.get_json()

        if data and 'pin_type' in data:
            pin.pint_type = data['pin_type']
        if data and'content' in data:
            pin.content = data['content']
        if data and 'position_x' in data:
            pin.position_x = int(data['position_x'])
        if data and 'position_y' in data:
            pin.position_y = int(data['position_y'])

    try:
        if attachments or files_to_delete:
            if attachments or files_to_delete:
                pin.revision_number = (pin.revision_number or 0)+1
            update_pin_files(attachments,pin_id,files_to_delete)
        db.session.commit()
        return jsonify({
            "message": "Pin updated successfully.",
            "pin_id": pin.pin_id,
            "pin_type": pin.pin_type,
            "content": pin.content
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating pins/files: {e}")
        return jsonify({"error": "Failed to update pins or files"}), 500


    



# --- DELETE a pin ---
# @pins_bp.route('/delete/<string:pin_id>', methods=['DELETE'])
# def delete_pin(pin_id):
#     pin = Pin.query.get_or_404(pin_id)
    
#     # deleted_files_Count = 0
#     try:
        
#         files_to_delete = Upload_Files.query.filter_by(pin_id = pin_id).all()
#         for file_record in files_to_delete:
#             try:
#                 if os.path.exists(file_record.file_path):
#                     os.remove(file_record.file_path)
#             except OSError:
#                 pass


                
#             db.session.delete(file_record)
#             deleted_files_count += 1
#         db.session.delete(pin)
#         db.session.commit()

#         return jsonify({'message': 'Pin deleted successfully',
#                         'files_deleted': deleted_files_count
#                     }), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

# @pins_bp.route('/delete/<string:pin_id>', methods=['DELETE'])
# def delete_pin(pin_id):
#     pin = Pin.query.get_or_404(pin_id)
    
#     # 🌟 CORRECT PLACEMENT: Initialize the variable here.
#     deleted_files_count = 0 
    
#     try:
#         # 1. FIND ALL CHILD RECORDS 
#         files_to_delete = Upload_Files.query.filter_by(pin_id=pin_id).all()
        
#         for file_record in files_to_delete:
#             # ... delete physical file logic ...
            
#             # Delete DB record
#             db.session.delete(file_record)
#             deleted_files_count += 1  # Variable is incremented safely
            
#         # Delete parent record
#         db.session.delete(pin)
#         db.session.commit()
        
#         # This return now works correctly
#         return jsonify({
#             'message': 'Pin and associated files deleted successfully',
#             'files_deleted': deleted_files_count 
#         }), 200
        
#     except Exception as e:
#         db.session.rollback()
#         # The error path does not need the count variable in the response
#         return jsonify({"error": "Failed to delete pin or files: " + str(e)}), 500

@pins_bp.route('/delete/<string:pin_id>', methods=['DELETE'])
def delete_pin(pin_id):
    pin = Pin.query.get_or_404(pin_id)
    
    if not pin:
        return jsonify({"error":"Pin not found"}) , 404
    
    try:
        uploads = Upload_Files.query.filter_by(pin_id=pin_id).all()
        for upload in uploads:
            db.session.delete(upload)

        db.session.commit()
        db.session.delete(upload)
        db.session.commit()
        return jsonify({"message":"Pins deleted successfully"})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting pin : {e}")
        return jsonify({"error":"Failed to delete pin"}) , 500
       