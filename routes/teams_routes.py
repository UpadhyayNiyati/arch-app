from flask import Blueprint, request, jsonify
from models import db , Teams
from datetime import datetime
import uuid
from decimal import Decimal
from flask_cors import CORS

#--- Utility Function Placeholder ---
def generate_uuid():
    """Generates a standard UUID-4 string."""
    return str(uuid.uuid4())

teams_bp = Blueprint('teams', __name__, url_prefix='/teams')
CORS(teams_bp)

@teams_bp.route('/post', methods=['POST'])
def create_team():
    # 1. Safely retrieve the JSON data
    # If the Content-Type header is missing, 'request.json' will be None.
    data = request.json
    
    # Check if data is None (due to missing Content-Type) or if required field is missing
    if data is None or 'team_name' not in data:
        return jsonify({
            "message": "Missing required fields or invalid JSON format. Ensure Content-Type is application/json."
        }), 400

    try:
        # 2. Create the new Teams object
        # .get() safely handles optional fields like 'description', 'phone_number', etc.
        new_team = Teams(
            team_name=data.get('team_name'),
            description=data.get('description'),
            phone_number=data.get('phone_number'),
            team_email=data.get('team_email')
            # owner_id=data['owner_id'] # Uncomment if you need this
        )

        # 3. Commit to database
        db.session.add(new_team)
        db.session.commit()
        
        return jsonify({
            "message": "Team created successfully", 
            "team_id": new_team.team_id
        }), 201 # 201 Created

    except Exception as e:
        db.session.rollback()
        # The 409 status code is often used for conflict/duplicate entry errors
        return jsonify({
            "message": "Failed to create team (Database Error)", 
            "error": str(e)
        }), 409
    

@teams_bp.route('/get', methods=['GET'])
def get_all_teams():
    teams = Teams.query.all()
    # Serialize the list
    teams_list = []
    for team in teams:
        teams_list.append({
            # 'team_id': team.team_id,
            'team_name': team.team_name,
            'description': team.description,
            'phone_number': team.phone_number,
            'team_email':team.team_email
            # 'created_at': team.created_at.isoformat(),
            # 'owner_id': team.owner_id
        })
    return jsonify(teams_list), 200

@teams_bp.route('/get/<team_id>', methods=['GET'])
def get_team(team_id):
    team = Teams.query.get(team_id)
    if not team:
        return jsonify({"message": "Team not found"}), 404

    team_data = {
        # 'team_id': team.team_id,
        'team_name': team.team_name,
        'description': team.description,
        'phone_number': team.phone_number,
        # 'created_at': team.created_at.isoformat(),
        'team_email':team.team_email
        # 'owner_id': team.owner_id
    }
    return jsonify(team_data), 200
@teams_bp.route('/update/<team_id>', methods=['PUT'])
def update_team(team_id):
    data = request.json
    team = Teams.query.get(team_id)

    if not team:
        return jsonify({"message": "Team not found"}), 404

    try:
        team.team_name = data.get('team_name', team.team_name)
        team.description = data.get('description', team.description)
        team.phone_number = data.get('phone_number', team.phone_number)
        db.session.commit()
        return jsonify({"message": "Team updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update team", "error": str(e)}), 400
    
@teams_bp.route('/delete/<team_id>', methods=['DELETE'])
def delete_team(team_id):
    team = Teams.query.get(team_id)

    if not team:
        return jsonify({"message": "Team not found"}), 404

    try:
        db.session.delete(team)
        db.session.commit()
        return jsonify({"message": "Team deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete team", "error": str(e)}), 400
    
# @teams_bp.route('/owner/<owner_id>', methods=['GET'])
# def get_teams_by_owner(owner_id):
#     teams = Teams.query.filter_by(owner_id=owner_id).all()
#     teams_list = []
#     for team in teams:
#         teams_list.append({
#             'team_id': team.team_id,
#             'team_name': team.team_name,
#             'description': team.description,
#             'phone_number': team.phone_number,
#             'created_at': team.created_at.isoformat(),
#             'owner_id': team.owner_id
#         })
#     return jsonify(teams_list), 200

# @teams_bp.route('/owner/<owner_id>/count', methods=['GET'])
# def count_teams_by_owner(owner_id):
#     count = Teams.query.filter_by(owner_id=owner_id).count()
#     return jsonify({"owner_id": owner_id, "team_count": count}), 200
# @teams_bp.route('/search', methods=['GET'])
# def search_teams():
#     name_query = request.args.get('name')
#     if not name_query:
#         return jsonify({"message": "Missing 'name' query parameter"}), 400

#     teams = Teams.query.filter(Teams.team_name.ilike(f'%{name_query}%')).all()
#     teams_list = []
#     for team in teams:
#         teams_list.append({
#             'team_id': team.team_id,
#             'team_name': team.team_name,
#             'description': team.description,
#             'phone_number': team.phone_number,
#             'created_at': team.created_at.isoformat(),
#             'owner_id': team.owner_id
#         })
#     return jsonify(teams_list), 200

# @teams_bp.route('/recent/<int:limit>', methods=['GET'])
# def get_recent_teams(limit):
#     teams = Teams.query.order_by(Teams.created_at.desc()).limit(limit).all()
#     teams_list = []
#     for team in teams:
#         teams_list.append({
#             'team_id': team.team_id,
#             'team_name': team.team_name,
#             'description': team.description,
#             'phone_number': team.phone_number,
#             'created_at': team.created_at.isoformat(),
#             'owner_id': team.owner_id
#         })
#     return jsonify(teams_list), 200

# @teams_bp.route('/count', methods=['GET'])
# def get_total_team_count():
#     count = Teams.query.count()
#     return jsonify({"total_team_count": count}), 200
# @teams_bp.route('/owner/<owner_id>/recent/<int:limit>', methods=['GET'])
# def get_recent_teams_by_owner(owner_id, limit):
#     teams = Teams.query.filter_by(owner_id=owner_id).order_by(Teams.created_at.desc()).limit(limit).all()
#     teams_list = []
#     for team in teams:
#         teams_list.append({
#             'team_id': team.team_id,
#             'team_name': team.team_name,
#             'description': team.description,
#             'phone_number': team.phone_number,
#             'created_at': team.created_at.isoformat(),
#             'owner_id': team.owner_id
#         })
#     return jsonify(teams_list), 200

# @teams_bp.route('/owner/<owner_id>/search', methods=['GET'])
# def search_teams_by_owner(owner_id):
#     name_query = request.args.get('name')
#     if not name_query:
#         return jsonify({"message": "Missing 'name' query parameter"}), 400

#     teams = Teams.query.filter(Teams.owner_id == owner_id, Teams.team_name.ilike(f'%{name_query}%')).all()
#     teams_list = []
#     for team in teams:
#         teams_list.append({
#             'team_id': team.team_id,
#             'team_name': team.team_name,
#             'description': team.description,
#             'phone_number': team.phone_number,
#             'created_at': team.created_at.isoformat(),
#             'owner_id': team.owner_id
#         })
#     return jsonify(teams_list), 200

# #--- End of teams_routes.py ---#




