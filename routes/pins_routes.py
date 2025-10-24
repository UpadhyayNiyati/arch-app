from flask import Blueprint , jsonify , request , current_app
import uuid
from datetime import datetime
from models import Pin, Boards, db , Upload_Files
from .upload_files_routes import upload_pin_files
import os
from sqlalchemy.exc import IntegrityError 

pins_bp = Blueprint("pins" , __name__)

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
    data = request.json
    pin = Pin.query.get_or_404(pin_id)
    
    try:
        if 'pin_type' in data:
            pin.pin_type = data['pin_type']
        if 'content' in data:
            pin.content = data['content']
        if 'position_x' in data:
            pin.position_x = data['position_x']
        if 'position_y' in data:
            pin.position_y = data['position_y']
            
        db.session.commit()
        return jsonify({'message': 'Pin updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

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
    
    deleted_files_count = 0 
    
    try:
        # 1. FIND AND DELETE CHILD RECORDS (Upload_Files)
        # This resolves the Foreign Key Constraint
        files_to_delete = Upload_Files.query.filter_by(pin_id=pin_id).all()
        
        for file_record in files_to_delete:
            
            # 2. DELETE PHYSICAL FILE (Prevents disk bloat)
            try:
                if os.path.exists(file_record.file_path):
                    os.remove(file_record.file_path)
            except OSError:
                # Log an error/warning if the file system operation fails
                current_app.logger.warning(f"Failed to delete physical file: {file_record.file_path}")
            
            # 3. DELETE CHILD RECORD FROM DB SESSION
            db.session.delete(file_record)
            deleted_files_count += 1
            
        # 4. DELETE PARENT PIN RECORD
        db.session.delete(pin)
        
        # 5. COMMIT: All changes are finalized atomically
        db.session.commit()
        
        return jsonify({
            'message': 'Pin and associated files deleted successfully',
            'files_deleted': deleted_files_count
        }), 200
        
    except IntegrityError as e:
        db.session.rollback()
        # This should only happen if another dependency exists (a third child table)
        return jsonify({"error": "Failed to delete pin due to remaining dependencies. Check for other related tables."}), 500
    except Exception as e:
        db.session.rollback()
        # Use exc_info=True for detailed server-side logging
        current_app.logger.error(f"Error deleting pin/files: {e}", exc_info=True) 
        return jsonify({"error": "Failed to delete pin or files: " + str(e)}), 500