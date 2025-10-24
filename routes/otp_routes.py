from flask import Blueprint , jsonify , request
from models import OtpCode,db , User
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from datetime import datetime , timedelta
import random
import os
from email.message import EmailMessage
import smtplib
import uuid

otp_bp = Blueprint('otp', __name__)
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


#verify otp
# Assuming all other imports and code from your prompt are present

# The corrected code for the verify_otp route
# In your otp_routes.py file
@otp_bp.route("/verify-otp", methods=['POST'])
def verify_otp():
    data = request.json
    user_id = data.get("user_id") # Get the user ID from the request body
    otp_code = data.get("otp_code")
    user_email = data.get("user_email") # Still get email for a final check

    if not all([user_id, otp_code, user_email]):
        return jsonify({"message": "User ID, email, and OTP are required"}), 400

    try:
        # Query the OtpCode table using the correct column: user_id
        otp_record = OtpCode.query.filter_by(
            user_id=user_id,
            otp_code=otp_code
        ).first()
        
        if not otp_record or otp_record.expires_at < datetime.utcnow() or otp_record.is_used:
            return jsonify({"message": "Invalid, expired, or used OTP"}), 400

        # ... (rest of your verification logic)
        
        user = User.query.filter_by(user_id=user_id, user_email=user_email).first()
        if user:
            otp_record.is_used = True
            db.session.commit()
            
            # Send the success email
            # ...
            
            return jsonify({"message": "OTP verified successfully. Your account is now active!"}), 200
        else:
            db.session.rollback()
            return jsonify({"message": "User not found."}), 404
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500