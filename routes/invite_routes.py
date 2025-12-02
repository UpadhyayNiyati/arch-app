from flask import Flask, request, jsonify , Blueprint , g
from models import db , Invite , User
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import logging
from flask_cors import CORS
from utils.email_utils import send_email
import os
import secrets
import hashlib
from auth.auth import jwt_required
from functools import wraps
from utils.email_utils import send_email
from flask_bcrypt import Bcrypt
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash 

invite_bp = Blueprint('Invite' , __name__)
CORS(invite_bp)
bcrypt = Bcrypt()


# ... imports and setup ...

@invite_bp.route("/invite/send", methods=["POST"])
@jwt_required 
def send_invite():
    data = request.get_json()
    emails = data.get("emails")
    company_id = data.get("company_id")
    
    # Get user_id from the request object, which was set by the decorator
    created_by_user_id = request.current_user_id 
    
    if not emails or not isinstance(emails, list):
        return jsonify({"error": "A list of emails is required"}), 400

    invite_links = []
    successful_sends = []
    failed_sends = []

    for email in emails:
        raw_token = secrets.token_urlsafe(16)
        salt = secrets.token_hex(16)
        token_hash = hashlib.sha256((salt + raw_token).encode()).hexdigest()
        
        # 1. Prepare the invite link
        invite_link = f"http://localhost:5173/invite/accept?token={raw_token}"

        invite = Invite(
            email=email,
            company_id=company_id,
            created_by_user_id=created_by_user_id, 
            raw_token_id=raw_token[:8],
            token_hash=token_hash,
            salt=salt,
            expires_at=datetime.utcnow() + timedelta(hours=72),
            single_use=True
        )

        db.session.add(invite)
        
        # 2. Add the link to the response list
        invite_links.append({"email": email, "invite_link": invite_link})

        # 3. *** ADDED: Logic to send the email ***
        try:
            subject = "You've been invited to join Architect's App!"
            # You should use an HTML template in a real app, but this is a simple text body
            body = f"Hello,\n\nYou have been invited to join a company on Architect App. Click the link below to accept the invitation and set up your account:\n\n{invite_link}\n\nThis link will expire in 72 hours."
            
            # Assuming send_email(recipient, subject, body) is the correct signature
            send_email(
                recipients=[email], # Changed from (email, subject, body)
                subject=subject,
                body=body
            )
            successful_sends.append(email)
            logging.info(f"Invite email successfully queued for {email}")

        except Exception as e:
            failed_sends.append(email)
            # Log the error, but continue processing other emails
            logging.error(f"FATAL: Failed to send invite email to {email} - Error: {e}")


    try:
        # Commit all invites to the database *after* attempting to send emails
        db.session.commit()
    except Exception as e:
        # Handle database commit error (e.g., rollback)
        logging.error(f"Database commit failed after processing invites: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to save invites to database after email attempts."}), 500

    
    # 4. Refine the final response to include status
    response_message = "Invites processed."
    if successful_sends:
        response_message += f" Successfully sent {len(successful_sends)} emails."
    if failed_sends:
        response_message += f" Failed to send {len(failed_sends)} emails."

    return jsonify({
        "message": response_message, 
        "invite_links": invite_links,
        "successful_sends": successful_sends,
        "failed_sends": failed_sends
    }), 201


@invite_bp.route("/invite/validate", methods=["POST"])
@jwt_required
def validate_invite():
    data = request.get_json()
    raw_token = data.get("token")

    invite = Invite.query.filter_by(raw_token_id=raw_token[:8]).first()

    if not invite:
        return jsonify({"error": "Invalid invite"}), 400

    # Validate hash
    computed_hash = hashlib.sha256((invite.salt + raw_token).encode()).hexdigest()

    if computed_hash != invite.token_hash:
        return jsonify({"error": "Invalid token"}), 400

    if datetime.utcnow() > invite.expires_at:
        return jsonify({"error": "Invite expired"}), 400

    return jsonify({
        "message": "Valid invite",
        "email": invite.email,
        "company_id": invite.company_id
    }), 200


@invite_bp.route("/invite/register", methods=["POST"])
def register_from_invite():
    data = request.get_json()
    raw_token = data.get("token")
    name = data.get("name")
    password = data.get("password")

    invite = Invite.query.filter_by(raw_token_id=raw_token[:8]).first()

    # (Repeat validation logic...)

    # Create user
    user = User(
        user_name=name,
        user_email=invite.email,
        company_id=invite.company_id,
        user_password=bcrypt.generate_password_hash(password).decode("utf-8"),
    )
    db.session.add(user)

    # Mark invite used
    invite.single_use = False
    db.session.commit()

    return jsonify({"message": "Account created successfully"}), 201


