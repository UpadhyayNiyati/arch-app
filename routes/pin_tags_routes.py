from flask import Blueprint, jsonify, request
from models import PinTag, Pin, Tag, db
import uuid

pin_tags_bp = Blueprint('pin_tags', __name__)

# --- POST: Assign a tag to a pin ---
@pin_tags_bp.route('/pin_tags', methods=['POST'])
def add_pin_tag():
    data = request.json
    pin_id = data.get('pin_id')
    tag_id = data.get('tag_id')
    
    if not all([pin_id, tag_id]):
        return jsonify({"error": "pin_id and tag_id are required"}), 400
    
    try:
        # Check if the pin and tag exist to prevent a foreign key error
        if not Pin.query.get(pin_id):
            return jsonify({"error": "Pin not found"}), 404
        if not Tag.query.get(tag_id):
            return jsonify({"error": "Tag not found"}), 404
        
        # Prevent duplicate entries
        if PinTag.query.filter_by(pin_id=pin_id, tag_id=tag_id).first():
            return jsonify({"message": "This tag is already assigned to this pin"}), 409

        new_pin_tag = PinTag(pin_id=pin_id, tag_id=tag_id)
        db.session.add(new_pin_tag)
        db.session.commit()
        return jsonify({'message': 'Tag assigned to pin successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- GET all pin-tag assignments ---
@pin_tags_bp.route('/pin_tags', methods=['GET'])
def get_all_pin_tags():
    try:
        assignments = PinTag.query.all()
        result = []
        for assignment in assignments:
            result.append({
                'pin_id': assignment.pin_id,
                'tag_id': assignment.tag_id
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- DELETE a pin-tag assignment ---
@pin_tags_bp.route('/pin_tags', methods=['DELETE'])
def delete_pin_tag():
    data = request.json
    pin_id = data.get('pin_id')
    tag_id = data.get('tag_id')
    
    if not all([pin_id, tag_id]):
        return jsonify({"error": "pin_id and tag_id are required"}), 400
        
    assignment = PinTag.query.filter_by(pin_id=pin_id, tag_id=tag_id).first()
    
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
        
    try:
        db.session.delete(assignment)
        db.session.commit()
        return jsonify({'message': 'Tag removed from pin successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500