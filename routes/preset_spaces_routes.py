from flask import Blueprint, request, jsonify, current_app
from models import db, Spaces , Upload_Files , Drawings , Preset , Projects ,  Tasks , PresetSpace 
from sqlalchemy.orm.exc import NoResultFound
from auth.authhelpers import jwt_required
import logging
import os
import json
from sqlalchemy import distinct, func
from utils.email_utils import send_email

preset_spaces_bp = Blueprint('PresetSpaces' , __name__)


# @preset_spaces_bp.route('/preset-spaces', methods=['GET'])
# @jwt_required
# def get_preset_spaces():
#     try:
#         preset_spaces = PresetSpace.query.all()
#         result = []
#         for ps in preset_spaces:
#             result.append({
#                 "preset_space_id": ps.preset_space_id,
#                 "preset_id": ps.preset_id,
#                 "space_id": ps.space_id,
#                 "space_name": ps.space_name,
#                 "space_type": ps.space_type,
#                 "description": ps.description
#             })
#         return jsonify(result), 200

#     except Exception as e:
#         logging.error(f"Error fetching preset spaces: {e}")
#         return jsonify({"message": "Internal server error"}), 500

    

# @preset_spaces_bp.route('/preset-spaces/<int:preset_space_id>', methods=['GET'])
# @jwt_required
# def get_preset_space(preset_space_id):
#     try:
#         ps = PresetSpace.query.get(preset_space_id)
#         if not ps:
#             return jsonify({"message": "Preset space not found"}), 404

#         result = {
#             "preset_space_id": ps.preset_space_id,
#             "preset_id": ps.preset_id,
#             "space_id": ps.space_id,
#             "space_name": ps.space_name,
#             "space_type": ps.space_type,
#             "description": ps.description
#         }
#         return jsonify(result), 200

#     except Exception as e:
#         logging.error(f"Error fetching preset space: {e}")
#         return jsonify({"message": "Internal server error"}), 500
    
# @preset_spaces_bp.route('/preset-spaces', methods=['POST'])
# @jwt_required
# def create_preset_space():
#     try:
#         data = request.get_json()

#         new_ps = PresetSpace(
#             preset_id=data.get("preset_id"),
#             space_id=data.get("space_id"),
#             space_name=data.get("space_name"),
#             space_type=data.get("space_type"),
#             description=data.get("description")
#         )

#         db.session.add(new_ps)
#         db.session.commit()

#         return jsonify({
#             "message": "Preset space created",
#             "preset_space_id": new_ps.preset_space_id
#         }), 201

#     except Exception as e:
#         logging.error(f"Error creating preset space: {e}")
#         return jsonify({"message": "Internal server error"}), 500
    
# @preset_spaces_bp.route('/preset-spaces/<int:preset_space_id>', methods=['PUT'])
# @jwt_required
# def update_preset_space(preset_space_id):
#     try:
#         ps = PresetSpace.query.get(preset_space_id)
#         if not ps:
#             return jsonify({"message": "Preset space not found"}), 404

#         data = request.get_json()

#         ps.preset_id = data.get("preset_id", ps.preset_id)
#         ps.space_id = data.get("space_id", ps.space_id)
#         ps.space_name = data.get("space_name", ps.space_name)
#         ps.space_type = data.get("space_type", ps.space_type)
#         ps.description = data.get("description", ps.description)

#         db.session.commit()

#         return jsonify({"message": "Preset space updated"}), 200

#     except Exception as e:
#         logging.error(f"Error updating preset space: {e}")
#         return jsonify({"message": "Internal server error"}), 500

# @preset_spaces_bp.route('/preset-spaces/<int:preset_space_id>', methods=['DELETE'])
# @jwt_required
# def delete_preset_space(preset_space_id):
#     try:
#         ps = PresetSpace.query.get(preset_space_id)
#         if not ps:
#             return jsonify({"message": "Preset space not found"}), 404

#         db.session.delete(ps)
#         db.session.commit()

#         return jsonify({"message": "Preset space deleted"}), 200

#     except Exception as e:
#         logging.error(f"Error deleting preset space: {e}")
#         return jsonify({"message": "Internal server error"}), 500


@preset_spaces_bp.route('/create-preset', methods=['POST'])
@jwt_required
def create_preset():
    data = request.get_json()

    preset_name = data.get("preset_name")
    preset_description = data.get("preset_description")
    preset_type = data.get("preset_type")

    if not preset_name:
        return jsonify({"error": "preset_name is required"}), 400

    new_preset = Preset(
        preset_name=preset_name,
        preset_description=preset_description,
        preset_type=preset_type
    )

    db.session.add(new_preset)
    db.session.commit()

    return jsonify({
        "message": "Preset created successfully",
        "preset_id": new_preset.preset_id,
        "preset_name": new_preset.preset_name,
        "preset_description": new_preset.preset_description,
        "preset_type": new_preset.preset_type
    }), 201



@preset_spaces_bp.route('/create-preset-space', methods=['POST'])
@jwt_required
def create_preset_space():
    data = request.get_json()

    preset_id = data.get("preset_id")
    space_name = data.get("space_name")
    space_type = data.get("space_type")
    description = data.get("description")

    if not preset_id or not space_name:
        return jsonify({"error": "preset_id and space_name are required"}), 400

    new_space = PresetSpace(
        preset_id=preset_id,
        space_name=space_name,
        space_type=space_type,
        description=description
    )

    db.session.add(new_space)
    db.session.commit()

    return jsonify({
        "message": "Preset space created successfully",
        "preset_space_id": new_space.preset_space_id,
        "preset_id": new_space.preset_id,
        "space_name": new_space.space_name,
        "space_type": new_space.space_type,
        "description": new_space.description
    }), 201


@preset_spaces_bp.route('/get-preset-spaces/<preset_id>', methods=['GET'])
@jwt_required
def get_preset_spaces(preset_id):

    spaces = PresetSpace.query.filter_by(preset_id=preset_id).all()

    result = []
    for s in spaces:
        result.append({
            "preset_space_id": s.preset_space_id,
            "space_name": s.space_name,
            "space_type": s.space_type,
            "description": s.description,
        
        })

    return jsonify(result), 200


@preset_spaces_bp.route('/get-all-presets', methods=['GET'])
@jwt_required
def get_all_presets():
    try:
        # 1. Query the Preset table for all records
        all_presets = Preset.query.all()

        result = []
        for p in all_presets:
            # 2. For each Preset, find all associated PresetSpace records
            spaces = PresetSpace.query.filter_by(preset_id=p.preset_id).all()
            
            # Format the list of spaces
            spaces_list = []
            for s in spaces:
                spaces_list.append({
                    "preset_space_id": s.preset_space_id,
                    "space_name": s.space_name,
                    "space_type": s.space_type,
                    "description": s.description,
                })
            
            # 3. Append the Preset data along with the nested spaces list
            result.append({
                "preset_id": p.preset_id,
                "preset_name": p.preset_name,
                "preset_description": p.preset_description,
                "preset_type": p.preset_type,
                "spaces": spaces_list  # Include the list of spaces here
            })

        return jsonify(result), 200

    except Exception as e:
        # Log the error
        logging.error(f"Error fetching all presets with spaces: {e}")
        return jsonify({"message": "Internal server error"}), 500