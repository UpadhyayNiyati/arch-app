from flask import Blueprint , jsonify , request
from models import Clients , db , Projects ,Tasks , Projectvendor , Vendors , OtpCode , User
from flask_jwt_extended import JWTManager , create_access_token , get_jwt_identity  , jwt_required
from werkzeug.security import generate_password_hash , check_password_hash
from email.message import EmailMessage
from datetime import datetime , timedelta , timezone
from auth.auth import jwt_required
import os
import smtplib
import datetime
import random
import uuid
import logging
from flask_cors import CORS

clients_bp = Blueprint('clients', __name__)

CORS(clients_bp)

# def send_email(recipients, subject, body):
#     msg = EmailMessage()
#     msg['Subject'] = subject
#     msg['From'] = os.getenv('EMAIL_SENDER')
#     msg['To'] = ', '.join(recipients)
#     msg.set_content(body)
#     with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
#         smtp.starttls()
#         smtp.login(os.getenv('EMAIL_SENDER'), os.getenv('EMAIL_PASSWORD'))
#         smtp.send_message(msg)

#get all clients
@clients_bp.route('/get_clients', methods=['GET'])
@jwt_required
def get_all_clients():
    """
    Retrieves a list of all clients.
    ---
    tags:
      - Client Management
    security:
      - bearerAuth: []
    responses:
      200:
        description: A list of all clients.
        schema:
          type: array
          items:
            type: object
            properties:
              client_id:
                type: integer
              client_name:
                type: string
              client_email:
                type: string
              client_phone:
                type: string
              client_address:
                type: string
              client_password:
                type: string
      500:
        description: Server error.
    """
    try:

        clients = Clients.query.all()
        result = []

        for client in clients:
            result.append({
                'client_id': client.client_id,
                'client_name': client.client_name,
                'client_email': client.client_email,
                'client_phone': client.client_phone,
                'client_address': client.client_address,
                'client_password':client.client_password,
                # 'created_at': client.created_at,
                # 'updated_at': client.updated_at,
            })

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        

#get single client by id
@clients_bp.route('/get_one_clients/<string:client_id>' , methods = ['GET'])
@jwt_required
def get_client_by_id(client_id):
    """
    Retrieves a single client by their ID.
    ---
    tags:
      - Client Management
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: client_id
        type: string
        required: true
        description: The ID of the client to retrieve.
    responses:
      200:
        description: Client data retrieved successfully.
        schema:
          type: object
          properties:
            client_id:
              type: string
            client_name:
              type: string
            client_email:
              type: string
            client_phone:
              type: string
            client_address:
              type: string
            user_id:
              type: integer
            client_password:
              type: string
      404:
        description: Client not found.
    """
    client = Clients.query.get_or_404(client_id)
    if not client:
        return jsonify({"message":"Client not found"}) , 404
    result = {
        'client_id' : client.client_id , 
        'client_name' : client.client_name , 
        'client_email' : client.client_email , 
        'client_phone ': client.client_phone , 
        'client_address' : client.client_address , 
        'user_id' : client.user_id,
        'client_password':client.client_password
    }
    return jsonify(result) , 200
    
#post client
@clients_bp.route('/post_client', methods=['POST'])
@jwt_required
def add_client():
    """
    Adds a new client profile (requires a pre-existing user_id).
    NOTE: For full registration, use the /register route.
    ---
    tags:
      - Client Management
    security:
      - bearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: client
        description: Client data to be added.
        required: true
        schema:
          type: object
          required: [client_name, client_email, client_phone, client_address, user_id, client_password]
          properties:
            client_name:
              type: string
            client_email:
              type: string
            client_phone:
              type: string
            client_address:
              type: string
            user_id:
              type: integer
            client_password:
              type: string
    responses:
      201:
        description: Client added successfully!
      400:
        description: Missing required fields.
      500:
        description: Server error.
    """
    data = request.json
    required_fields = ['client_name', 'client_email', 'client_phone', 'client_address' , 'client_password']
    
    # Check if all required fields are present
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"'{field}' is required"}), 400
            
    # If all fields are present, attempt to add the new client
    try:
        new_client = Clients (

            client_name=data['client_name'],
            client_email=data['client_email'],
            client_phone=data['client_phone'],
            client_address=data['client_address'] , 
            user_id = data['user_id'],  # Assuming user_id is provided in the request
            client_password = data['client_password']
        )
        db.session.add(new_client)
        db.session.commit()
        return jsonify({"message": "Client added successfully!"}), 201  # Changed to 201 Created status
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clients_bp.route('/update_client/<string:client_id>', methods=['PUT', 'PATCH'])
@jwt_required
def update_client(client_id):
    """
    Updates client details based on the provided client_id (partial updates supported).
    NOTE: Password updates should ideally be handled by a separate, secure route.
    ---
    tags:
      - Client Management
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: client_id
        type: string
        required: true
        description: The ID of the client to update.
      - in: body
        name: client_data
        description: Fields to update for the client.
        required: true
        schema:
          type: object
          properties:
            client_name:
              type: string
            client_email:
              type: string
            client_phone:
              type: string
            client_address:
              type: string
            client_password:
              type: string
    responses:
      200:
        description: Client updated successfully.
      404:
        description: Client not found.
      500:
        description: Internal server error.
    """
    data = request.get_json()
    
    # 1. Find the client by their primary key
    client = Clients.query.get(client_id)
    
    if not client:
        return jsonify({'message': 'Client not found'}), 404

    # 2. Modify the attributes based on the received data
    
    # The .get() method safely retrieves a value from the dictionary, returning None if the key doesn't exist.
    # This allows partial updates (PATCH).
    
    # Simple Fields
    if 'client_name' in data:
        client.client_name = data['client_name']
        
    if 'client_email' in data:
        client.client_email = data['client_email']
        
    if 'client_phone' in data:
        client.client_phone = data['client_phone']
        
    if 'client_address' in data:
        client.client_address = data['client_address']
        
    # Security Note: Updating the password should involve hashing it *before* assignment.
    # if 'client_password' in data:
    #     client.client_password = generate_password_hash(data['client_password']) 

    # 3. Commit the changes
    try:
        db.session.commit()
        return jsonify({
            'message': 'Client updated successfully',
            'client_id': client.client_id,
            'client_name': client.client_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        # Handle unique constraint errors (e.g., duplicate email or phone)
        # In a real app, you'd check the error type more specifically.
        if 'UNIQUE constraint failed' in str(e):
             return jsonify({'message': 'Update failed: Email or phone number already exists.'}), 400
        
        return jsonify({'message': f'An error occurred: {e}'}), 500
    
#delete client
@clients_bp.route('/del/client/<string:client_id>' , methods = ['DELETE'])
@jwt_required
def del_client(client_id):
    """
    Deletes a client profile by ID.
    ---
    tags:
      - Client Management
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: client_id
        type: string
        required: true
        description: The ID of the client to delete.
    responses:
      200:
        description: Client deleted successfully.
      404:
        description: Client not found.
      500:
        description: Internal server error.
    """
    client = Clients.query.get_or_404(client_id)
    if not client:
        return jsonify({"message" : "Client not found"}) , 404
    db.session.delete(client)
    db.session.commit()



@clients_bp.route('/dashboard/<string:client_id>', methods=['GET'])
@jwt_required
# @jwt_required() # You might want to protect this route with authentication
def get_client_dashboard(client_id):
    """
    Retrieves dashboard data for a specific client, including all their projects, 
    tasks, and assigned vendors.
    ---
    tags:
      - Client Dashboard
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: client_id
        type: string
        required: true
        description: The ID of the client whose dashboard to retrieve.
    responses:
      200:
        description: Client dashboard data retrieved successfully.
        schema:
          type: array
          items:
            type: object
            properties:
              project_id:
                type: string
              project_name:
                type: string
              project_status:
                type: string
              total_tasks:
                type: integer
              completed_tasks:
                type: integer
              project_tasks:
                type: array
                items:
                  type: object
                  properties:
                    task_name:
                      type: string
                    status:
                      type: string
                    due_date:
                      type: string
                      format: date-time
              assigned_vendors:
                type: array
                items:
                  type: object
                  properties:
                    company_name:
                      type: string
                    role:
                      type: string
                    tasks_assigned:
                      type: array
                      items:
                        type: object
      404:
        description: Client not found.
      500:
        description: Internal server error.
    """

    try:
        # Check if the client exists
        client = Clients.query.get(client_id)
        if not client:
            return jsonify({"message": "Client not found."}), 404

        # Query all projects for this specific client
        projects = Projects.query.filter_by(client_id=client_id).all()
        dashboard_data = []

        # Iterate through each project the client owns
        for project in projects:
            # --- Get all tasks for this project ---
            tasks = Tasks.query.filter_by(project_id=project.project_id).all()
            task_list = []
            completed_tasks_count = 0
            for task in tasks:
                if task.status.lower() == 'completed':
                    completed_tasks_count += 1
                
                # Client-facing task details
                task_list.append({
                    "task_name": task.task_name,
                    "status": task.status,
                    "due_date": task.due_date.isoformat()
                })

            # --- Get all vendors for this project ---
            project_vendors = Projectvendor.query.filter_by(project_id=project.project_id).all()
            vendor_list = []
            for pv in project_vendors:
                vendor = Vendors.query.get(pv.vendor_id)
                if vendor:
                    # Find tasks specifically assigned to this vendor
                    vendor_tasks = Tasks.query.filter_by(project_id=project.project_id, assigned_to=pv.vendor_id).all()
                    vendor_task_list = []
                    for task in vendor_tasks:
                        vendor_task_list.append({
                            "task_name": task.task_name,
                            "status": task.status,
                            "due_date": task.due_date.isoformat()
                        })

                    vendor_list.append({
                        "company_name": vendor.company_name,
                        "role": pv.role,
                        "tasks_assigned": vendor_task_list
                    })

            # Combine all the data for this project
            project_data = {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "project_description": project.project_description,
                "project_status": project.status,
                "total_tasks": len(tasks),
                "completed_tasks": completed_tasks_count,
                "project_tasks": task_list,
                "assigned_vendors": vendor_list
            }
            dashboard_data.append(project_data)

        return jsonify(dashboard_data), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
