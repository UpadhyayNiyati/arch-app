import time
from flask import Blueprint , jsonify , request , url_for , current_app
from models import User , db , OtpCode , ProjectAssignments , Clients , Projects , Tasks , Projectvendor , Vendors , Boards ,Pin , ProjectTemplates , Templates , Role , UserToken , UserRole , Invite , Company , Pinterest
from flask_jwt_extended import jwt_required , create_access_token , get_jwt_identity  , create_refresh_token , get_jwt, decode_token
from flask_migrate import Migrate
import uuid
from functools import wraps
import logging
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
# from flask_bcrypt import bcrypt
from flask_bcrypt import Bcrypt
from email.message import EmailMessage
from werkzeug.security import generate_password_hash , check_password_hash
import smtplib
import random
import os
import inspect
from auth.auth import decode_jwt
import jwt
from flask_cors import CORS
from utils.email_utils import send_email
from itsdangerous import URLSafeTimedSerializer


# from architect_mngmnt_app.archs import bcrypt as Bcrypt
from datetime import datetime, timedelta , timezone
import uuid

user_bp = Blueprint('user' , __name__)
bcrypt = Bcrypt()

CORS(user_bp)

def generate_uuid():
    return str(uuid.uuid4())



def decode_reset_token(token):
    secret = PASSWORD_RESET_SECRET

    try:
        # Introspect what params decode_jwt_custom supports
        sig = inspect.signature(decode_jwt)
        params = sig.parameters

        # Build only allowed arguments
        kwargs = {}
        if "algorithms" in params:
            kwargs["algorithms"] = ["HS256"]
        if "options" in params:
            kwargs["options"] = {"verify_exp": True}

        return decode_jwt(token, secret, **kwargs)

    except TypeError:
        # Fallback: call with ONLY token + secret
        return decode_jwt(token, secret)

@user_bp.route('/get_users' , methods = ['GET'])
def get_all_users():
    """
    Get All Users with Roles
    ---
    tags:
      - User Management
    responses:
      200:
        description: A list of all user records, including their assigned role name.
        schema:
          type: array
          items:
            $ref: '#/definitions/UserDetail'
      500:
        description: Server error occurred during retrieval.
    """
    try:
        # 1. Query: Select User objects and join with the Roles table.
        # This allows accessing role attributes directly.
        users_with_roles = db.session.query(User, Role)\
            .join(Role, User.role_id == Role.role_id)\
            .all()

        result = []
        for user, role in users_with_roles:
            # IMPORTANT: Do NOT return user_password in a real application!
            # I've commented it out below for security.
            
            # 2. Append the required role_id and role_name
            result.append({
                'user_id' : user.user_id , 
                'user_name' : user.user_name , 
                'user_email' : user.user_email , 
                # 'user_password' : user.user_password ,  <-- REMOVED FOR SECURITY
                'user_address' : user.user_address , 
                'created_at' : user.created_at.isoformat() if user.created_at else None,
                'role_id': user.role_id,            # Added role_id
                'role_name': role.role_name ,
                'company_id':user.company_id
        # Added role_name from the joined table
            })
            
        return jsonify(result) , 200

    except Exception as e:
        # In case of an error (e.g., table not found, relationship issue)
        return jsonify({"error" : str(e)}) , 500
    
#get single user by id
@user_bp.route('/get_one_user/<string:user_id>' , methods = ['GET'])
def get_user_by_id(user_id):
    user = User.query.get_or_404(user_id)
    if not user:
        return jsonify({"message":"User not found"}) , 404
    
    user_with_roles = db.session.query(User, Role)\
    .join(Role, User.role_id == Role.role_id)\
    .filter(User.user_id == user_id)\
    .all()
    
    # if not user_with_roles:
        # return jsonify({"message": "User not found"}), 404
    
    for user, role in user_with_roles:
        print(user, role) 
    
     # Now works

    # user_with_roles = db.session.query(User , Role)\
    #     .join(Role, User.role_id == Role.role_id)\
    #     .all()
    
    # if not user_with_roles:
    #         return jsonify({"message": "User not found"}), 404

    # user, role = user_with_roles  # unpack tuple

    result = {
        'user_id' : user.user_id , 
        'user_name' : user.user_name , 
        'user_email' : user.user_email , 
        'user_password' : user.user_password , 
        'user_address' : user.user_address , 
        'created_at' : user.created_at,
        'company_id' : user.company_id
    }
    return jsonify(result) , 200

#post user
@user_bp.route('/post_user' , methods = ['POST'])
def post_user():
    """
    Create New User (Internal/Admin use)
    ---
    tags:
      - User Management
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/UserCreate'
    responses:
      201:
        description: User added successfully.
      400:
        description: Missing required fields.
      500:
        description: Server error or database constraint violation.
    """
    data = request.json
    required_fields = ['user_name' , 'user_email' , 'user_phone' , 'user_password' , 'user_address']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"'{field}' is required"}), 400
        hashed_password = bcrypt.generate_password_hash(data['user_password']).decode('utf-8')
        try:
            new_user = User(
                user_name = data['user_name'] , 
                user_email = data['user_email'] ,
                user_phone = data['user_phone'] ,
                user_password = hashed_password ,
                user_address = data['user_address'] ,
                company_id = data['company_id']
            )
            db.session.add(new_user)
            db.session.commit()
            return jsonify({
                "message" : "User added successfully!!",
                "user": {
                "user_id": new_user.user_id,          # Assumes user_id is automatically generated
                "user_name": new_user.user_name,
                "user_email": new_user.user_email,
                "user_phone": new_user.user_phone,
                "user_address": new_user.user_address,
                "company_id": new_user.company_id
                }
            })
        except Exception as e:
            return jsonify({"error" : str(e)}) , 500
        
#protected_route



#update user    
@user_bp.route('/update_user/<string:user_id>' , methods = ['PUT'])
def update_user(user_id):           
    """
    Update User Details
    ---
    tags:
      - User Management
    parameters:
      - name: user_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/UserUpdate'
    responses:
      200:
        description: User updated successfully.
      404:
        description: User not found.
      500:
        description: Server error during update.
    """
    data = request.json
    user = User.query.get_or_404(user_id)
    if not user:
        return jsonify({"message" : "User not found"}) , 404
    if "user_name" in data:
        user.user_name =data["user_name"]
    if "user_email" in data:
        user.user_email = data["user_email"]
    if "user_phone" in data:
        user.user_phone = data["user_phone"]
    if "user_password" in data:
        hashed_password = bcrypt.generate_password_hash(data['user_password']).decode('utf-8')
        user.user_password = hashed_password
    if "user_address" in data:
        user.user_address = data["user_address"]
    db.session.commit()
    return jsonify({"message" : "User updated successfully!!",
                    "user":{
                        "user_id": user.user_id,
                        "user_name": user.user_name,
                        "user_email": user.user_email,
                        "user_phone": user.user_phone,
                        "user_address": user.user_address,
                        "company_id": user.company_id
                    }
                    }) , 200

#delete user
@user_bp.route('/delete_user/<string:user_id>', methods=['DELETE'])
def del_user(user_id):
    try:

        data = request.get_json()
        user_password = data.get("user_password")

        if not user_password:
            return jsonify({"error": "Password is required"}), 400
        user = User.query.get_or_404(user_id)

        # DELETE CHILD RECORDS FIRST
        UserToken.query.filter_by(user_id=user_id).delete()
        OtpCode.query.filter_by(user_id=user_id).delete()   # <-- ADD THIS
        Invite.query.filter_by(created_by_user_id=user.user_id).delete()  # <-- ADD THIS IF INVITE MODEL IS IMPORTED
        Invite.query.filter_by(accepted_by_user_id=user.user_id).delete()
        Tasks.query.filter_by(assigned_to=user_id).delete()
        UserRole.query.filter_by(user_id=user_id).delete()
        # Role.query.filter_by(role_id=user.role_id).delete()
        Pinterest.query.filter_by(user_id=user_id).delete()
        Boards.query.filter_by(user_id=user_id).delete()
        # Company.query.filter_by(company_id=company_id).delete()

        db.session.delete(user)
        db.session.commit()

        return jsonify({"message": "User deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("DELETE ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@user_bp.route('/dashboard/<string:user_id>', methods=['GET'])
def get_user_dashboard(user_id):
    try:
        # Get optional search parameters from the URL
        project_name_query = request.args.get('project_name')
        task_status_query = request.args.get('task_status')
        vendor_name_query = request.args.get('vendor_name')

        # Check if the user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

        # Start with a base query for the user's project assignments
        assignments_query = ProjectAssignments.query.filter_by(user_id=user_id)
        
        # Apply filters to the project assignments query if parameters are provided
        if project_name_query:
            # We need to join with the Projects table to filter by project name
            assignments_query = assignments_query.join(Projects).filter(
                Projects.project_name.ilike(f'%{project_name_query}%')
            )

        # Apply vendor filter
        if vendor_name_query:
            # Join with Projectvendor and Vendors to filter by vendor name
            assignments_query = assignments_query.join(Projectvendor).join(Vendors).filter(
                Vendors.company_name.ilike(f'%{vendor_name_query}%')
            )
            
        assignments = assignments_query.all()
        dashboard_data = []

        for assignment in assignments:
            project = Projects.query.get(assignment.project_id)
            if not project:
                continue

            # Your existing logic to get client, templates, etc.
            client_info = None
            client_assignment = ProjectAssignments.query.filter_by(
                project_id=project.project_id,
                role='client'
            ).first()
            if client_assignment:
                client = Clients.query.filter_by(user_id=client_assignment.user_id).first()
                if client:
                    client_info = {
                        "client_name": client.client_name,
                        "client_email": client.client_email,
                        "client_phone": client.client_phone
                    }

            # --- Apply task status filter here ---
            tasks_query = Tasks.query.filter_by(project_id=project.project_id)
            if task_status_query:
                tasks_query = tasks_query.filter(Tasks.status.ilike(f'%{task_status_query}%'))
            
            tasks = tasks_query.all()
            task_list = []
            for task in tasks:
                task_list.append({
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "status": task.status,
                    "due_date": task.due_date.isoformat(),
                    "priority": task.priority,
                    "assigned_to": task.assigned_to
                })

            # Existing logic for templates, vendors, boards, and pins
            project_templates = ProjectTemplates.query.filter_by(project_id=project.project_id).all()
            template_list = []
            for pt in project_templates:
                template = Templates.query.get(pt.template_id)
                if template:
                    template_list.append({
                        "template_id": template.template_id,
                        "template_name": template.template_name,
                        "file_url": pt.template_file_url
                    })

            project_vendors = Projectvendor.query.filter_by(project_id=project.project_id).all()
            vendor_list = []
            for pv in project_vendors:
                vendor = Vendors.query.get(pv.vendor_id)
                if vendor:
                    vendor_list.append({
                        "vendor_id": vendor.vendor_id,
                        "company_name": vendor.company_name,
                        "role": pv.role
                    })

            project_boards = Boards.query.filter_by(project_id=project.project_id).all()
            board_list = []
            for board in project_boards:
                pins = Pin.query.filter_by(board_id=board.board_id).all()
                pin_list = []
                for pin in pins:
                    pin_list.append({
                        "pin_id": pin.pin_id,
                        "pin_type": pin.pin_type,
                        "content": pin.content,
                        "position_x": pin.position_x,
                        "position_y": pin.position_y
                    })
                
                board_list.append({
                    "board_id": board.board_id,
                    "board_name": board.board_name,
                    "board_description": board.board_description,
                    "pins": pin_list
                })

            project_data = {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "project_status": project.status,
                "assigned_client": client_info,
                "assigned_tasks": task_list,
                "assigned_templates": template_list,
                "assigned_vendors": vendor_list,
                "project_boards": board_list
            }
            dashboard_data.append(project_data)

        return jsonify(dashboard_data), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    

PASSWORD_RESET_SECRET = os.getenv('PASSWORD_RESET_SECRET', 'your_password_reset_secret_key') 
RESET_TOKEN_EXPIRY = timedelta(hours=10)
# NOTE: The original code used URLSafeTimedSerializer which is generally okay, 
# but using the standard `jwt` library keeps the token mechanism consistent.

# Helper function to generate a password reset JWT
def create_reset_token(user_id):
    expiration = datetime.utcnow() + RESET_TOKEN_EXPIRY
    payload = {
        'user_id': str(user_id),  # Ensure UUID is converted to string for JWT
        'exp': expiration.timestamp(),
        'type': 'password_reset'
    }
    return jwt.encode(payload, PASSWORD_RESET_SECRET, algorithm='HS256')

    
logger = logging.getLogger(__name__)


@user_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Initiates the password reset process by generating a JWT token and sending a link.
    This JWT contains the user_id and an expiration timestamp.
    """
    data = request.get_json()
    user_email = data.get('user_email')

    if not user_email:
        return jsonify({'error': 'Email is required'}), 400

    # 1. Find the user
    user = User.query.filter_by(user_email=user_email).first()

    # 2. Security: Always return success to prevent user enumeration
    if user:
        try:
            try:
                base_url = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:5173") 
            except RuntimeError:
                # Fallback for testing if current_app is not set up correctly
                import os
                base_url = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173")
            # 3. Generate a time-limited **JWT Token**
            reset_token = create_reset_token(user.user_id)
            
            # 4. Construct the reset link for the client to use.
            # NOTE: 'user.reset_password' is a placeholder endpoint name. 
            # It should match the actual endpoint for the reset POST request in your application (e.g., your frontend's link).
            # For this backend, we point to the token validation endpoint.
            # Replace 'auth.reset_password' with the correct blueprint/route if necessary, 
            # or hardcode the expected frontend URL.
            reset_url = f"{base_url}/user/reset-password?token={reset_token}" # Adjust this URL for your client
            
            # 5. Send the email with the reset link
            email_body = (
                f"Hello {user.user_name},\n\n"
                f"You requested a password reset. Click the link below to set a new password. "
                f"This link will expire in 1 hour:\n\n{reset_url}"
            )
            
            # Use the existing send_email helper
            send_email(
                recipients=[user.user_email],
                subject="Password Reset Request",
                body=email_body
            )
            
            logger.info("Password reset link generated and sent to %s", user_email)

        except Exception as e:
            logger.error(f"Error sending password reset email: {e}", exc_info=True)
            # The error is logged, but we still return success to the client for security.
            pass 

    # Always return a generic success message for security (prevents leaking valid emails)
    return jsonify({
        "message": "If the email address is associated with an account, a password reset link has been sent."
    }), 200



@user_bp.route("/okay",methods=['GET'])
def okay():
    return jsonify({"message":"jeocn"})



# --- RESET PASSWORD ROUTE (REVISED) ---
@user_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Resets the user's password using the JWT token provided by the client.
    The client should send the token and the new_password in the body.
    """
    data = request.get_json()
    new_password = data.get('new_password')
    token = data.get('token')
    
    # 1. Input Validation
    if not new_password or not token:
        logger.warning("Password reset attempt failed: Missing token or new_password in request body.")
        return jsonify({'error': 'Token and new password are required'}), 400

    # 2. Decode and validate the JWT token
    payload = decode_reset_token(token)
    
    if payload.get("message"):
        if payload.get("expired"):
            # Log the expiration attempt
            logger.warning(f"Password reset attempt with expired token.")
            return jsonify({'error': 'Password reset link has expired. Please request a new one.'}), 401
        
        # Log the invalid token attempt
        logger.warning(f"Password reset attempt with invalid token.")
        return jsonify({'error': 'Invalid password reset token. Access denied.'}), 401

    user_id = payload.get("user_id")

    # 3. Find the user
    user = User.query.get(user_id)

    if not user:
        # User ID from token does not exist (e.g., deleted user)
        logger.error("User ID from valid token not found in database: %s", user_id)
        return jsonify({'error': 'User not found or account is unavailable.'}), 404

    try:
        # 4. Hash the new password and update the user record
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.user_password = hashed_password
        
        # 5. Security: Invalidate all existing refresh tokens for the user
        # This forces the user to log in again with the new password.
        tokens_revoked = UserToken.query.filter_by(user_id=user.user_id).delete()
        
        db.session.commit()
        
        logger.info("Password successfully reset for user ID: %s. Revoked %d refresh tokens.", user_id, tokens_revoked)
        
        # 6. Send confirmation email
        send_email(
            recipients=[user.user_email],
            subject="Password Reset Successful",
            body=f"Hello {user.user_name},\n\nYour password has been successfully reset. If you did not initiate this change, please contact support immediately."
        )

        return jsonify({'message': 'Password has been reset successfully. You can now log in with your new password.'}), 200

    except Exception as e:
        # 7. Rollback in case of any database error during commit
        db.session.rollback()
        logger.error("Error resetting password for user %s: %s", user_id, str(e), exc_info=True)
        return jsonify({'error': 'An internal server error occurred while updating the password.'}), 500
    
@user_bp.route('/create_role', methods=['POST'])
def create_role():
    data = request.json
    role_name = data.get('role_name')

    if not role_name:
        return jsonify({"message": "Role name is required"}), 400

    try:
        new_role = Role(role_name=role_name)
        db.session.add(new_role)
        db.session.commit()
        return jsonify({"message": "Role added successfully",
                        "role":{
                            "role_id":new_role.role_id,
                            "role_name":new_role.role_name
                        }
                    }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
   

@user_bp.route("/assign_role", methods=["POST"])
def assign_role():
    data = request.json
    user_id = data.get("user_id")
    role_id = data.get("role_id")

    if not user_id or not role_id:
        return jsonify({"error": "user_id and role_id required"}), 400

    # Check if user already has this role
    existing = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first()
    if existing:
        return jsonify({"message": "Role already assigned",
                         "role":{
                                "user_id": existing.user_id,
                                "role_id": existing.role_id
                         }
                        }), 200

    new_role = UserRole(user_id=user_id, role_id=role_id)
    db.session.add(new_role)
    db.session.commit()

    return jsonify({"message": "Role assigned successfully"}), 201


@user_bp.route('/get_users_by_company/<string:company_id>/<string:project_id>', methods=['GET'])
def get_users_by_company_id(company_id, project_id):
    """
    Get all Users by Company ID and check whether each user is assigned
    to the given project (to show + or - symbol in UI)
    """
    try:
        # Fetch all users belonging to the company
        users = User.query.filter_by(company_id=company_id).all()

        if not users:
            return jsonify({"message": f"No users found for company ID: {company_id}"}), 404

        result = []

        for user in users:

            # Check if user is already assigned to that project
            is_assigned = ProjectAssignments.query.filter_by(
                user_id=user.user_id,
                project_id=project_id
            ).first()

            # Build response object
            result.append({
                "user_id": user.user_id,
                "user_name": user.user_name,
                "user_email": user.user_email,
                "user_address": user.user_address,
                "company_id": user.company_id,
                "created_at": user.created_at.isoformat() if user.created_at else None,

                # Show + or - button
                "assigned": True if is_assigned else False
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@user_bp.route('/get_users_from_company_with_role/<string:company_id>', methods=['GET'])
def get_users_by_company_id_with_role(company_id):
    """
    Get all users for a company with their roles.
    """
    try:
        # Fetch all users belonging to the company
        users = (
            db.session.query(User)
            .filter(User.company_id == company_id)
            .all()
        )

        if not users:
            return jsonify({
                "message": f"No users found for company ID: {company_id}"
            }), 404

        result = []

        for user in users:
            # Fetch roles for each user
            user_roles = (
                db.session.query(Role.role_name)
                .join(UserRole, Role.role_id == UserRole.role_id)
                .filter(UserRole.user_id == user.user_id)
                .all()
            )

            role_names = [r.role_name for r in user_roles]

            result.append({
                "user_id": user.user_id,
                "user_name": user.user_name,
                "user_email": user.user_email,
                "user_address": user.user_address,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "company_id": user.company_id,
                "roles": role_names
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# @user_bp.route('/users/projects', methods=['GET'])
# @jwt_required # Assuming this decorator extracts user ID and/or validates the request
# def get_user_all_projects_from_assignments(user_id):
#     """
#     Retrieves ALL projects assigned to a specific user by querying the ProjectAssignments table.
#     No pagination is applied.
#     """
#     user_id = request.current_user_id  # Extracted from JWT or request context
#     # Optional: Add status filter (e.g., /projects?status=Active)
#     project_status_filter = request.args.get('status')
    
#     # Optional: Add role filter (e.g., /projects?role=Architect)
#     role_filter = request.args.get('role')

#     try:
#         # 1. Base Query: Start from ProjectAssignments for the specific user_id
#         query = ProjectAssignments.query.filter(
#             ProjectAssignments.user_id == user_id,
#             ProjectAssignments.is_assigned == True # Only fetch current assignments
#         )
        
#         # 2. Apply role filter if provided
#         if role_filter:
#             query = query.filter(ProjectAssignments.role.ilike(f'%{role_filter}%'))

#         # 3. Execute the query to get all assignment records
#         assignments = query.all()

#         project_list = []
#         for assignment in assignments:
            
#             # Retrieve the Project and Client details for each assignment
#             project = Projects.query.get(assignment.project_id)
            
#             # Ensure the project exists and apply the status filter (if needed)
#             if not project:
#                 continue
            
#             if project_status_filter and project.status != project_status_filter:
#                 continue
                
#             client_name = project.client.client_name if hasattr(project, 'client') and project.client else None

#             # 4. Serialize the data
#             project_list.append({
#                 # Data directly from the ProjectAssignments table
#                 'assignment_id': assignment.assignment_id,
#                 'user_role_in_project': assignment.role,
#                 'assigned_at': assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                
#                 # Data from the joined Projects and Clients tables
#                 'project_id': project.project_id,
#                 'project_name': project.project_name,
#                 'location': project.location,
#                 'due_date': project.due_date.isoformat() if project.due_date else None,
#                 'status': project.status or 'Not Started',
#                 'client_name': client_name,
#                 'company_id': project.company_id # Assuming Projects model has company_id
#             })

#         # 5. Return the full list response
#         return jsonify({
#             'user_id': user_id,
#             'projects': project_list,
#             'total_projects': len(project_list)
#         }), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": f"An error occurred: {str(e)}"}), 500


# @user_bp.route('/users/projects', methods=['GET'])
# @jwt_required 
# def get_user_all_projects_from_assignments():
#     """
#     Retrieves ALL projects assigned to the current user.
#     """
#     try:
#         # The jwt_required decorator correctly sets this attribute on the request object
#         user_id = request.current_user_id  

#         project_status_filter = request.args.get('status')
#         role_filter = request.args.get('role')

#         # 1. Query assignments for the user
#         # It's better to use joins/subqueries for performance if possible, 
#         # but sticking to the current structure for minimal changes.
#         query = ProjectAssignments.query.filter(
#             ProjectAssignments.user_id == user_id,
#             ProjectAssignments.is_assigned == True
#         )

#         if role_filter:
#             # Added a more robust check for non-empty string for the filter
#             query = query.filter(ProjectAssignments.role.ilike(f"%{role_filter}%"))

#         assignments = query.all()
#         project_list = []
#         project_ids = [assignment.project_id for assignment in assignments]

#         # 2. Bulk fetch all relevant projects to reduce database hits (optimization)
#         if project_ids:
#             # Start with a query for all relevant projects
#             projects_query = Projects.query.filter(Projects.project_id.in_(project_ids))
            
#             # Apply status filter if present
#             if project_status_filter:
#                 projects_query = projects_query.filter(Projects.status == project_status_filter)
            
#             # Fetch all matching projects
#             projects = projects_query.all()
            
#             # Create a dictionary for quick lookup: {project_id: project_object}
#             project_map = {p.project_id: p for p in projects}

#             # 3. Iterate through assignments and combine data
#             for assignment in assignments:
#                 project = project_map.get(assignment.project_id)
                
#                 # Check if the project was found AND if it passed the status filter
#                 # If a project was filtered out in the projects_query, it won't be in project_map
#                 if not project:
#                     continue

#                 # Safely get client name using the relationship (assuming Project model has a 'client' relationship)
#                 client_name = getattr(project.client, "client_name", None) if hasattr(project, 'client') else None

#                 project_list.append({
#                     "assignment_id": assignment.assignment_id,
#                     "user_role_in_project": assignment.role,
#                     "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
#                     "project_id": project.project_id,
#                     "project_name": project.project_name,
#                     "location": project.location,
#                     "due_date": project.due_date.isoformat() if project.due_date else None,
#                     "status": project.status or "Not Started",
#                     "client_name": client_name,
#                     "company_id": project.company_id
#                 })
        
#         # Original single-query logic (less efficient but matches your original code flow more closely):
#         # for assignment in assignments:
#         #     project = Projects.query.get(assignment.project_id)
#         #     if not project:
#         #         continue
#         #     # ... rest of the original filtering and appending logic ...


#         return jsonify({
#             "user_id": user_id,
#             "projects": project_list,
#             "total_projects": len(project_list)
#         }), 200

#     except Exception as e:
#         # Ensure rollback is called in case of any database error before the commit
#         db.session.rollback()
#         # Log the exception for debugging on the server side
#         print(f"Error retrieving user projects: {e}") 
#         return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

@user_bp.route('/users/<string:user_id>/projects', methods=['GET'])
# @jwt_required
def get_user_all_projects_from_assignments(user_id):
    """
    Retrieves ALL projects assigned to a specific user by querying the ProjectAssignments table.
    No pagination is applied.
    """

    project_status_filter = request.args.get('status')
    role_filter = request.args.get('role')

    try:
        # 1. Base Query
        query = ProjectAssignments.query.filter(
            ProjectAssignments.user_id == user_id,
            ProjectAssignments.is_assigned == True
        )

        # 2. Role filter
        if role_filter:
            query = query.filter(ProjectAssignments.role.ilike(f'%{role_filter}%'))

        assignments = query.all()

        project_list = []

        for assignment in assignments:
            project = Projects.query.get(assignment.project_id)

            if not project:
                continue

            # Status filter
            if project_status_filter and project.status != project_status_filter:
                continue

            client_name = (
                project.client.client_name
                if hasattr(project, 'client') and project.client
                else None
            )

            project_list.append({
                'assignment_id': assignment.assignment_id,
                'user_role_in_project': assignment.role,
                'assigned_at': assignment.assigned_at.isoformat() if assignment.assigned_at else None,

                'project_id': project.project_id,
                'project_name': project.project_name,
                'location': project.location,
                'due_date': project.due_date.isoformat() if project.due_date else None,
                'status': project.status or 'Not Started',
                'client_name': client_name,
                'company_id': project.company_id
            })

        return jsonify({
            'user_id': user_id,
            'projects': project_list,
            'total_projects': len(project_list)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    


#------------------------FOR ADMIN------------------------------
@user_bp.route('/companies/<string:company_id>/projects', methods=['GET'])
@jwt_required
def get_all_projects_for_company(company_id):
    try:
        projects = Projects.query.filter_by(company_id=company_id).all()

        data = [{
            "project_id": p.project_id,
            "project_name": p.project_name,
            "status": p.status,
            "location": p.location,
            "due_date": p.due_date.isoformat() if p.due_date else None
        } for p in projects]

        return jsonify({
            "company_id": company_id,
            "total_projects": len(data),
            "projects": data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

#-----------------------FOR ADMIN-----------------------------
# @user_bp.route('/companies/<string:company_id>/projects/<string:project_id>', methods=['GET'])
# @jwt_required
# def get_specific_project(company_id, project_id):
#     try:
#         project = Projects.query.filter_by(project_id=project_id, company_id=company_id).first()

#         if not project:
#             return jsonify({"message": "Project not found"}), 404

#         data = {
#             "project_id": project.project_id,
#             "project_name": project.project_name,
#             "status": project.status,
#             "location": project.location,
#             "due_date": project.due_date.isoformat() if project.due_date else None
#         }

#         return jsonify(data), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500




