from flask import Blueprint, jsonify, request
from models import Tag, PinTag, db
import uuid
import datetime

tags_bp = Blueprint('tags', __name__)

# --- GET all tags ---
@tags_bp.route('/tags', methods=['GET'])
def get_all_tags():
    try:
        tags = Tag.query.all()
        result = []
        for tag in tags:
            result.append({
                'tag_id': tag.tag_id,
                'tag_name': tag.tag_name
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GET a single tag by ID ---
@tags_bp.route('/tags/<string:tag_id>', methods=['GET'])
def get_one_tag(tag_id):
    try:
        tag = Tag.query.get_or_404(tag_id)
        result = {
            'tag_id': tag.tag_id,
            'tag_name': tag.tag_name
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new tag ---
@tags_bp.route('/tags', methods=['POST'])
def add_tag():
    data = request.json
    tag_name = data.get('tag_name')
    
    if not tag_name:
        return jsonify({"error": "Tag name is required"}), 400
        
    try:
        new_tag = Tag(tag_name=tag_name)
        db.session.add(new_tag)
        db.session.commit()
        return jsonify({'message': 'Tag added successfully', 'tag_id': new_tag.tag_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PUT (update) an existing tag ---
@tags_bp.route('/tags/<string:tag_id>', methods=['PUT'])
def update_tag(tag_id):
    data = request.json
    tag = Tag.query.get_or_404(tag_id)
    
    try:
        if 'tag_name' in data:
            tag.tag_name = data['tag_name']
            
        db.session.commit()
        return jsonify({'message': 'Tag updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE a tag ---
@tags_bp.route('/tags/<string:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    try:
        # Check if the tag is assigned to any pins before deleting
        if PinTag.query.filter_by(tag_id=tag_id).first():
            return jsonify({"error": "Cannot delete tag; it is still in use."}), 409

        db.session.delete(tag)
        db.session.commit()
        return jsonify({'message': 'Tag deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500