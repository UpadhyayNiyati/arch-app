
from datetime import datetime, timedelta
import logging
from random import random
import uuid
import bcrypt
from flask import Flask
from flask_bcrypt import Bcrypt
from flask import Blueprint, jsonify, request
from flask_mail import Mail
from sqlalchemy import and_
import random
# from architect_backend0.routes.clients_routes import send_email
from routes.clients_routes import send_email
from models import OtpCode, User, UserToken,db, generate_uuid
# from werkzeug.security import generate_password_hash,check_password_hash
from auth.authhelpers import  REFRESH_TOKEN_SECRET, create_access_token, create_refresh_token, decode_jwt,  jwt_required, refresh_token_expiry_time
from werkzeug.exceptions import BadRequest
from sqlalchemy.exc import SQLAlchemyError

auth_bp = Blueprint('auth', __name__ ,url_prefix="/api/auth")

app = Flask(__name__)
bcrypt = Bcrypt(app)


@auth_bp.route("/login" , methods = ['POST'])
def login_user():
    """
    User Login (Step 1: Credentials Check and OTP Trigger)
    ---
    tags:
      - User Authentication
    description: Authenticates user credentials (email/password) and sends a login verification OTP via email.
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: UserLogin
          properties:
            user_email:
              type: string
              format: email
              description: The user's registered email address.
            user_password:
              type: string
              format: password
              description: The user's password.
    responses:
      200:
        description: OTP successfully generated and sent for login verification.
        schema:
          type: object
          properties:
            message:
              type: string
              example: OTP sent for login verification. Please check your email.
      400:
        description: Missing email or password in the request body.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Email and password are required
      401:
        description: Invalid email or password provided.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Invalid email or password
      500:
        description: Server error during OTP generation or email sending.
    """
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
    




@auth_bp.route('/verify_login_otp', methods=['POST'])
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
       
        access_token = create_access_token(user.user_id, company_id) # <-- Use Custom
        refresh_token = create_refresh_token(user.user_id, company_id)

        #generate uuid
        token_id = generate_uuid()

        print(access_token)
        print(refresh_token)
        expires_at=datetime.utcnow() + refresh_token_expiry_time

        new_token_record = UserToken(
            user_id = user.user_id , 
            token = refresh_token , 
            expires_at = expires_at
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





@auth_bp.route("/refresh", methods=['GET', 'POST'])
def refresh():
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({'message': 'Refresh token is required!'}), 400

        payload = decode_jwt(refresh_token, REFRESH_TOKEN_SECRET)
        if not payload or 'message' in payload:
            return jsonify({'message': payload.get('message', 'Invalid token')}), 401

        user_id = payload['user_id']
        company_id = payload['company_id']

        stored_token = db.session.query(UserToken).filter(
            and_(
                UserToken.token == refresh_token,
                UserToken.user_id == user_id
            )
        ).first()

        if not stored_token:
            return jsonify({'message': 'Invalid refresh token!'}), 401

        # Delete old token
        db.session.delete(stored_token)

        # Create new tokens
        new_access_token = create_access_token(user_id=user_id, company_id=company_id)
        new_refresh_token = create_refresh_token(user_id=user_id, company_id=company_id)

        # Store new refresh token
        now = datetime.utcnow()
        refresh_token_expiry_time = timedelta(days=7)  # Adjust as needed

        new_token = UserToken(
            token_id=uuid.uuid4(),
            user_id=user_id,
            token=new_refresh_token,
           
            expires_at=now + refresh_token_expiry_time
        )

        db.session.add(new_token)
        db.session.commit()

        return jsonify({
            'message': 'Token refreshed successfully!',
            'access_token': new_access_token,
            'refresh_token': new_refresh_token
        }), 200

    except Exception as e:
        return jsonify({'message': 'An error occurred', 'error': str(e)}), 500
    

@auth_bp.route('/logout' , methods = ['POST'])#take refresh token in logout also and delete it
def logout_user():
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({"message": "Refresh token is required."}), 400
        
        # 1. Decode the token to get claims (using the refresh token secret)
        payload = decode_jwt(refresh_token, REFRESH_TOKEN_SECRET)
        
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
