from flask import Blueprint , jsonify , request
from models import User , db , OtpCode , ProjectAssignments , Clients , Projects , Tasks , Projectvendor , Vendors , Boards ,Pin , ProjectTemplates , Templates , Role , UserToken , UserRole
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
import jwt
from flask_cors import CORS

# from architect_mngmnt_app.archs import bcrypt as Bcrypt
from datetime import datetime , timedelta
import uuid

user_bp = Blueprint('user' , __name__)
bcrypt = Bcrypt()

# Helper function to send email
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

CORS(user_bp)

def generate_uuid():
    return str(uuid.uuid4())

@user_bp.route('/get_users' , methods = ['GET'])
def get_all_users():
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
                'role_name': role.role_name         # Added role_name from the joined table
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
    
    user_with_roles = db.session.query(User , Role)\
        .join(Role, User.role_id == Role.role_id)\
        .all()

    result = {
        'user_id' : user.user_id , 
        'user_name' : user.user_name , 
        'user_email' : user.user_email , 
        'user_password' : user.user_password , 
        'user_address' : user.user_address , 
        'created_at' : user.created_at
    }
    return jsonify(result) , 200

#post user
@user_bp.route('/post_user' , methods = ['POST'])
def post_user():
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
                user_address = data['user_address'] 
            )
            db.session.add(new_user)
            db.session.commit()
            return jsonify({"message" : "User added successfully"}) , 201
        except Exception as e:
            return jsonify({"error" : str(e)}) , 500
        

#user registration route
@user_bp.route('/register' , methods = ['POST'])
def register_user():
    data = request.json
    user_name = data.get("user_name")
    user_email = data.get("user_email")
    # user_phone = data.get("user_phone")
    # user_address = data.get("user_address")
    user_password = data.get("user_password")

    if not all([user_name, user_email, user_password]):
        return jsonify({"message": "All fields are required"}), 400

    existing_user = User.query.filter_by(user_email=user_email).first()
    if existing_user:
        return jsonify({"message": "User with this email already exists"}), 409

    try:
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(user_password).decode('utf-8')

        new_user = User(
            user_name=user_name,
            user_email=user_email,
            # user_phone=user_phone,
            # user_address=user_address,
            user_password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        
        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now() + timedelta(minutes = 5)
        new_otp = OtpCode(
            user_id=new_user.user_id,
            otp_code=otp_code,
            expires_at=expires_at,
            type='registration'
        )
        db.session.add(new_otp)
        db.session.commit()

        # Send OTP via email
        send_email(
            recipients=[user_email],
            subject="Your Registration OTP",
            body=f"Hello {user_name},\n\nYour OTP code is {otp_code}. It is valid for 5 minutes."
        )

        return jsonify({"message": "User registered. Please check your email for the OTP."}), 201
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#user login route
@user_bp.route("/login" , methods = ['POST'])
def login_user():
    data = request.json
    user_email = data.get("user_email")
    user_password = data.get("user_password")

    if not all([user_email , user_password]):
        return jsonify({"message":"Email and password are required"}) , 400
    
    user = User.query.filter_by(user_email=user_email).first()

    if user and bcrypt.check_password_hash(user.user_password , user_password):
        try:
            OtpCode.query.filter_by(user_id = user.user_id).delete()
            db.session.commit()

            #generate new otp
            otp_code = str(random.randint(100000 , 999999))
            expires_at = datetime.now() + timedelta(minutes = 5)

            new_otp = OtpCode(
                user_id = user.user_id,
                otp_code = otp_code ,
                expires_at = expires_at,
                type = 'login'
            )
            db.session.add(new_otp)
            db.session.commit()

            send_email(
                recipients=[user_email],
                subject="Login Verification OTP",
                body=f"Hello {user.user_name},\n\nYour login verification code is {otp_code}. It is valid for 5 minutes."
            )

            return jsonify({"message": "OTP sent for login verification. Please check your email."}), 200
        
        except Exception as e:
            return jsonify({"error" : str(e)}) , 500
    else:
        return jsonify({"message" : "Invalid email or password"}) , 401
    
#protected_route
@user_bp.route('/user/protected' , methods = ['GET'])
@jwt_required()
def protected_route():
    current_user_id = get_jwt_identity()
    return jsonify({"message" : "You have access to this protected resource." , 
                    "user_id" : current_user_id
                    }) , 200

@user_bp.route('/refresh' , methods = ['POST'])
@jwt_required(refresh = True)
def refresh_token():
    current_user_id = get_jwt_identity()
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        # This should rarely happen as jwt_required usually catches it, but it's safe.
        return jsonify({"message": "Authorization header missing or malformed"}), 400
    token_to_check = auth_header.split()[1]
    token_record = UserToken.query.filter(
            UserToken.user_id == current_user_id,
            UserToken.token == token_to_check,
            UserToken.expires_at > datetime.utcnow()
        ).first()
    if not token_record:
            # If the token is not found, it means it was revoked (via /logout) or is expired.
            return jsonify({"message": "Invalid or revoked refresh token. Please log in again."}), 401
    new_access_token = create_access_token(identity = current_user_id , expires_delta = timedelta(minutes = 15))
    return jsonify({

        "access_token" : new_access_token
    }) , 200


#update user    
@user_bp.route('/update_user/<string:user_id>' , methods = ['PUT'])
def update_user(user_id):           
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
    return jsonify({"message" : "User updated successfully!!"}) , 200

#delete user
@user_bp.route('/del_user/<string:user_id>' , methods = ['DELETE'])
def del_user(user_id):
    user = User.query.get_or_404(user_id)
    if not user:
        return jsonify({"message":"User not found"}) , 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message" : "User deleted successfully!!"}) , 200


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
    
@user_bp.route('/verify_registration_otp', methods=['POST'])
def verify_registration_otp():
    data = request.json
    user_email = data.get("user_email")
    otp_code = data.get("otp_code")

    if not all([user_email, otp_code]):
        return jsonify({"message": "Email and OTP code are required"}), 400

    user = User.query.filter_by(user_email=user_email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Find the valid, unused, and unexpired OTP for this user and type
    otp_record = OtpCode.query.filter(
        OtpCode.user_id == user.user_id,
        OtpCode.otp_code == otp_code,
        OtpCode.expires_at > datetime.now(),
        OtpCode.is_used == False,
        OtpCode.type == 'registration'
    ).order_by(OtpCode.created_at.desc()).first()

    if otp_record:
        # Mark OTP as used
        otp_record.is_used = True
        db.session.commit()

        # You might want to 'activate' the user here if you have an 'is_active' column
        # user.is_active = True 
        # db.session.commit()

        # Generate access token
        access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(minutes=15))
        refresh_token = create_refresh_token(identity=user.user_id , expires_delta = timedelta(days = 7))
        
        # Send confirmation email
        send_email(
            recipients=[user_email],
            subject="Registration Successful!",
            body=f"Hello {user.user_name},\n\nYour account has been successfully verified and registered."
        )

        return jsonify({
            "message": "Registration complete and OTP verified. Login successful.",
            # "access_token": access_token,
            # "refresh_token" : refresh_token,
            "user_id": user.user_id
        }), 200
    else:
        # Increment attempt counter (optional, for brute-force protection)
        failed_otp = OtpCode.query.filter(
            OtpCode.user_id == user.user_id,
            OtpCode.otp_code == otp_code,
            OtpCode.type == 'user_registration'
        ).first()
        if failed_otp:
            failed_otp.attempts += 1
            db.session.commit()
            
        return jsonify({"message": "Invalid, expired, or used OTP code."}), 401
    
access_token_expiry_time=timedelta(minutes=10)
refresh_token_expiry_time=timedelta(days=7)

ACCESS_TOKEN_SECRET=str(os.getenv('ACCESS_TOKEN_SECRET'))
REFRESH_TOKEN_SECRET=str(os.getenv('REFRESH_TOKEN_SECRET'))
def create_access_token_custom(user_id, company_id):
    expiration = datetime.utcnow() + access_token_expiry_time
    payload = {'user_id': user_id, 'company_id': company_id, 'exp': expiration.timestamp(), 'type': 'access'}
    return jwt.encode(payload, ACCESS_TOKEN_SECRET, algorithm='HS256')

def create_refresh_token_custom(user_id, company_id):
    expiration = datetime.utcnow() + refresh_token_expiry_time
    payload = {'user_id': user_id, 'company_id': company_id, 'exp': expiration.timestamp(), 'type': 'refresh'}
    return jwt.encode(payload, REFRESH_TOKEN_SECRET, algorithm='HS256')

def decode_jwt_custom(jwt_token, secret_key):
    try:
        # Decode the token and verify its signature
        # Setting options to require an expiration claim (exp)
        decoded = jwt.decode(
            jwt_token,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "user_id", "type"]}
        )
        return decoded
    except jwt.ExpiredSignatureError:
        return {"message": "Token has expired", "expired": True}
    except jwt.InvalidTokenError:
        return {"message": "Invalid token", "invalid": True}

# --- Custom Decorator for Authentication (Replacing the Flask-JWT-Extended one) ---
# Since we are using custom token creation, we need a custom required decorator.

def custom_jwt_required(token_type='access'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Authorization header is missing or invalid"}), 401

            token = auth_header.split(" ")[1]
            secret = ACCESS_TOKEN_SECRET if token_type == 'access' else REFRESH_TOKEN_SECRET
            
            try:
                payload = decode_jwt_custom(token, secret)
                
                if payload.get("message"): # Check for expiration or invalid messages
                    if payload.get("expired"):
                         return jsonify({"error": "Token has expired"}), 401
                    if payload.get("invalid"):
                        return jsonify({"error": "Invalid token"}), 401

                user_id = payload.get("user_id")
                if not user_id:
                    return jsonify({"message": "Unauthorized: Token missing user identity"}), 401
                
                # Attach user_id to the request context for use in the decorated function
                # (Simulating what get_jwt_identity() does)
                request.current_user_id = user_id

            except Exception as e:
                return jsonify({"error": str(e)}), 401

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- Utility Functions for Role-Based Access Control (updated to use custom logic) ---

def get_auth_key_from_request():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Authorization header missing or malformed")
    return auth_header.split(" ")[1]

def get_user_id_from_auth_key(auth_key):
    try:
        payload = decode_jwt_custom(auth_key, ACCESS_TOKEN_SECRET)
        if payload.get("expired") or payload.get("invalid"): return None
        return payload.get('user_id')
    except Exception as e:
        logging.error(f"JWT decoding failed: {e}")
        return None
    
def get_user_role(auth_key):
    u_id = get_user_id_from_auth_key(auth_key)
    if not u_id:
        return None  
    # Assuming User model has a direct role_id column based on get_all_users logic
    user = User.query.get(u_id)
    if user and user.role_id:
        role = db.session.query(Role).filter_by(role_id=user.role_id).first()
        return role.role_name if role else None
    
    # Fallback to UserRole if User doesn't have role_id directly (checking existing code)
    userrole = db.session.query(UserRole).filter_by(user_id=u_id).first()
    if userrole:
        role = db.session.query(Role).filter_by(role_id=userrole.role_id).first()
        return role.role_name if role else None
    return None

def superAdmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_header = get_auth_key_from_request()
        except ValueError as e:
            return jsonify({"error": str(e)}), 401
            
        is_super_admin=get_user_role(auth_header)
        
        if is_super_admin != "Superadmin":
            return jsonify({"error" : "Only Super Admin can access this page"}),403
        return f(*args, **kwargs)
    return decorated_function
    

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_header = get_auth_key_from_request()
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

        is_admin = get_user_role(auth_header)
        
        if is_admin is None:
            return jsonify({"message": "Invalid or expired token"}), 401
        if is_admin != "Admin":
            return jsonify({"error" : "Only Admin can access this page"}),403
        return f(*args, **kwargs)
    return decorated_function

    


 


# --- NEW: OTP Verification for Login ---
@user_bp.route('/verify_login_otp', methods=['POST'])
def verify_login_otp():
    data = request.json
    user_email = data.get("user_email")
    otp_code = data.get("otp_code")

    if not all([user_email, otp_code]):
        return jsonify({"message": "Email and OTP code are required"}), 400

    user = User.query.filter_by(user_email=user_email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Find the valid, unused, and unexpired OTP for this user and type
    otp_record = OtpCode.query.filter(
        OtpCode.user_id == user.user_id,
        OtpCode.otp_code == otp_code,
        OtpCode.expires_at > datetime.now(),
        OtpCode.is_used == False,
        OtpCode.type == 'login'
    ).order_by(OtpCode.created_at.desc()).first()

    if otp_record:
        # Mark OTP as used
        otp_record.is_used = True
        db.session.commit()

        company_id = user.company_id
        
        # Generate access token
        access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(days=1))
        refresh_token_delta = timedelta(days = 7)
        refresh_token = create_refresh_token(identity=user.user_id , expires_delta = refresh_token_delta)

        #generate uuid
        token_id = generate_uuid()

        #store the access and refresh tokens
        refresh_token_expires_at = datetime.utcnow() + refresh_token_delta
        # refresh_token_hashed = generate_password_hash(refresh_token)

        new_token_record = UserToken(
            user_id = user.user_id , 
            token = refresh_token , 
            expires_at = refresh_token_expires_at
        )

        db.session.add(new_token_record)
        db.session.commit()

        
        # Send confirmation email
        send_email(
            recipients=[user_email],
            subject="Successful Login Notification",
            body=f"Hello {user.user_name},\n\nYour login attempt at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} was successful."
        )

        return jsonify({
            "message": "Login successful.",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user.user_id,
            "company_id": company_id
        }), 200
    else:
        # Increment attempt counter (optional, for brute-force protection)
        failed_otp = OtpCode.query.filter(
            OtpCode.user_id == user.user_id,
            OtpCode.otp_code == otp_code,
            OtpCode.type == 'user_login'
        ).first()
        if failed_otp:
            failed_otp.attempts += 1
            db.session.commit()
            
        return jsonify({"message": "Invalid, expired, or used OTP code."}), 401

# @user_bp.route('/refresh', methods=['POST'])
# @custom_jwt_required(token_type='refresh') # Require a valid refresh token
# def refresh_token():
#     try:
#         # The token is already validated by @custom_jwt_required('refresh')
#         auth_header = get_auth_key_from_request()
#         refresh_token = auth_header # The token is the refresh token itself from the header
        
#         # Get claims from the already decoded token (we use the same logic as custom_jwt_required)
#         payload = decode_jwt_custom(refresh_token, REFRESH_TOKEN_SECRET)
#         user_id = payload.get('user_id')
#         company_id = payload.get('company_id')

#         # 1. Database Check (Revocation/Expiry Check)
#         stored_token_record = db.session.query(UserToken).filter(
#             and_(
#                 UserToken.token == refresh_token,
#                 UserToken.user_id == user_id,
#                 UserToken.expires_at > datetime.utcnow()
#             )
#         ).first()

#         if not stored_token_record:
#             return jsonify({"message": "Invalid, revoked, or expired refresh token. Please log in again."}), 401
        
#         # 2. Generate new access token
#         new_access_token = create_access_token_custom(user_id, company_id)

#         # NOTE: Token Rotation (deleting old, creating new refresh token)
#         # is a more advanced pattern and is usually implemented here.
#         # For simplicity and to match the original attempt, we'll only return the new access token.

#         return jsonify({
#             "access_token": new_access_token
#         }), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'message': f'An unexpected server error occurred: {str(e)}'}), 500 

@user_bp.route('/logout' , methods = ['POST'])#take refresh token in logout also and delete it
def logout_user():
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({"message": "Refresh token is required."}), 400
        
        # 1. Decode the token to get claims (using the refresh token secret)
        payload = decode_jwt_custom(refresh_token, REFRESH_TOKEN_SECRET)
        
        if payload.get("message"):
            # Token is expired or invalid, but we should still try to delete it
            pass
        
        user_id = payload.get('user_id')
        token_type = payload.get('type')
        
        if not user_id or token_type != 'refresh':
            # Even if decoded, it might not be the correct token type or payload structure
            # We proceed with database deletion just in case, but warn if the token looks wrong
            logging.warning(f"Logout attempt with potentially invalid refresh token payload for user_id: {user_id}")

        # 2. Delete the refresh token from the database (revocation)
        # We look up *only* by the token string itself to revoke it, regardless of its status.
        rows_deleted = db.session.query(UserToken).filter(
            UserToken.token == refresh_token
        ).delete()
        
        db.session.commit()
        
        if rows_deleted == 0 and not payload.get("message"):
            # The token was structurally valid but not found in the DB (already revoked or expired from DB)
            return jsonify({'message': 'Logout successful. Token was not active or already logged out.'}), 200

        # 3. Success Response
        return jsonify({
            'message': 'Logout successful. Refresh token revoked.'
        }), 200

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"message": "A database error occurred during logout."}), 500
    except Exception as e:
        db.session.rollback() 
        logging.error(f"Unexpected error during logout: {e}", exc_info=True)
        return jsonify({'message': 'An unexpected server error occurred.'}), 500
    
@user_bp.route('/user/protected', methods=['GET'])
@custom_jwt_required # Use the custom decorator
def protected_route():
    # You would need to get the user ID from the token payload inside the route or via a helper
    # For now, let's keep the user_id extraction logic clean:
    try:
        token = get_auth_key_from_request()
        payload = decode_jwt_custom(token, ACCESS_TOKEN_SECRET)
        current_user_id = payload.get('user_id')
    except Exception:
        current_user_id = "Unknown" # Should be caught by the decorator, but good fallback

    return jsonify({
        "message": "You have access to this protected resource.",
        "user_id": current_user_id
    }), 200