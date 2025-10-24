from flask import Flask, request, jsonify , Blueprint
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from models import db , TeamMembership
import uuid

# Initialize Flask App and SQLAlchemy (placeholders)
# app = Flask(__name__)
# db = SQLAlchemy(app) # Assume db is initialized elsewhere

# --- Utility Function Placeholder ---
def generate_uuid():
    """Generates a standard UUID-4 string."""
    return str(uuid.uuid4())

team_members_bp = Blueprint('team_members' , __name__)

# --- Placeholder TeamMembership Model ---
class TeamMembership(db.Model):
    __tablename__ = 'team_members'
    membership_id = db.Column(db.String(50), primary_key=True, default=generate_uuid, nullable=False) 
    team_id = db.Column(db.String(50), db.ForeignKey('teams.team_id'), nullable=False)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    team_role = db.Column(db.String(50), nullable=True) 
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    # team = db.relationship('Teams', back_populates='memberships')
    # member = db.relationship('User', back_populates='team_memberships')

    def to_dict(self):
        """Converts the TeamMembership object to a dictionary for JSON serialization."""
        return {
            'membership_id': self.membership_id,
            'team_id': self.team_id,
            'user_id': self.user_id,
            'team_role': self.team_role,
            'joined_at': self.joined_at.isoformat()
        }
    
@team_members_bp.route('/add_team_memberships', methods=['POST'])
def create_team_membership():
    data = request.get_json()

    # Basic validation for required fields
    required_fields = ['team_id', 'user_id']
    if not all(k in data for k in required_fields):
        return jsonify({"message": f"Missing required fields: {', '.join(required_fields)}"}), 400

    try:
        new_membership = TeamMembership(
            team_id=data['team_id'],
            user_id=data['user_id'],
            team_role=data.get('team_role'),
            # joined_at can be set from the request if provided, otherwise defaults to utcnow
            joined_at=datetime.fromisoformat(data['joined_at']) if 'joined_at' in data else None
        )

        db.session.add(new_membership)
        db.session.commit()
        return jsonify(new_membership.to_dict()), 201 # 201 Created

    except Exception as e:
        db.session.rollback()
        # Handle database constraints (like duplicate user/team combination if you add a unique constraint)
        return jsonify({"message": "Failed to create team membership", "error": str(e)}), 400
    
@team_members_bp.route('/get_team_memberships', methods=['GET'])
def get_all_team_memberships():
    memberships = TeamMembership.query.all()
    # Serialize the list of objects
    return jsonify([m.to_dict() for m in memberships]), 200

@team_members_bp.route('/api/team_memberships/<string:membership_id>', methods=['GET'])
def get_team_membership_by_id(membership_id):
    membership = TeamMembership.query.get(membership_id)

    if membership is None:
        return jsonify({"message": f"Team Membership with ID {membership_id} not found"}), 404

    return jsonify(membership.to_dict()), 200

@team_members_bp.route('/update_team_memberships/<string:membership_id>', methods=['PUT'])
def update_team_membership(membership_id):
    data = request.get_json()
    membership = TeamMembership.query.get(membership_id)

    if membership is None:
        return jsonify({"message": f"Team Membership with ID {membership_id} not found"}), 404

    try:
        # Update fields only if they exist in the incoming data
        # Note: Usually team_id and user_id are not changed in a PUT/PATCH, 
        # as a change implies a new membership, but we include them for completeness.
        if 'team_id' in data:
            membership.team_id = data['team_id']
        if 'user_id' in data:
            membership.user_id = data['user_id']
        if 'team_role' in data:
            membership.team_role = data['team_role']
        if 'joined_at' in data:
            membership.joined_at = datetime.fromisoformat(data['joined_at'])

        db.session.commit()
        return jsonify(membership.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update team membership", "error": str(e)}), 400
    
@team_members_bp.route('/del_team_memberships/<string:membership_id>', methods=['DELETE'])
def delete_team_membership(membership_id):
    membership = TeamMembership.query.get(membership_id)

    if membership is None:
        return jsonify({"message": f"Team Membership with ID {membership_id} not found"}), 404

    try:
        db.session.delete(membership)
        db.session.commit()
        # 204 No Content is standard for a successful DELETE
        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete team membership", "error": str(e)}), 500
    
@team_members_bp.route('/get_team_memberships/<string:membership_id>', methods=['GET'])
def get_team_membership_by_id(membership_id):
    # 1. Query the database using the primary key
    membership = TeamMembership.query.get(membership_id)

    # 2. Check if a membership was found
    if membership is None:
        # Return a 404 Not Found error if no membership exists
        return jsonify({"message": f"Team Membership with ID {membership_id} not found"}), 404

    # 3. Return the serialized membership object with a 200 OK status
    return jsonify(membership.to_dict()), 200