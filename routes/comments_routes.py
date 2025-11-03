from flask import Blueprint, jsonify, request
from models import Comment, User, Boards, Pin, db
from datetime import datetime
import uuid
from flask_cors import CORS

comments_bp = Blueprint('comments', __name__)

CORS(comments_bp)

# --- GET all comments ---
@comments_bp.route('/comments', methods=['GET'])
def get_all_comments():
    try:
        comments = Comment.query.all()
        result = []
        for comment in comments:
            result.append({
                'comment_id': comment.comment_id,
                'pin_id': comment.pin_id,
                'board_id': comment.board_id,
                'user_id': comment.user_id,
                'comment_text': comment.comment_text,
                'created_at': comment.created_at.isoformat()
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GET a single comment by ID ---
@comments_bp.route('/comments/<string:comment_id>', methods=['GET'])
def get_one_comment(comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        result = {
            'comment_id': comment.comment_id,
            'pin_id': comment.pin_id,
            'board_id': comment.board_id,
            'user_id': comment.user_id,
            'comment_text': comment.comment_text,
            'created_at': comment.created_at.isoformat()
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new comment ---
@comments_bp.route('/comments', methods=['POST'])
def add_comment():
    data = request.json
    required_fields = ['board_id', 'user_id', 'comment_text']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "board_id, user_id, and comment_text are required"}), 400
        
    try:
        # Check if the board and user exist before creating the comment
        if not Boards.query.get(data['board_id']):
            return jsonify({"error": "Board not found"}), 404
        if not User.query.get(data['user_id']):
            return jsonify({"error": "User not found"}), 404
        if data.get('pin_id') and not Pin.query.get(data['pin_id']):
            return jsonify({"error": "Pin not found"}), 404

        new_comment = Comment(
            pin_id=data.get('pin_id'),
            board_id=data['board_id'],
            user_id=data['user_id'],
            comment_text=data['comment_text']
        )
        db.session.add(new_comment)
        db.session.commit()
        return jsonify({'message': 'Comment added successfully', 'comment_id': new_comment.comment_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PUT (update) an existing comment ---
@comments_bp.route('/comments/<string:comment_id>', methods=['PUT'])
def update_comment(comment_id):
    data = request.json
    comment = Comment.query.get_or_404(comment_id)
    
    try:
        if 'comment_text' in data:
            comment.comment_text = data['comment_text']
            
        db.session.commit()
        return jsonify({'message': 'Comment updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE a comment ---
@comments_bp.route('/comments/<string:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'message': 'Comment deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500