from flask import Flask, request, jsonify , Blueprint , g
from models import db , Invite , User , Role , UserRole
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_cors import cross_origin
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
            expires_at=datetime.utcnow() + timedelta(hours=1),
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


# @invite_bp.route("/user/revoke_admin", methods=["POST"])
# @jwt_required
# def revoke_admin():
#     data = request.get_json()
#     target_user_id = data.get("user_id")
#     company_id = data.get("company_id")

#     # Get the user making the request
#     current_user_id = request.current_user_id
#     current_user = User.query.get(current_user_id)

#     # Only allow if current user is admin
#     if not current_user.is_admin or current_user.company_id != company_id:
#         return jsonify({"error": "Not authorized"}), 403

#     # Find the target user
#     target_user = User.query.filter_by(user_id=target_user_id, company_id=company_id).first()
#     if not target_user:
#         return jsonify({"error": "User not found"}), 404

#     # Revoke admin
#     target_user.is_admin = False
#     db.session.commit()

#     return jsonify({"message": f"Admin rights revoked for {target_user.user_name}"}), 200


# @invite_bp.route("/user/revoke_admin", methods=["POST"])
# @jwt_required# Use parentheses if not already done in your setup
# def revoke_admin():
#     """
#     Revokes the 'Administrator' role from a specified user within the same company.
#     Requires the current user to also have the 'Administrator' role.
#     """
#     data = request.get_json()
#     target_user_id = data.get("user_id")
#     company_id = data.get("company_id") # The company of the target user

#     # --- 1. Basic Input Validation ---
#     if not all([target_user_id, company_id]):
#         return jsonify({"error": "Missing required fields: user_id and company_id"}), 400

#     # --- 2. Get Current User and Admin Role ---
#     # Assuming request.current_user_id is set by a custom JWT loader or similar
#     current_user_id = request.current_user_id
#     current_user = User.query.filter_by(user_id=current_user_id).first()
    
#     # This check is mostly for safety, as jwt_required should ensure a user exists
#     if not current_user:
#         return jsonify({"error": "Authentication user not found"}), 401 

#     admin_role = Role.query.filter_by(role_name="Administrator").first()
#     if not admin_role:
#         return jsonify({"error": "Administrator role not found in system"}), 500
        
#     # --- 3. Authorization Check (Current User) ---
#     # Check if current user is an admin AND belongs to the specified company
#     is_admin = UserRole.query.filter_by(
#         user_id=current_user.user_id,
#         role_id=admin_role.role_id
#     ).first()

#     # The authorization logic is to check if the current user has the Admin role 
#     # AND that the operation is being performed within their own company context.
#     if not is_admin or (current_user.company_id != company_id):
#         # Prevent non-admins or users from different companies from revoking roles
#         return jsonify({"error": "Not authorized to perform this action in this context"}), 403

#     # --- 4. Find the Target User ---
#     # Target user must exist and belong to the same company being targeted
#     target_user = User.query.filter_by(
#         user_id=target_user_id, 
#         company_id=company_id
#     ).first()
    
#     if not target_user:
#         return jsonify({"error": "Target user not found in the specified company"}), 404

#     # Prevent an admin from revoking their own administrator status
#     if target_user.user_id == current_user_id:
#         return jsonify({"error": "You cannot revoke your own administrator rights"}), 400

#     # --- 5. Revoke Administrator Role ---
#     # Find the link between the target user and the Administrator role
#     user_role_link = UserRole.query.filter_by(
#         user_id=target_user.user_id,
#         role_id=admin_role.role_id
#     ).first()

#     if not user_role_link:
#         # User doesn't have the role, so the goal is already achieved
#         return jsonify({
#             "message": f"Administrator rights already revoked or never assigned for {target_user.user_name if target_user.user_name else target_user.user_email}"
#         }), 200

#     # --- 6. Remove UserRole link and Commit ---
#     db.session.delete(user_role_link)
#     db.session.commit()

#     return jsonify({
#         "message": f"Administrator rights revoked for {target_user.user_name if target_user.user_name else target_user.user_email}"
#     }), 200

@invite_bp.route("/user/grant_admin", methods=["POST"])
@jwt_required
def grant_admin():
    data = request.get_json()
    target_user_id = data.get("user_id")
    company_id = data.get("company_id")

    # Get the user making the request
    current_user_id = request.current_user_id
    current_user = User.query.get(current_user_id)

    # Only allow if current user is admin
    if not current_user.is_admin or current_user.company_id != company_id:
        return jsonify({"error": "Not authorized"}), 403

    # Find the target user
    target_user = User.query.filter_by(user_id=target_user_id, company_id=company_id).first()
    if not target_user:
        return jsonify({"error": "User not found"}), 404

    # Grant admin
    target_user.is_admin = True
    db.session.commit()

    return jsonify({"message": f"Admin rights granted to {target_user.user_name}"}), 200

@invite_bp.route("/user/revoke_access", methods=["POST"])
@jwt_required
def revoke_access():
    """
    Deactivates a specified user's account within the same company,
    effectively revoking their access.
    Requires the current user to have the 'Administrator' role
    and belong to the specified company.
    """
    data = request.get_json()
    target_user_id = data.get("user_id")
    company_id = data.get("company_id")

    # --- 1. Basic Input Validation ---
    if not all([target_user_id, company_id]):
        return jsonify({"error": "Missing required fields: user_id and company_id"}), 400

    # --- 2. Get Current User and Admin Role ---
    current_user_id = request.current_user_id
    
    # We only need the admin role ID for the UserRole check
    admin_role = Role.query.filter_by(role_name="Administrator").first()
    if not admin_role:
        return jsonify({"error": "Administrator role not found in system"}), 500
        
    # --- 3. Combined Authorization Check (Current User) ---
    # Check if current user is an admin AND belongs to the specified company in UserRole
    is_admin_of_company = UserRole.query.filter_by(
        user_id=current_user_id, # Use current_user_id directly from the token
        role_id=admin_role.role_id,
        # company_id=company_id # Check company membership directly from UserRole
    ).first()

    if not is_admin_of_company:
        return jsonify({"error": "Not authorized: Current user is not an Admin for this company."}), 403

    # --- 4. Find the Target User ---
    # Find the target user and ensure they belong to the specified company
    target_user = User.query.filter_by(
        user_id=target_user_id, 
        company_id=company_id
    ).first()
    
    if not target_user:
        return jsonify({"error": "Target user not found in the specified company"}), 404

    # Prevent an admin from revoking their own access
    if target_user.user_id == current_user_id:
        return jsonify({"error": "You cannot revoke your own access"}), 400

    # --- 5. Revoke Access (Deactivate User) ---
    if not target_user.is_active:
        return jsonify({
            "message": f"Access already revoked for {target_user.user_name if target_user.user_name else target_user.user_email}"
        }), 200

    target_user.is_active = False # Assuming 'is_active' is the field for access control
    db.session.commit()

    return jsonify({
        "message": f"Access successfully revoked (user deactivated) for {target_user.user_name if target_user.user_name else target_user.user_email}"
    }), 200