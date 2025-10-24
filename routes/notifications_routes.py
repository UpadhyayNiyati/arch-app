from flask import Blueprint, jsonify, request
from models import Notification, User, db , Projects ,ProjectAssignments , Tasks
from datetime import datetime
import uuid

notifications_bp = Blueprint('notifications', __name__)

# # --- GET all notifications (typically for a specific user) ---
# @notifications_bp.route('/notifications', methods=['GET'])
# def get_all_notifications():
#     try:
#         notifications = Notification.query.all()
#         result = []
#         for n in notifications:
#             result.append({
#                 'notification_id': n.notification_id,
#                 'user_id': n.user_id,
#                 'message': n.message,
#                 'read_status': n.read_status,
#                 'created_at': n.created_at.isoformat()
#             })
#         return jsonify(result), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # --- GET a single notification by ID ---
# @notifications_bp.route('/notifications/<string:notification_id>', methods=['GET'])
# def get_one_notification(notification_id):
#     try:
#         notification = Notification.query.get_or_404(notification_id)
#         result = {
#             'notification_id': notification.notification_id,
#             'user_id': notification.user_id,
#             'message': notification.message,
#             'read_status': notification.read_status,
#             'created_at': notification.created_at.isoformat()
#         }
#         return jsonify(result), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # --- POST a new notification (typically by the application's internal logic) ---
# @notifications_bp.route('/notifications', methods=['POST'])
# def add_notification():
#     data = request.json
#     required_fields = ['user_id', 'message']
    
#     if not all(field in data for field in required_fields):
#         return jsonify({"error": "user_id and message are required"}), 400
        
#     try:
#         if not User.query.get(data['user_id']):
#             return jsonify({"error": "User not found"}), 404

#         new_notification = Notification(
#             user_id=data['user_id'],
#             message=data['message'],
#             read_status=data.get('read_status', False)
#         )
#         db.session.add(new_notification)
#         db.session.commit()
#         return jsonify({'message': 'Notification added successfully', 'notification_id': new_notification.notification_id}), 201
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

# # --- PUT (update) an existing notification (e.g., mark as read) ---
# @notifications_bp.route('/notifications/<string:notification_id>', methods=['PUT'])
# def update_notification(notification_id):
#     data = request.json
#     notification = Notification.query.get_or_404(notification_id)
    
#     try:
#         # The primary field to update is usually 'read_status'
#         if 'message' in data:
#             notification.message = data['message']
#         if 'read_status' in data:
#             notification.read_status = data['read_status']
            
#         db.session.commit()
#         return jsonify({'message': 'Notification updated successfully'}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

# # --- DELETE a notification ---
# @notifications_bp.route('/notifications/<string:notification_id>', methods=['DELETE'])
# def delete_notification(notification_id):
#     notification = Notification.query.get_or_404(notification_id)
#     try:
#         db.session.delete(notification)
#         db.session.commit()
#         return jsonify({'message': 'Notification deleted successfully'}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

def get_client_user_id_for_project(project_id):
    """Retrieves the User ID of the client assigned to a specific project."""
    # Find the assignment where the role is 'client' for the given project
    client_assignment = ProjectAssignments.query.filter_by(
        project_id=project_id,
        role='client' # Assuming the client is identified by role='client'
    ).first()
    
    if client_assignment:
        # The user_id in ProjectAssignments links to the Clients model which links to the User model.
        # Assuming ProjectAssignments directly links to the User.
        return client_assignment.user_id
    return None

# --- NEW: Route to send completion status notification to the client ---
@notifications_bp.route('/notify_completion/<string:project_id>', methods=['POST'])
def send_completion_notification(project_id):
    try:
        project = Projects.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # 1. Get the Client's User ID
        client_user_id = get_client_user_id_for_project(project_id)
        if not client_user_id:
            return jsonify({"error": "Client not assigned to this project"}), 404
        
        # 2. Query all tasks for the project
        tasks = Tasks.query.filter_by(project_id=project_id).all()
        
        if not tasks:
            # Send notification that the project has no tasks yet
            message = f"Project '{project.project_name}' has been created but no tasks have been assigned yet."
            completion_percentage = 0
        else:
            # 3. Calculate completion status
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks if task.status.lower() == 'completed')
            completion_percentage = (completed_tasks / total_tasks) * 100
            
            # 4. Format the message
            message = (
                f"The task status for your project '{project.project_name}' has been updated. "
                f"Completion is now at {completion_percentage:.2f}%. "
                f"({completed_tasks} out of {total_tasks} tasks completed)."
            )

        # 5. Create the Notification record
        new_notification = Notification(
            user_id=client_user_id,
            message=message,
            read_status=False
        )
        db.session.add(new_notification)
        db.session.commit()
        
        return jsonify({
            'message': 'Completion notification sent successfully', 
            'project_name': project.project_name,
            'completion_percentage': f"{completion_percentage:.2f}%",
            'notification_id': new_notification.notification_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to send notification: {str(e)}"}), 500

# --- EXISTING ROUTES (Retained for completeness) ---

# --- GET all notifications (typically for a specific user) ---
@notifications_bp.route('/notifications', methods=['GET'])
def get_all_notifications():
    try:
        notifications = Notification.query.all()
        result = []
        for n in notifications:
            result.append({
                'notification_id': n.notification_id,
                'user_id': n.user_id,
                'message': n.message,
                'read_status': n.read_status,
                'created_at': n.created_at.isoformat()
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GET a single notification by ID ---
@notifications_bp.route('/notifications/<string:notification_id>', methods=['GET'])
def get_one_notification(notification_id):
    try:
        notification = Notification.query.get_or_404(notification_id)
        result = {
            'notification_id': notification.notification_id,
            'user_id': notification.user_id,
            'message': notification.message,
            'read_status': notification.read_status,
            'created_at': notification.created_at.isoformat()
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new notification (typically by the application's internal logic) ---
@notifications_bp.route('/notifications', methods=['POST'])
def add_notification():
    data = request.json
    required_fields = ['user_id', 'message']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "user_id and message are required"}), 400
        
    try:
        if not User.query.get(data['user_id']):
            return jsonify({"error": "User not found"}), 404

        new_notification = Notification(
            user_id=data['user_id'],
            message=data['message'],
            read_status=data.get('read_status', False)
        )
        db.session.add(new_notification)
        db.session.commit()
        return jsonify({'message': 'Notification added successfully', 'notification_id': new_notification.notification_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PUT (update) an existing notification (e.g., mark as read) ---
@notifications_bp.route('/notifications/<string:notification_id>', methods=['PUT'])
def update_notification(notification_id):
    data = request.json
    notification = Notification.query.get_or_404(notification_id)
    
    try:
        # The primary field to update is usually 'read_status'
        if 'message' in data:
            notification.message = data['message']
        if 'read_status' in data:
            notification.read_status = data['read_status']
            
        db.session.commit()
        return jsonify({'message': 'Notification updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE a notification ---
@notifications_bp.route('/notifications/<string:notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    try:
        db.session.delete(notification)
        db.session.commit()
        return jsonify({'message': 'Notification deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
