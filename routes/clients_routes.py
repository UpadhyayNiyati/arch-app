from flask import Blueprint , jsonify , request
from models import Clients , db , Projects ,Tasks , Projectvendor , Vendors , OtpCode , User
from flask_jwt_extended import JWTManager , create_access_token , get_jwt_identity  , jwt_required
from werkzeug.security import generate_password_hash , check_password_hash
from email.message import EmailMessage
from datetime import datetime , timedelta , timezone
import os
import smtplib
import datetime
import random
import uuid
import logging
from flask_cors import CORS

clients_bp = Blueprint('clients', __name__)

CORS(clients_bp)

def send_email(recipients, subject, body):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = os.getenv('EMAIL_SENDER')
    msg['To'] = ', '.join(recipients)
    msg.set_content(body)
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.login(os.getenv('EMAIL_SENDER'), os.getenv('EMAIL_PASSWORD'))
        smtp.send_message(msg)

#get all clients
@clients_bp.route('/get_clients', methods=['GET'])
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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

#update client
# @clients_bp.route('/update_client/<string:client_id>' , methods = ['PUT'])
# def update_client(client_id):
#     data = request.json
#     client = Clients.query.get_or_404(client_id)
#     if not client:
#         return jsonify({"message" : "Client not found"}) , 404
#     if "client_name" in data:
#         client.client_name =data["client_name"]
#     if "client_email" in data:
#         client.client_email = data["client_email"]
#     if "client_phone" in data:
#         client.client_phone = data["client_phone"]
#     if "client_address" in data:
#         client.client_address = data["client_address"]
#     if "client_password" in data:
#         client.client_password = data["client_password"]

#         db.session.commit()
#         return jsonify({"message" : "Client updated successfully!"}) , 200
#     else:
#         return jsonify({"message" : "No valid fields to update"}) , 400
    

@clients_bp.route('/update_client/<string:client_id>', methods=['PUT', 'PATCH'])
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
    
# @clients_bp.route('/register' , methods = ['POST'])
# def register_client():
#     data = request.json
#     required_fields = ['client_name', 'client_email', 'client_phone', 'client_address', 'client_password']
    
#     for field in required_fields:
#         if not data.get(field):
#             return jsonify({"error": f"'{field}' is required"}), 400
            
#     existing_client = Clients.query.filter_by(client_email=data['client_email']).first()
#     if existing_client:
#         return jsonify({"message": "Client with this email already exists"}), 409
        
#     try:
#         # Hash the password for security
#         hashed_password = generate_password_hash(data['client_password'])
        
#         new_client = Clients(
#             client_name=data['client_name'],
#             client_email=data['client_email'],
#             client_phone=data['client_phone'],
#             client_address=data['client_address'],
#             client_password=hashed_password
#         )
#         db.session.add(new_client)
#         db.session.commit()
        
#         # Generate and save OTP for registration verification
#         otp_code = str(random.randint(100000, 999999))
#         expires_at = datetime.utcnow() + timedelta(minutes=5)
#         new_otp = OtpCode(
#             client_id=new_client.client_id,
#             otp_code=otp_code,
#             expires_at=expires_at,
#             otp_type='registration'  # Use a type to differentiate purposes
#         )
#         db.session.add(new_otp)
#         db.session.commit()
        
#         # Send OTP via email
#         send_email(
#             recipients=[data['client_email']],
#             subject="Client Registration OTP",
#             body=f"Hello {data['client_name']},\n\nYour OTP for registration is {otp_code}. It is valid for 5 minutes."
#         )
        
#         return jsonify({"message": "Client registered successfully. Please check your email for the OTP."}), 201
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

# Assuming you have a User model with user_id, user_email, and user_password fields
# and a Clients model with a user_id foreign key.

# @clients_bp.route('/register' , methods = ['POST'])
# def register_client():
#     data = request.json
#     required_fields = ['client_name', 'client_email', 'client_phone', 'client_address', 'client_password']
    
#     for field in required_fields:
#         if not data.get(field):
#             return jsonify({"error": f"'{field}' is required"}), 400
            
#     # Check for existing user with the same email
#     existing_user = Clients.query.filter_by(user_email=data['client_email']).first()
#     if existing_user:
#         return jsonify({"message": "Client with this email already exists"}), 409
        
#     try:
#         # Step 1: Create the User account first
#         hashed_password = generate_password_hash(data['client_password'])
#         new_user = User(
#             user_email=data['client_email'],
#             user_password=hashed_password
#         )
#         db.session.add(new_user)
#         # db.session.commit() # Don't commit yet

#         # Step 2: Create the Client profile and link it to the new user's ID
#         # db.session.flush() gets the new_user.user_id without committing to the database
#         db.session.flush() 
        
#         new_client = Clients(
#             client_name=data['client_name'],
#             client_email=data['client_email'],
#             client_phone=data['client_phone'],
#             client_address=data['client_address'],
#             user_id=new_user.user_id # Link to the User ID from the new user record
#         )
#         db.session.add(new_client)
#         db.session.commit() # Commit both new records in a single transaction

#         # Generate and save OTP for registration verification
#         # ... (rest of your OTP and email logic)
        
#         return jsonify({"message": "Client registered successfully. Please check your email for the OTP."}), 201
#     except Exception as e:
#         db.session.rollback() # Rollback all changes if an error occurs
#         return jsonify({"error": str(e)}), 500

# @clients_bp.route('/register', methods=['POST'])
# def register_client():
#     data = request.json
#     required_fields = ['client_name', 'client_email', 'client_phone', 'client_address', 'client_password']

#     # 1. Input Validation
#     for field in required_fields:
#         if not data or not data.get(field):
#             return jsonify({"error": f"'{field}' is required"}), 400

#     # 2. Check for existing CLIENT profile uniqueness (based on client_email)
#     existing_client_profile = Clients.query.filter_by(client_email=data['client_email']).first()
#     if existing_client_profile:
#         return jsonify({"message": "A client profile with this email already exists"}), 409

#     try:
#         # Hash the password once
#         hashed_password = generate_password_hash(data['client_password'])
        
#         # 3. Start Transaction to create BOTH User (account) and Client (profile)
        
#         # 3a. Create the User account (for authentication)
#         new_user = User(
#             user_email=data['client_email'],
#             user_password=hashed_password # Stored in User table
#         )
#         db.session.add(new_user)

#         # 3b. KEY STEP: Retrieve the auto-generated user_id
#         # This executes the INSERT for 'new_user' and gives us the primary key (user_id).
#         db.session.flush()

#         # 3c. Create the Client profile, linking it and storing the hashed password
#         new_client = Clients(
#             client_name=data['client_name'],
#             client_email=data['client_email'],
#             client_phone=data['client_phone'],
#             client_address=data['client_address'],
#             user_id=new_user.user_id,         # Link to the newly generated user_id
#             client_password=hashed_password   # Stored in Clients table (as per your model)
#         )
#         db.session.add(new_client)

#         # 3d. Commit both new records in a single atomic transaction
#         db.session.commit()

#         # 4. Success Response
#         # (Your OTP/email logic would go here)
        
#         return jsonify({
#             "message": "Client registered successfully. Please check your email for the OTP.", 
#             "user_id": new_user.user_id
#         }), 201
    
#     except Exception as e:
#         # 5. Error Handling and Rollback
#         db.session.rollback()
#         # In a production environment, you would log the error `str(e)`
#         print(f"Registration Error: {e}")
#         return jsonify({"error": "An internal server error occurred during registration. Transaction rolled back."}), 500

# @clients_bp.route('/register', methods=['POST'])
# def register_client():
#     """
#     Registers a new client by creating linked records in the User and Clients tables
#     in a single, atomic transaction.
#     """
#     data = request.json
    
#     # Fields required for both User and Clients models
#     required_fields = [
#         'client_name', 'client_email', 'client_phone', 
#         'client_address', 'client_password'
#     ]

#     # 1. Input Validation: Check for missing fields
#     for field in required_fields:
#         if not data or not data.get(field):
#             return jsonify({"error": f"'{field}' is required"}), 400

#     # --- 2. CRITICAL UNIQUENESS CHECKS ---
    
#     # Due to your database structure duplicating profile fields in both User and Clients,
#     # we must check for uniqueness across both tables to prevent IntegrityErrors.

#     client_email = data['client_email']
#     client_phone = data['client_phone']
    
#     # 2a. Check if email exists in the core User authentication table
#     if User.query.filter_by(user_email=client_email).first():
#         return jsonify({"message": "An account already exists with this email address."}), 409

#     # 2b. Check if email exists in the Clients profile table (Your model has this as unique)
#     if Clients.query.filter_by(client_email=client_email).first():
#         return jsonify({"message": "A client profile already exists with this email."}), 409

#     # 2c. Check if phone exists in the Clients profile table (Your model has this as unique)
#     if Clients.query.filter_by(client_phone=client_phone).first():
#         return jsonify({"message": "A client profile already exists with this phone number."}), 409
        
#     # NOTE: If User model also has unique on user_phone, add that check here too.
        
#     try:
#         # Hash the password once for security
#         hashed_password = generate_password_hash(data['client_password'])
        
#         # 3. START ATOMIC TRANSACTION
        
#         # 3a. Create the User account (The authentication record)
#         # Note: We must also provide user_name, user_phone, user_address as they are nullable=False in your User model.
#         new_user = User(
#             user_name=data['client_name'],
#             user_email=client_email,
#             user_phone=client_phone,
#             user_address=data['client_address'],
#             user_password=hashed_password
#         )
#         db.session.add(new_user)

#         # 3b. KEY STEP: Retrieve the auto-generated user_id
#         # Flush executes the INSERT for new_user, populating new_user.user_id, 
#         # but keeps the transaction uncommitted.
#         db.session.flush()

#         # 3c. Create the Client profile, linking it with the retrieved ID
#         new_client = Clients(
#             client_name=data['client_name'],
#             client_email=client_email,
#             client_phone=client_phone,
#             client_address=data['client_address'],
#             user_id=new_user.user_id,          # <--- Foreign Key Link established here
#             client_password=hashed_password    # Stored due to your Clients model definition
#         )
#         db.session.add(new_client)

#         # 3d. Commit both records in a single atomic transaction
#         # db.session.commit()

#         otp_code = str(random.randint(100000, 999999))
#         expires_at = datetime.utcnow() + timedelta(minutes=5)
        
#         new_otp = OtpCode(
#             user_id=new_user.user_id, # Link OTP to the newly created User ID
#             otp_code=otp_code,
#             expires_at=expires_at,
#             type='client_registration' # Use type to identify the purpose
#         )
#         db.session.add(new_otp)
#         db.session.commit()

#         send_email(
#             recipients=[client_email],
#             subject="Registration Verification OTP",
#             body=f"Welcome {new_user.user_name}!\n\nYour registration verification code is {otp_code}. It is valid for 5 minutes."
#         )

#         # 4. Success Response
#         return jsonify({
#             "message": "Client registered successfully. Please check your email for the OTP.", 
#             "user_id": new_user.user_id
#         }), 201
    
#     except Exception as e:
#         # 5. Error Handling and Rollback
#         db.session.rollback()  # Undo both User and Client additions if any error occurred
#         print(f"Registration Error: {e}") # Log the error for developer debugging
#         return jsonify({"error": "An internal server error occurred during registration. Transaction rolled back."}), 500


@clients_bp.route('/register', methods=['POST'])
@jwt_required()
def register_client():
    """
    Registers a new client by creating linked records in the User, Clients, 
    and OtpCode tables in an atomic transaction, then sends a verification email.
    ---
    tags:
      - Client Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: client
        description: Client registration data
        required: true
        schema:
          type: object
          required: [client_name, client_email, client_phone, client_address, client_password]
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
      201:
        description: Client registered successfully. OTP sent for verification.
        schema:
          type: object
          properties:
            message:
              type: string
            user_id:
              type: integer
      400:
        description: Missing required fields or invalid input.
      409:
        description: A user/client with this email/phone already exists.
      500:
        description: Internal server error during registration or rollback.
    """
    data = request.json
    
    required_fields = [
        'client_name', 'client_email', 'client_phone', 
        'client_address', 'client_password'
    ]

    # 1. Input Validation: Check for missing fields
    for field in required_fields:
        if not data or not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    client_email = data['client_email']
    client_phone = data['client_phone']
    
    # 2. CRITICAL UNIQUENESS CHECKS
    # Check both tables before attempting registration
    if User.query.filter_by(user_email=client_email).first():
        return jsonify({"message": "An account already exists with this email address."}), 409
    
    if Clients.query.filter_by(client_email=client_email).first():
        return jsonify({"message": "A client profile already exists with this email."}), 409

    if Clients.query.filter_by(client_phone=client_phone).first():
        return jsonify({"message": "A client profile already exists with this phone number."}), 409
        
    try:
        # Hash the password once
        hashed_password = generate_password_hash(data['client_password'])
        
        # 3. START ATOMIC TRANSACTION (User, Client, and OTP added to the session)
        
        # 3a. Create the User account
        new_user = User(
            user_name=data['client_name'],
            user_email=client_email,
            user_phone=client_phone,
            user_address=data['client_address'],
            user_password=hashed_password
        )
        db.session.add(new_user)
        db.session.flush() # Get the auto-generated user_id
        
        # 3b. Create the Client profile
        new_client = Clients(
            client_name=data['client_name'],
            client_email=client_email,
            client_phone=client_phone,
            client_address=data['client_address'],
            user_id=new_user.user_id, # Foreign Key Link
            client_password=hashed_password
        )
        db.session.add(new_client)
        db.session.commit()

        # 3c. Generate and create the OTP record
        otp_code = str(random.randint(100000, 999999))
        
        # FIX: Use datetime.now(timezone.utc) to resolve the 'utcnow' error
        expires_at = datetime.now()+ timedelta(minutes=5)
        
        new_otp = OtpCode(
            user_id=new_user.user_id,
            otp_code=otp_code,
            expires_at=expires_at,
            type='client_registration'
        )
        db.session.add(new_otp)

        # 4. COMMIT ALL records (User, Client, OTP) in a SINGLE transaction
        db.session.commit()
        
        # 5. External Action: Send Email (Executed ONLY after successful commit)
        send_email(
            recipients=[client_email],
            subject="Registration Verification OTP",
            body=f"Welcome {new_user.user_name}!\n\nYour registration verification code is {otp_code}. It is valid for 5 minutes."
        )

        # 6. Success Response
        return jsonify({
            "message": "Client registered successfully. Please check your email for the OTP.", 
            "user_id": new_user.user_id
        }), 201
    
    except Exception as e:
        # 7. Error Handling: Rollback all changes if commit failed
        db.session.rollback()
        # Log the error for developer debugging
        print(f"Registration Error: {e}") 
        
        # Provide a generic server error message
        return jsonify({"error": "An internal server error occurred during registration. Transaction rolled back."}), 500



# clients_bp.py
# @clients_bp.route('/login', methods=['POST'])
# def login_client():
#     data = request.json
#     client_email = data.get("client_email")
#     client_password = data.get("client_password")
    
#     if not all([client_email, client_password]):
#         return jsonify({"message": "Email and password are required"}), 400
        
#     client = Clients.query.filter_by(client_email=client_email).first()
    
#     # Check if client exists and password is correct
#     if client and check_password_hash(client.client_password, client_password):
#         try:
#             # Delete any old, unused OTPs for this client to ensure a clean slate
#             OtpCode.query.filter_by(client_id=client.client_id).delete()
#             db.session.commit()
            
#             # Generate a new OTP for login verification
#             otp_code = str(random.randint(100000, 999999))
#             expires_at = datetime.utcnow() + timedelta(minutes=5)
            
#             new_otp = OtpCode(
#                 client_id=client.client_id,
#                 otp_code=otp_code,
#                 expires_at=expires_at,
#                 otp_type='login'
#             )
#             db.session.add(new_otp)
#             db.session.commit()
            
#             # Send the login OTP via email
#             send_email(
#                 recipients=[client_email],
#                 subject="Login Verification OTP",
#                 body=f"Hello {client.client_name},\n\nYour login verification code is {otp_code}. It is valid for 5 minutes."
#             )
            
#             return jsonify({"message": "OTP sent for login verification. Please check your email."}), 200
        
#         except Exception as e:
#             db.session.rollback()
#             return jsonify({"error": str(e)}), 500
            
#     else:
#         return jsonify({"message": "Invalid email or password"}), 401
# @clients_bp.route('/login', methods=['POST'])
# def login_client():
#     data = request.json
#     client_email = data.get("client_email")
#     client_password = data.get("client_password")
    
#     if not all([client_email, client_password]):
#         return jsonify({"message": "Email and password are required"}), 400
        
#     # FIX: Authenticate against the core User table, not the Clients profile table.
#     user_account = User.query.filter_by(user_email=client_email).first()
    
#     # Check if user account exists and password is correct (using user_password field)
#     # The user_password is the hashed version stored in the User table.
#     if user_account and check_password_hash(user_account.user_password, client_password):
#         try:
#             # OPTIONAL STEP: Find the linked client profile to use client_id/client_name, if needed.
#             # However, OTP should ideally be linked to the user_id, which is the primary key.
#             # Assuming OtpCode uses user_id for linking (based on your model structure)

#             # Delete any old, unused OTPs for this user
#             OtpCode.query.filter_by(user_id=user_account.user_id).delete()
#             db.session.commit()
            
#             # Generate a new OTP for login verification
#             otp_code = str(random.randint(100000, 999999))
#             expires_at = datetime.utcnow() + timedelta(minutes=5)
            
#             # Link OTP to user_id (primary authentication ID)
#             new_otp = OtpCode(
#                 user_id=user_account.user_id,
#                 otp_code=otp_code,
#                 expires_at=expires_at,
#                 type='login' # Renamed otp_type to 'type' based on model (type is a reserved Python keyword)
#             )
#             db.session.add(new_otp)
#             db.session.commit()
            
#             # Send the login OTP via email
#             # NOTE: send_email function is assumed to be defined elsewhere
#             # You would likely need the client's name for a personalized email
#             # client_profile = Clients.query.filter_by(user_id=user_account.user_id).first()
            
#             send_email(
#                 recipients=[client_email],
#                 subject="Login Verification OTP",
#                 body=f"Hello {user_account.user_name},\n\nYour login verification code is {otp_code}. It is valid for 5 minutes."
#             )
            
#             return jsonify({"message": "OTP sent for login verification. Please check your email."}), 200
        
#         except Exception as e:
#             db.session.rollback()
#             # In production, use logging instead of returning str(e)
#             print(f"Login OTP generation error: {e}") 
#             return jsonify({"error": "An internal server error occurred during login."}), 500
            
#     else:
#         # User not found OR password check failed
#         return jsonify({"message": "Invalid email or password"}), 401

@clients_bp.route('/login', methods=['POST'])
@jwt_required()
def login_client_profile():
    """
    First stage of client login: Authenticates credentials, cleans up old OTPs, 
    generates a new login OTP, saves it, and sends it via email.
    ---
    tags:
      - Client Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: credentials
        description: Client login credentials
        required: true
        schema:
          type: object
          required: [client_email, client_password]
          properties:
            client_email:
              type: string
            client_password:
              type: string
    responses:
      200:
        description: OTP sent successfully for login verification.
        schema:
          type: object
          properties:
            message:
              type: string
      400:
        description: Email and password are required.
      401:
        description: Invalid email or password.
      500:
        description: Internal server error.
    """
    data = request.json
    client_email = data.get("client_email")
    client_password = data.get("client_password")
    
    if not all([client_email, client_password]):
        return jsonify({"message": "Email and password are required"}), 400
        
    # 1. AUTHENTICATION: Check the primary User table for credentials
    user_account = User.query.filter_by(user_email=client_email).first()
    
    # Check if user account exists AND password is correct
    if user_account and check_password_hash(user_account.user_password, client_password):
        
        # 2. CLIENT PROFILE RETRIEVAL: Find the specific client profile using the user_id
        client_profile = Clients.query.filter_by(user_id=user_account.user_id).first()
        
        if not client_profile:
            # This is a critical error; user exists but no linked client profile
            return jsonify({"error": "User found, but no linked client profile exists."}), 500

        try:
            # 3. OTP CLEANUP & GENERATION
            
            # Delete any old, unused OTPs for this user
            OtpCode.query.filter_by(user_id=user_account.user_id).delete()
            db.session.commit() # Commit the deletion
            
            # Generate a new OTP for login verification
            otp_code = str(random.randint(100000, 999999))
            expires_at = datetime.datetime.now() + timedelta(minutes=5) # FIX: Use timezone.utc
            
            # Link OTP to user_id
            new_otp = OtpCode(
                user_id=user_account.user_id,
                otp_code=otp_code,
                expires_at=expires_at,
                type='client_login'
            )
            db.session.add(new_otp)
            db.session.commit() # Commit the new OTP record
            
            # 4. Send the login OTP via email
            send_email(
                recipients=[client_email],
                subject="Login Verification OTP",
                # Use data from the client_profile or user_account for personalization
                body=f"Hello {client_profile.client_name},\n\nYour login verification code is {otp_code}. It is valid for 5 minutes."
            )
            
            return jsonify({"message": "OTP sent for login verification. Please check your email."}), 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Login OTP generation error: {e}") 
            logging.exception(f"Login OTP generation error for email: {client_email}") 
            return jsonify({"error": "An internal server error occurred during login. Transaction rolled back."}), 500
            
    else:
        # User not found OR password check failed
        return jsonify({"message": "Invalid email or password"}), 401
    

@clients_bp.route('/verify_registration_otp', methods=['POST'])
@jwt_required()
def verify_client_registration_otp():
    """
    Verifies the registration OTP code provided by the client.
    If valid, marks the OTP as used, generates and returns a JWT access token.
    ---
    tags:
      - Client Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: verification
        description: Email and OTP for registration verification.
        required: true
        schema:
          type: object
          required: [client_email, otp_code]
          properties:
            client_email:
              type: string
            otp_code:
              type: string
    responses:
      200:
        description: Registration complete, OTP verified, and login successful.
        schema:
          type: object
          properties:
            message:
              type: string
            access_token:
              type: string
            client_id:
              type: integer
            user_id:
              type: integer
      400:
        description: Missing email or OTP code.
      401:
        description: Invalid, expired, or used OTP code.
      404:
        description: User or Client profile not found.
      500:
        description: Server error during finalization.
    """
    data = request.json
    user_email = data.get("client_email")
    otp_code = data.get("otp_code")

    if not all([user_email, otp_code]):
        return jsonify({"message": "Email and OTP code are required"}), 400

    user = User.query.filter_by(user_email=user_email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    client_profile = Clients.query.filter_by(user_id=user.user_id).first()
    if not client_profile:
        return jsonify({"message": "Client profile not found"}), 404

    # Find the valid, unused, and unexpired OTP for this user and type
    otp_record = OtpCode.query.filter(
        OtpCode.user_id == user.user_id,
        OtpCode.otp_code == otp_code,
        OtpCode.expires_at > datetime.datetime.now(),
        OtpCode.is_used == False,
        OtpCode.type == 'client_registration'
    ).order_by(OtpCode.created_at.desc()).first()

    if otp_record:
        try:
            # 1. Mark OTP as used and commit
            otp_record.is_used = True
            db.session.commit()

            # 2. Generate JWT access token
            # We use the primary user_id as the JWT identity
            access_token = create_access_token(
                identity=user.user_id, 
                expires_delta=timedelta(minutes = 15)
            )
            # refresh_token = create_refresh_token(identity = user.user_id , expires_delta = timedelta(days = 7))
            
            # 3. Send confirmation email
            send_email(
                recipients=[user_email],
                subject="Registration Successful! 🎉",
                body=f"Hello {client_profile.client_name},\n\nYour account has been successfully verified and registered."
            )

            return jsonify({
                "message": "Registration complete and OTP verified. You are now logged in.",
                "access_token": access_token,
                "client_id": client_profile.client_id,
                "user_id": user.user_id
            }), 200
        except Exception as e:
            db.session.rollback()
            logging.exception("Error during registration OTP verification finalization.")
            return jsonify({"error": "Server error during finalization."}), 500
    else:
        # OTP is invalid, expired, or already used
        return jsonify({"message": "Invalid, expired, or used OTP code."}), 401


# --- NEW: OTP Verification for Client Login ---
@clients_bp.route('/verify_login_otp', methods=['POST'])
@jwt_required()
def verify_client_login_otp():
    """
    Second stage of client login: Verifies the login OTP code.
    If valid, marks the OTP as used, generates and returns a JWT access token.
    ---
    tags:
      - Client Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: verification
        description: Email and OTP for login verification.
        required: true
        schema:
          type: object
          required: [client_email, otp_code]
          properties:
            client_email:
              type: string
            otp_code:
              type: string
    responses:
      200:
        description: Login successful. Access token returned.
        schema:
          type: object
          properties:
            message:
              type: string
            access_token:
              type: string
            client_id:
              type: integer
            user_id:
              type: integer
      400:
        description: Missing email or OTP code.
      401:
        description: Invalid, expired, or used OTP code.
      404:
        description: User or Client profile not found.
      500:
        description: Server error during finalization.
    """
    data = request.json
    user_email = data.get("client_email")
    otp_code = data.get("otp_code")

    if not all([user_email, otp_code]):
        return jsonify({"message": "Email and OTP code are required"}), 400

    user = User.query.filter_by(user_email=user_email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    client_profile = Clients.query.filter_by(user_id=user.user_id).first()
    if not client_profile:
        return jsonify({"message": "Client profile not found"}), 404

    # Find the valid, unused, and unexpired OTP for this user and type
    otp_record = OtpCode.query.filter(
        OtpCode.user_id == user.user_id,
        OtpCode.otp_code == otp_code,
        OtpCode.expires_at > datetime.datetime.now(),
        OtpCode.is_used == False,
        OtpCode.type == 'client_login'
    ).order_by(OtpCode.created_at.desc()).first()

    if otp_record:
        try:
            # 1. Mark OTP as used and commit
            otp_record.is_used = True
            db.session.commit()
            
            # 2. Generate JWT access token
            access_token = create_access_token(
                identity=user.user_id, 
                expires_delta=timedelta(days=1)
            )
            
            # 3. Send confirmation email
            send_email(
                recipients=[user_email],
                subject="Successful Login Notification",
                body=f"Hello {client_profile.client_name},\n\nYour login attempt at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} was successful."
            )

            return jsonify({
                "message": "Login successful.",
                "access_token": access_token,
                "client_id": client_profile.client_id,
                "user_id": user.user_id
            }), 200
        except Exception as e:
            db.session.rollback()
            logging.exception("Error during login OTP verification finalization.")
            return jsonify({"error": "Server error during finalization."}), 500
    else:
        # OTP is invalid, expired, or already used
        return jsonify({"message": "Invalid, expired, or used OTP code."}), 401
