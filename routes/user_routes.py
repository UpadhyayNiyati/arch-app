import time
from flask import Blueprint , jsonify , request , url_for
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
import inspect
import jwt
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer


# from architect_mngmnt_app.archs import bcrypt as Bcrypt
from datetime import datetime, timedelta , timezone
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



# def decode_reset_token(token):
#     """Decodes and validates a password reset JWT token, checking its type."""
#     # 1. Decode using the central helper function
#     result = decode_jwt_custom(
#         token,
#         PASSWORD_RESET_SECRET,
#         options={"require": ["exp", "user_id", "type"]}
#     )

#     # 2. Check if the token was technically valid (not expired/invalid signature)
#     if not result.get("valid"):
#         return result # Return the error dictionary (expired/invalid)

#     # 3. Apply password-reset specific business logic
#     decoded_data = result["data"]
#     if decoded_data.get('type') != 'password_reset':
#         return {"message": "Invalid token type", "invalid": True, "valid": False}

#     # 4. Success
#     return decoded_data

def decode_reset_token(token):
    secret = PASSWORD_RESET_SECRET

    try:
        # Introspect what params decode_jwt_custom supports
        sig = inspect.signature(decode_jwt_custom)
        params = sig.parameters

        # Build only allowed arguments
        kwargs = {}
        if "algorithms" in params:
            kwargs["algorithms"] = ["HS256"]
        if "options" in params:
            kwargs["options"] = {"verify_exp": True}

        return decode_jwt_custom(token, secret, **kwargs)

    except TypeError:
        # Fallback: call with ONLY token + secret
        return decode_jwt_custom(token, secret)


import jwt
import time

def decode_jwt_custom(token, secret):
    try:
        print(secret)
        print(token)
        # Decode WITHOUT UTC exp check
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_exp": False}
        )

        # Manual expiration check (IST system time)
        now_ts = time.time()

        if "exp" in payload:
            if payload["exp"] < now_ts:
                print("DEBUG: Token expired (IST check)")
                raise ValueError("Expired token")

        return payload

    except Exception as e:
        print("DEBUG: JWT decode error ->", str(e))
        raise ValueError("Invalid token")
# def decode_jwt_custom(jwt_token, secret_key):
#     try:
#         print("PYTHON time.time():", time.time())
#         print("datetime.utcnow():", datetime.utcnow().timestamp())      
#         print("SERVER TIME:", datetime.utcnow().timestamp())
#         decoded_unverified = jwt.decode(jwt_token, options={"verify_signature": False})
#         print("TOKEN EXP:", decoded_unverified.get("exp"))
#         print("DIFF =", datetime.utcnow().timestamp() - decoded_unverified.get("exp"))
#                 # Decode the token and verify its signature

#         print("jwt_token",jwt_token)
#         # Setting options to require an expiration claim (exp)
#         decoded = jwt.decode(
#             jwt_token,
#             secret_key,
#             algorithms=["HS256"],
#             leeway=20000 
#             # options={"require": ["exp", "user_id", "type"]}
#         )
#         print(decoded)
#         return decoded
#     except jwt.ExpiredSignatureError:
#         return {"message": "Token has expired", "expired": True}
#     except jwt.InvalidTokenError:
#         return {"message": "Invalid token", "invalid": True}

# --- Custom Decorator for Authentication (Replacing the Flask-JWT-Extended one) ---
# Since we are using custom token creation, we need a custom required decorator.

# def custom_jwt_required(token_type='access'):
#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             auth_header = request.headers.get("Authorization")
#             print("Authorization Header:", auth_header)
#             if not auth_header or not auth_header.startswith("Bearer "):
#                 return jsonify({"error": "Authorization header is missing or invalid"}), 401

#             token = auth_header.split(" ")[1]
#             secret = ACCESS_TOKEN_SECRET if token_type == 'access' else REFRESH_TOKEN_SECRET
            
#             try:
#                 payload = decode_jwt_custom(token, secret)
                
#                 if payload.get("message"): # Check for expiration or invalid messages
#                     exp = payload.get("exp")

#                     if exp and exp < time.time():
#                         return jsonify({"error": "Token has expired"}), 401
#                     if payload.get("invalid"):
#                         return jsonify({"error": "Invalid token"}), 401
#                     return jsonify({"error": payload.get("message", "Token validation failed")}), 401

#                 user_id = payload.get("user_id")
#                 print(user_id)
#                 company_id = payload.get("company_id")
#                 if not user_id:
#                     return jsonify({"message": "Unauthorized: Token missing user identity"}), 401
                
#                 # Attach user_id to the request context for use in the decorated function
#                 # (Simulating what get_jwt_identity() does)
#                 request.current_user_id = user_id
#                 request.current_company_id = company_id

#             except Exception as e:
#                 return jsonify({"error": str(e)}), 401

#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator

def jwt_required_now(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authorization header is missing or invalid"}), 401

        parts = auth_header.split(" ")

        if len(parts) != 2 or parts[0].lower() != "bearer":
            logging.error("Invalid Authorization header format")
            raise ValueError("Invalid Authorization header format. Expected: Bearer <token>")
       
        token = parts[1].strip()

        if token == "":
            return jsonify({"error": "Bearer token missing"}), 401
        
        try:
           
            try:
                payload = decode_jwt_custom(token, ACCESS_TOKEN_SECRET)
                print(payload)
            except Exception as e:
                return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401
            user_id = payload.get("user_id")
            if not user_id:
             return jsonify({"error": "Invalid token payload"}), 401
        except Exception as e:
            return jsonify({"error": str(e)}), 401

        return f(*args, **kwargs)
    return decorated_function

def custom_jwt_required(token_type='access'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            print(auth_header)
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Authorization header is missing or invalid"}), 401
            token = auth_header.split(" ")[1]
            secret = ACCESS_TOKEN_SECRET if token_type == 'access' else REFRESH_TOKEN_SECRET
            print(token)
            print(secret)
            try:
                payload = decode_jwt_custom(token, secret)
                print(payload)
                # Flags from decoder
                if payload.get("invalid") or payload.get("expired"):
                    return jsonify({"error": payload.get("message", "Invalid token")}), 401
                
                # Safe exp check
                exp = payload.get("exp")
                if exp:
                    exp = int(exp)
                    now = int(datetime.utcnow().timestamp())
                    if exp < now:
                        return jsonify({"error": "Token has expired"}), 401

                # Extract fields
                user_id = payload.get("user_id")
                print(user_id)
                company_id = payload.get("company_id")
                print(company_id)

                if not user_id:
                    return jsonify({"message": "Unauthorized: Token missing user identity"}), 401

                request.current_user_id = user_id
                request.current_company_id = company_id

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


# def create_access_token_custom(user_id, company_id):
#     # expiration = datetime.utcnow() + timedelta(minutes=15)
#     exp = int(time.time()) + 3600  # 1 hour expiry
#     integer_converted=int(exp.timestamp())
#     payload = {'user_id': user_id, 'company_id': company_id, 'exp': integer_converted, 'type': 'access'}
#     print(payload)
#     return jwt.encode(payload, ACCESS_TOKEN_SECRET, algorithm='HS256')

def create_access_token_custom(user_id, company_id):
    # Calculate expiry as an integer Unix timestamp (current time + 3600 seconds/1 hour)
    exp = int(time.time()) + 3600  # exp is already the correct integer value
    
    # integer_converted = int(exp.timestamp()) # REMOVE THIS LINE ENTIRELY

    # Use 'exp' directly
    payload = {'user_id': user_id, 'company_id': company_id, 'exp': exp, 'type': 'access'}
    print(payload)
    return jwt.encode(payload, ACCESS_TOKEN_SECRET, algorithm='HS256')

# def create_refresh_token_custom(user_id, company_id):
#     # expiration = datetime.utcnow() + refresh_token_expiry_time
#     exp = int(time.time()) + 7 * 24 * 60 * 60
#     payload = {'user_id': user_id, 'company_id': company_id, 'exp': exp.timestamp(), 'type': 'refresh'}
#     return jwt.encode(payload, REFRESH_TOKEN_SECRET, algorithm='HS256')


def create_refresh_token_custom(user_id, company_id):
    # Calculate expiry as an integer Unix timestamp (current time + 7 days)
    exp = int(time.time()) + 7 * 24 * 60 * 60
    
    # Use 'exp' directly (it's already an integer timestamp)
    payload = {'user_id': user_id, 'company_id': company_id, 'exp': exp, 'type': 'refresh'}
    return jwt.encode(payload, REFRESH_TOKEN_SECRET, algorithm='HS256')

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
            return jsonify({"message" : "User added successfully"}) , 201
        except Exception as e:
            return jsonify({"error" : str(e)}) , 500
        

#user registration route
@user_bp.route('/register' , methods = ['POST'])
def register_user():
    """
    User Registration (Step 1: Create User & Send OTP)
    ---
    tags:
      - User Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/UserRegister'
    responses:
      201:
        description: User registered. OTP sent to email.
      400:
        description: Missing required fields.
      409:
        description: User with this email already exists.
      500:
        description: Server error during registration or OTP generation/sending.
    """
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

#protected_route
@user_bp.route('/user/protected' , methods = ['GET'])
@custom_jwt_required()
def protected_route():
    # Access the claims directly from the request context!
    return jsonify({
        "message" : "You have access to this protected resource.", 
        "user_id" : request.current_user_id,
        "company_id": request.current_company_id
    }) , 200

from datetime import datetime , timezone , timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# @user_bp.route('/refresh', methods=['POST'])
# @custom_jwt_required(token_type='refresh')
# def refresh_token():
#     try:
#         # 1. Extract token
#         refresh_token = get_auth_key_from_request()

#         # 2. Decode token manually using IST timestamps
#         payload = decode_jwt_custom(refresh_token, REFRESH_TOKEN_SECRET)

#         user_id = payload.get('user_id')
#         if not user_id:
#             return jsonify({"message": "Token payload missing user ID."}), 401

#         # 3. Fetch user
#         user = User.query.get(user_id)
#         if not user:
#             return jsonify({"message": "User not found."}), 404

#         company_id = user.company_id  # always from DB

#         # 4. Refresh token revocation check — MUST use IST
#         now_ist = datetime.now(IST)

#         stored_token_record = db.session.query(UserToken).filter(
#             UserToken.token == refresh_token,
#             UserToken.user_id == user_id,
#             UserToken.expires_at > now_ist
#         ).first()

#         if not stored_token_record:
#             return jsonify({
#                 "message": "Invalid, revoked, or expired refresh token. Please log in again."
#             }), 401

#         # 5. Create new access token
#         new_access_token = create_access_token_custom(user_id, company_id)

#         return jsonify({
#             "access_token": new_access_token
#         }), 200

#     except Exception as e:
#         db.session.rollback()
#         logging.error(f"Error during token refresh: {e}", exc_info=True)
#         return jsonify({'message': f'Server error: {str(e)}'}), 500

# @user_bp.route('/refresh', methods=['POST'])
# @jwt_required_now
# def refresh_token():
#     try:
#         refresh_token = get_auth_key_from_request()

#         # Decode using IST-friendly function
#         payload = decode_jwt_custom(refresh_token, REFRESH_TOKEN_SECRET)

#         user_id = payload.get('user_id')
#         if not user_id:
#             return jsonify({"message": "Token payload missing user ID."}), 401

#         user = User.query.get(user_id)
#         if not user:
#             return jsonify({"message": "User not found."}), 404

#         # company_id must come from DB
#         company_id = user.company_id
#         print(company_id)
#         if not company_id:
#             return jsonify({"message": "User does not belong to any company."}), 400

#         # IST now
#         now_ist = datetime.now(IST)

#         # Convert IST to UTC if your DB stores UTC timestamps
#         now_utc = now_ist.astimezone(timezone.utc)

#         stored_token_record = db.session.query(UserToken).filter(
#             UserToken.token == refresh_token,
#             UserToken.user_id == user_id,
#             UserToken.expires_at > now_utc      # FIXED
#         ).first()

#         if not stored_token_record:
#             return jsonify({
#                 "message": "Invalid, revoked, or expired refresh token. Please log in again."
#             }), 401

#         new_access_token = create_access_token_custom(user_id, company_id)

#         return jsonify({
#             "access_token": new_access_token
#         }), 200

#     except Exception as e:
#         db.session.rollback()
#         logging.error(f"Error during token refresh: {e}", exc_info=True)
#         return jsonify({'message': f'Server error: {str(e)}'}), 500



# @user_bp.route('/refresh' , methods = ['POST'])
# @custom_jwt_required(token_type = 'refresh')
# def refresh_token():
#     current_user_id = get_jwt_identity()
#     auth_header = request.headers.get('Authorization')
#     if not auth_header or not auth_header.startswith('Bearer '):
#         # This should rarely happen as jwt_required usually catches it, but it's safe.
#         return jsonify({"message": "Authorization header missing or malformed"}), 400
#     token_to_check = auth_header.split()[1]
#     token_record = UserToken.query.filter(
#             UserToken.user_id == current_user_id,
#             UserToken.token == token_to_check,
#             UserToken.expires_at > datetime.utcnow()
#         ).first()
#     if not token_record:
#             # If the token is not found, it means it was revoked (via /logout) or is expired.
#             return jsonify({"message": "Invalid or revoked refresh token. Please log in again."}), 401
#     new_access_token = create_access_token(identity = current_user_id , expires_delta = timedelta(minutes = 15))
#     return jsonify({

#         "access_token" : new_access_token
#     }) , 200


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
    return jsonify({"message" : "User updated successfully!!"}) , 200

#delete user
@user_bp.route('/del_user/<string:user_id>' , methods = ['DELETE'])
def del_user(user_id):
    """
    Delete User
    ---
    tags:
      - User Management
    parameters:
      - name: user_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: User deleted successfully.
      404:
        description: User not found.
      500:
        description: Server error during deletion.
    """
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
    """
    Verify Registration OTP (Step 2: OTP Verification & Final Login)
    ---
    tags:
      - User Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/OtpVerify'
    responses:
      200:
        description: Registration complete and OTP verified. Returns access tokens.
        schema:
          $ref: '#/definitions/AuthResponse'
      400:
        description: Missing required fields.
      401:
        description: Invalid, expired, or used OTP code.
      404:
        description: User not found.
    """
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
        
        company_id = user.company_id

        # You might want to 'activate' the user here if you have an 'is_active' column
        # user.is_active = True 
        # db.session.commit()

        # Generate access token
        # access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(minutes=15))
        # refresh_token = create_refresh_token(identity=user.user_id , expires_delta = timedelta(days = 7))
        access_token = create_access_token_custom(user.user_id, company_id)     
        refresh_token = create_refresh_token_custom(user.user_id, company_id)
        
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
    
access_token_expiry_time=timedelta(minutes=30)
refresh_token_expiry_time=timedelta(days=7)

ACCESS_TOKEN_SECRET=str(os.getenv('ACCESS_TOKEN_SECRET'))
REFRESH_TOKEN_SECRET=str(os.getenv('REFRESH_TOKEN_SECRET'))




    
# def decode_reset_token(token):
#     """Decodes and validates a password reset JWT token."""
#     # It just delegates the complex work to the reusable helper
#     return decode_jwt_custom(token, 
#                              PASSWORD_RESET_SECRET, 
#                              expected_type='password_reset')


 


# --- NEW: OTP Verification for Login ---
@user_bp.route('/verify_login_otp', methods=['POST'])
def verify_login_otp():
    """
    Verify Login OTP (Step 2: OTP Verification & Final Login)
    ---
    tags:
      - User Authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/OtpVerify'
    responses:
      200:
        description: Login successful. Returns access tokens.
        schema:
          $ref: '#/definitions/AuthResponse'
      400:
        description: Missing required fields.
      401:
        description: Invalid, expired, or used OTP code.
      404:
        description: User not found.
    """
    data = request.json
    user_email = data.get("user_email")
    otp_code = data.get("otp_code")

    if not all([user_email and otp_code]):
        return jsonify({"message": "OTP code are required"}), 400

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
        print(company_id)
        # Generate access token
        # access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(days=1))
        refresh_token_delta = timedelta(days = 7)
        # refresh_token = create_refresh_token(identity=user.user_id , expires_delta = refresh_token_delta)
        access_token = create_access_token_custom(user.user_id, company_id) # <-- Use Custom
        refresh_token = create_refresh_token_custom(user.user_id, company_id)

        #generate uuid
        token_id = generate_uuid()

        #store the access and refresh tokens
        refresh_token_expires_at = datetime.now(IST) + refresh_token_delta
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

# Helper function to decode and validate a password reset JWT
# def decode_reset_token(token):
#     try:
#         decoded = jwt.decode(
#             token,
#             PASSWORD_RESET_SECRET,
#             algorithms=["HS256"],
#             options={"require": ["exp", "user_id", "type"]}
#         )
#         if decoded.get('type') != 'password_reset':
#             return {"message": "Invalid token type", "invalid": True}
#         return decoded
#     except jwt.ExpiredSignatureError:
#         return {"message": "Token has expired", "expired": True}
#     except jwt.InvalidTokenError:
#         return {"message": "Invalid token", "invalid": True}
    
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
            # 3. Generate a time-limited **JWT Token**
            reset_token = create_reset_token(user.user_id)
            
            # 4. Construct the reset link for the client to use.
            # NOTE: 'user.reset_password' is a placeholder endpoint name. 
            # It should match the actual endpoint for the reset POST request in your application (e.g., your frontend's link).
            # For this backend, we point to the token validation endpoint.
            # Replace 'auth.reset_password' with the correct blueprint/route if necessary, 
            # or hardcode the expected frontend URL.
            reset_url = f"http://localhost:5173/reset-password?token={reset_token}" # Adjust this URL for your client
            
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
        return jsonify({"message": "Role added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@user_bp.route('/company_projects')
@custom_jwt_required()
def get_company_projects():
    # Get payload from the validated token
    auth_header = get_auth_key_from_request()
    payload = decode_jwt_custom(auth_header, ACCESS_TOKEN_SECRET)
    
    current_company_id = payload.get('company_id') # Quick access to company_id

    # Filter all queries by company_id for security and performance
    projects = Projects.query.filter_by(company_id=current_company_id).all()
    # ... rest of the logic
