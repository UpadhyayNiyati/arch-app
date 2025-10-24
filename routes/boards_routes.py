from flask import Blueprint , jsonify , request
from models import Boards , db , Projects , PinTag ,Pin,Tag
import uuid
from flask import current_app
import datetime

boards_bp = Blueprint('board' , __name__)

def allowed_file(filename):
    # This checks the file extension against a set of allowed types.
    # We'll assume a global 'ALLOWED_EXTENSIONS' set is configured.
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})


# --- GET all boards ---
@boards_bp.route('/boards', methods=['GET'])
def get_all_boards():
    try:
        boards = Boards.query.all()
        result = []
        for board in boards:
            result.append({
                'board_id': board.board_id,
                'project_id': board.project_id,
                'board_name': board.board_name,
                'board_description': board.board_description,
                'created_at': board.created_at.isoformat(),
                # 'image_url': board.image_url
            })
        return jsonify(result), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- GET a single board by ID ---
@boards_bp.route('/boards/<string:board_id>', methods=['GET'])
def get_board_by_id(board_id):
    try:
        board = Boards.query.get_or_404(board_id)
        result = {
            'board_id': board.board_id,
            'project_id': board.project_id,
            'board_name': board.board_name,
            'board_description': board.board_description,
            'created_at': board.created_at.isoformat(),
            # 'image_url': board.image_url
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# --- POST a new board ---
@boards_bp.route('/boards', methods=['POST'])
def add_board():
    data = request.json
    required_fields = ['project_id', 'board_name']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "project_id and board_name are required"}), 400
        
    try:
        # Check if the project exists before adding the board
        if not Projects.query.get(data['project_id']):
            return jsonify({"error": "Project not found"}), 404

        new_board = Boards(
            project_id=data['project_id'],
            board_name=data['board_name'],
            board_description=data.get('board_description'),
            image_url=data.get('image_url')
        )
        db.session.add(new_board)
        db.session.commit()
        return jsonify({'message': 'Board added successfully', 'board_id': new_board.board_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PUT (update) an existing board ---
@boards_bp.route('/boards/<string:board_id>', methods=['PUT'])
def update_board(board_id):
    data = request.json
    board = Boards.query.get_or_404(board_id)
    
    try:
        if 'board_name' in data:
            board.board_name = data['board_name']
        if 'board_description' in data:
            board.board_description = data['board_description']
        if 'image_url' in data:
            board.image_url = data['image_url']
            
        db.session.commit()
        return jsonify({'message': 'Board updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE a board ---
@boards_bp.route('/boards/<string:board_id>', methods=['DELETE'])
def delete_board(board_id):
    board = Boards.query.get_or_404(board_id)
    try:
        db.session.delete(board)
        db.session.commit()
        return jsonify({'message': 'Board deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
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