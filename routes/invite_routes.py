from flask import Flask, request, jsonify , Blueprint , g , current_app
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
    # company_id = data.get("company_id")
    
    # Get user_id from the request object, which was set by the decorator
    created_by_user_id = request.current_user_id 
    current_user = User.query.get(created_by_user_id)
    if not current_user:
        return jsonify({"error": "Authenticated user not found"}), 401
    
    company_id = current_user.company_id
    if not company_id:
        return jsonify({"error": "User does not belong to any company"}), 400
    
    if not emails or not isinstance(emails, list):
        return jsonify({"error": "A list of emails is required"}), 400

    invite_links = []
    successful_sends = []
    failed_sends = []
    already_registered = []

    expiry_time = datetime.utcnow() + timedelta(hours=72)

    for email in emails:
        # Assuming you have access to the User model here.
        existing_user = User.query.filter_by(user_email=email, company_id=company_id).first()
        if existing_user:
            already_registered.append(email)
            logging.warning(f"Invite skipped: {email} is already a user in company {company_id}.")
            continue

        active_invite = Invite.query.filter_by(
            email=email, 
            company_id=company_id, 
            single_use=True
        ).filter(Invite.expires_at > datetime.utcnow()).first()

        if active_invite:
             # Just resend the existing invite link if it's still valid
            raw_token = active_invite.raw_token_id # Fetch token ID to reconstruct link
            token_hash = active_invite.token_hash
            salt = active_invite.salt
            invite_link = f"http://localhost:5173/invite/accept?token={raw_token}"
            logging.info(f"Using existing active invite for {email}")

            invite = active_invite  # Reuse existing invite

        else:
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
            expires_at=expiry_time,
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
            successful_sends.append({
                "email": email,
                "invite_link": invite_link,
                "company_id": company_id
            })
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
    if already_registered:
        response_message += f" Skipped {len(already_registered)} emails (users already registered)."

    return jsonify({
        "message": response_message, 
        "invite_links": [s['invite_link'] for s in successful_sends],
        "successful_sends": successful_sends,
        "failed_sends": failed_sends,
        "already_registered": already_registered
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
        "company_id": invite.company_id,
        "created_by_user_id": invite.created_by_user_id
    }), 200


@invite_bp.route("/invite/register", methods=["POST"])
def register_from_invite():
    data = request.get_json()
    raw_token = data.get("token")
    name = data.get("name")
    password = data.get("password")

    if not all([raw_token, name, password]):
        return jsonify({"error": "Missing required fields: token, name, and password"}), 400

    invite = Invite.query.filter_by(raw_token_id=raw_token[:8]).first()

    if not invite:
        return jsonify({"error": "Invalid invite or token prefix"}), 400
    
    computed_hash = hashlib.sha256((invite.salt + raw_token).encode()).hexdigest()

    if computed_hash != invite.token_hash:
        return jsonify({"error": "Invalid token signature"}), 400

    if datetime.utcnow() > invite.expires_at:
        return jsonify({"error": "Invite expired"}), 400
    
    if not invite.single_use:
         return jsonify({"error": "Invite has already been used"}), 400
    # --- End Validation Logic ---

    # Check for existing user with the same email in the company (Safety check)
    existing_user = User.query.filter_by(user_email=invite.email, company_id=invite.company_id).first()
    if existing_user:
        # Mark invite as accepted/used even if a user somehow got created outside the flow
        invite.single_use = False
        invite.accepted = True
        invite.accepted_by_user_id = user.user_id
        invite.accepted_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"message": "Account already exists and invite marked as used."}), 409

    # (Repeat validation logic...)

    # Create user
    user = User(
        user_name=name,
        user_email=invite.email,
        company_id=invite.company_id,
        user_password=bcrypt.generate_password_hash(password).decode("utf-8"),
        is_active=True
    )
    db.session.add(user)
    db.session.flush()

    # Mark invite used
    invite.single_use = False
    invite.accepted =   True
    invite.accepted_by_user_id = user.user_id
    invite.accepted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Account created successfully",
                    "user_id": user.user_id,
                    "company_id": user.company_id,
                    "created_by_user_id": invite.created_by_user_id, # User who originally sent the invite
                    "accepted_by_user_id": user.user_id # The new user's ID
                    }), 201


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

    current_user = User.query.get(request.current_user_id)
    if not current_user or current_user.company_id != company_id or not is_admin_of_company:
        return jsonify({"error": "Not authorized: Current user is not an Admin of the specified company."}), 403

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


# @invite_bp.route("/invite/send_with_role", methods=["POST"])
# @jwt_required
# def send_invite_with_role():
#     data = request.get_json()
#     emails = data.get("emails")
#     selected_role_name = data.get("role_name")  # NEW FIELD
    
#     created_by_user_id = request.current_user_id
#     current_user = User.query.get(created_by_user_id)

#     if not current_user:
#         return jsonify({"error": "Authenticated user not found"}), 401

#     company_id = current_user.company_id
#     if not company_id:
#         return jsonify({"error": "User does not belong to any company"}), 400

#     if not emails or not isinstance(emails, list):
#         return jsonify({"error": "A list of emails is required"}), 400

#     if not selected_role_name:
#         return jsonify({"error": "Role name is required"}), 400

#     # Validate role
#     role = Role.query.filter_by(role_name=selected_role_name).first()
#     if not role:
#         return jsonify({"error": f"Role '{selected_role_name}' does not exist"}), 400

#     invite_links = []
#     successful_sends = []
#     failed_sends = []
#     already_registered = []

#     expiry_time = datetime.utcnow() + timedelta(hours=72)

#     for email in emails:

#         existing_user = User.query.filter_by(user_email=email, company_id=company_id).first()
#         if existing_user:
#             already_registered.append(email)
#             continue

#         raw_token = secrets.token_urlsafe(16)
#         salt = secrets.token_hex(16)
#         token_hash = hashlib.sha256((salt + raw_token).encode()).hexdigest()

#         invite_link = f"http://localhost:5173/invite/accept?token={raw_token}"

#         invite = Invite(
#             email=email,
#             company_id=company_id,
#             created_by_user_id=created_by_user_id,
#             raw_token_id=raw_token[:8],
#             token_hash=token_hash,
#             salt=salt,
#             role_id=role.role_id,     # <—— Save selected role
#             expires_at=expiry_time,
#             single_use=True
#         )

#         db.session.add(invite)

#         # send email
#         try:
#             subject = "You've been invited!"
#             body = f"You were invited as '{selected_role_name}'. Click link:\n{invite_link}"

#             send_email(
#                 recipients=[email],
#                 subject=subject,
#                 body=body
#             )
#             successful_sends.append({"email": email, "invite_link": invite_link})
#         except:
#             failed_sends.append(email)

#     db.session.commit()

#     return jsonify({
#         "message": "Invites processed.",
#         "successful_sends": successful_sends,
#         "failed_sends": failed_sends,
#         "already_registered": already_registered
#     }), 201

@invite_bp.route("/invite/send_with_role", methods=["POST"])
@jwt_required
# Assuming jwt_required, User, Role, Invite, db, send_email are available globally or imported
def send_invite_with_role():
    """
    Sends invitations to a list of emails with a specified user role.
    """
    data = request.get_json()
    emails = data.get("emails")
    selected_role_name = data.get("role_name")  # NEW FIELD
    
    # 1. Authentication and User/Company Retrieval
    # created_by_user_id = request.current_user_id # Assuming this is set by jwt_required
    
    # --- START DUMMY PLACEHOLDER FOR TESTING ---
    # NOTE: Replace with actual authentication logic in a real application
    # For demonstration, we'll assume a fixed user/company setup if auth is bypassed
    try:
        created_by_user_id = request.current_user_id
        print(f"Authenticated user ID: {created_by_user_id}")
    except AttributeError:
        # Fallback for testing if jwt_required isn't fully set up in a context
        return jsonify({"error": "Authentication token required"}), 401 
    # --- END DUMMY PLACEHOLDER FOR TESTING ---
    
    current_user = User.query.get(created_by_user_id)

    if not current_user:
        return jsonify({"error": "Authenticated user not found"}), 401

    company_id = current_user.company_id
    if not company_id:
        return jsonify({"error": "User does not belong to any company"}), 400

    # 2. Input Validation
    if not emails or not isinstance(emails, list):
        return jsonify({"error": "A list of emails is required"}), 400

    if not selected_role_name:
        return jsonify({"error": "Role name is required"}), 400

    # 3. Role Validation and Retrieval
    # THIS SECTION CORRECTLY RETRIEVES THE ROLE OBJECT
    role = Role.query.filter_by(role_name=selected_role_name).first()
    if not role:
        return jsonify({"error": f"Role '{selected_role_name}' does not exist"}), 400
    

    try:
        # Get FRONTEND_BASE_URL from the Flask config
        base_url = current_app.config.get("FRONTEND_BASE_URL")
        if not base_url:
             raise KeyError("FRONTEND_BASE_URL not configured")
    except (RuntimeError, KeyError) as e:
        # Fallback if current_app isn't available or key is missing
        # NOTE: Using environment variables is the standard fallback for non-app contexts
        import os
        base_url = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173")
        if str(e) == "FRONTEND_BASE_URL not configured":
             print(f"WARNING: FRONTEND_BASE_URL not in config, falling back to {base_url}")
        
    # Standard cleanup for base_url (remove trailing slash if present)
    base_url = base_url.rstrip("/")

    invite_links = []
    successful_sends = []
    failed_sends = []
    already_registered = []

    expiry_time = datetime.utcnow() + timedelta(hours=72)
    invites_to_commit = [] # List to hold Invite objects before final commit

    for email in emails:
        email = email.strip().lower() # Basic sanitization

        # Check if user already exists in this company
        existing_user = User.query.filter_by(user_email=email, company_id=company_id).first()
        if existing_user:
            already_registered.append(email)
            continue

        # Generate unique token, salt, and hash
        raw_token = secrets.token_urlsafe(16)
        salt = secrets.token_hex(16)
        token_hash = hashlib.sha256((salt + raw_token).encode()).hexdigest()

        invite_link = f"{base_url}/invite/accept?token={raw_token}"

        # 4. Create Invite Object
        # THIS IS WHERE role.role_id IS CORRECTLY ASSIGNED
        invite = Invite(
            email=email,
            company_id=company_id,
            created_by_user_id=created_by_user_id,
            raw_token_id=raw_token[:8],
            token_hash=token_hash,
            salt=salt,
            role_id=role.role_id,       # <—— Correctly saves the Role ID
            expires_at=expiry_time,
            single_use=True
        )

        invites_to_commit.append(invite)

        # 5. Send Email
        try:
            subject = "You've been invited!"
            body = f"You were invited as '{selected_role_name}'. Click link:\n{invite_link}"

            # Ensure send_email is properly implemented to handle SMTP errors
            send_email(
                recipients=[email],
                subject=subject,
                body=body
            )
            successful_sends.append({"email": email, "invite_link": invite_link})
        except Exception as e:
            # Catch specific email errors if possible, otherwise general Exception
            failed_sends.append(email)
            # Log the error (optional)
            # print(f"Failed to send email to {email}: {e}")
            
    # Add all successfully created invites to the session (moved outside the loop for one block of work)
    for invite in invites_to_commit:
        # Only commit invites whose emails were attempted to be sent
        if invite.email in [s['email'] for s in successful_sends]:
             db.session.add(invite)
        # OPTION: You might choose to add ALL invites and then manually mark those that failed email as 'pending' or 'failed_send' status if your model supported it.
        # For simplicity, we only commit those that *successfully* sent an email.
        
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Log the database error
        return jsonify({"error": "An internal database error occurred while saving invites."}), 500


    # 6. Final Response
    return jsonify({
        "message": "Invites processed.",
        "successful_sends": successful_sends,
        "failed_sends": failed_sends,
        "already_registered": already_registered
    }), 201


@invite_bp.route("/invite/validate_with_role", methods=["POST"])
# @jwt_required
def validate_invite_with_role():
    data = request.get_json()
    raw_token = data.get("token")

    invite = Invite.query.filter_by(raw_token_id=raw_token[:8]).first()
    if not invite:
        return jsonify({"error": "Invalid invite"}), 400

    computed_hash = hashlib.sha256((invite.salt + raw_token).encode()).hexdigest()
    if computed_hash != invite.token_hash:
        return jsonify({"error": "Invalid token"}), 400

    if datetime.utcnow() > invite.expires_at:
        return jsonify({"error": "Invite expired"}), 400

    role = Role.query.get(invite.role_id)

    return jsonify({
        "message": "Valid invite",
        "email": invite.email,
        "company_id": invite.company_id,
        "role_name": role.role_name if role else None
    }), 200


@invite_bp.route("/invite/register_with_role", methods=["POST"])
# @jwt_required
def register_from_invite_with_role():
    data = request.get_json()
    raw_token = data.get("token")
    name = data.get("name")
    password = data.get("password")

    invite = Invite.query.filter_by(raw_token_id=raw_token[:8]).first()
    if not invite:
        return jsonify({"error": "Invalid invite"}), 400

    computed_hash = hashlib.sha256((invite.salt + raw_token).encode()).hexdigest()
    if computed_hash != invite.token_hash:
        return jsonify({"error": "Invalid token"}), 400
    
    existing_user = User.query.filter_by(user_email=invite.email).first()
    if existing_user:
        return jsonify({
            "error": "This email is already registered. Please login instead."
        }), 400


    if datetime.utcnow() > invite.expires_at:
        return jsonify({"error": "Invite expired"}), 400

    # Create user
    user = User(
        user_name=name,
        user_email=invite.email,
        company_id=invite.company_id,
        user_password=bcrypt.generate_password_hash(password).decode("utf-8"),
        is_active=True,
        role_id=invite.role_id,

    )
    db.session.add(user)
    db.session.flush()

    # Assign role from invite
    if invite.role_id:
        user_role = UserRole(
            user_id=user.user_id,
            role_id=invite.role_id
        )
        db.session.add(user_role)

    # Mark invite as used
    invite.single_use = False
    invite.accepted = True
    invite.accepted_at = datetime.utcnow()
    invite.accepted_by_user_id = user.user_id

    db.session.commit()

    role = Role.query.get(invite.role_id)

    return jsonify({
        "message": "Account created",
        "user_id": user.user_id,
        "role_assigned": role.role_name if role else None
    }), 201
