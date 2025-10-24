from flask import Blueprint,Flask, jsonify , request
from models import ActivityLog, db

activity_log_bp = Blueprint('ActivityLog' , __name__)

@activity_log_bp.route('/activity_logs/<log_id>', methods=['GET'])
def get_log_by_id(log_id):
    log = ActivityLog.query.get(log_id)
    if log:
        return jsonify({
            'log_id': log.log_id,
            'user_id': log.user_id,
            'action': log.action,
            'target_entity': log.target_entity,
            'target_id': log.target_id,
            'timestamp': log.timestamp.isoformat()
        })
    return jsonify({'error': 'Log not found'}), 404


@activity_log_bp.route('/activity_logs', methods=['GET'])
def get_all_logs():
    query = ActivityLog.query
    user_id = request.args.get('user_id')
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    logs = query.order_by(ActivityLog.timestamp.desc()).all()
    
    return jsonify([{
        'log_id': log.log_id,
        'user_id': log.user_id,
        'action': log.action,
        'target_entity': log.target_entity,
        'target_id': log.target_id,
        'timestamp': log.timestamp.isoformat()
    } for log in logs])



@activity_log_bp.route('/activity_logs', methods=['POST'])
def create_log():
    data = request.get_json()
    if not data or not all(key in data for key in ['user_id', 'action', 'target_entity', 'target_id']):
        return jsonify({'error': 'Missing data'}), 400

    new_log = ActivityLog(
        user_id=data['user_id'],
        action=data['action'],
        target_entity=data['target_entity'],
        target_id=data['target_id']
    )
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify({
        'message': 'Log created successfully',
        'log_id': new_log.log_id
    }), 201

# This route is not recommended for an audit log.
@activity_log_bp.route('/activity_logs/<log_id>', methods=['PUT'])
def update_log(log_id):
    return jsonify({'error': 'Log entries cannot be updated'}), 403

# This route is not recommended for an audit log.
@activity_log_bp.route('/activity_logs/<log_id>', methods=['DELETE'])
def delete_log(log_id):
    return jsonify({'error': 'Log entries cannot be deleted'}), 403