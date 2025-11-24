import requests
from flask import Flask, request, session, redirect, url_for, abort,jsonify
# from . import REFRESH_TOKEN_SECRET, decode_jwt_custom, generate_uuid, logging
import os
import json
from dotenv import load_dotenv
import secrets
from models import User , db , Pinterest 
import base64
from datetime import datetime, timedelta
from flask import Blueprint
import logging 
from flask_login import current_user
import uuid
from flask_jwt_extended import jwt_required, get_jwt_identity , decode_jwt_custom , generate_jwt_custom

def generate_uuid():
    return str(uuid.uuid4())

load_dotenv()


pinterest_bp = Blueprint('pinterest', __name__)

logger = logging.getLogger(__name__)

TOKEN_URL = os.getenv("TOKEN_URI")
PINTEREST_CLIENT_ID = os.getenv("CLIENT_ID")
PINTEREST_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
PINTEREST_REDIRECT_URI = os.getenv("REDIRECT_URI")
REFRESH_TOKEN_SECRET = os.getenv("REFRESH_TOKEN_SECRET")

@pinterest_bp.route('/pinterest_login', methods=['POST'])
def handle_pinterest_token_exchange():
    """
    Simulates the exchange of an Authorization Code for Pinterest Access/Refresh Tokens
    and stores them in the User model.
    """
    data = request.json
    user_id = data.get('user_id')
    
    # ⚠️ These tokens would typically come from a Pinterest OAuth server exchange,
    # along with the expiration time. This is simulated for demonstration.
    pinterest_access_token = data.get('pinterest_access_token')
    pinterest_refresh_token = data.get('pinterest_refresh_token')
    
    # Pinterest access tokens often expire after a short time (e.g., 24 hours).
    # Refresh tokens typically last longer (e.g., 1 year).
    ACCESS_EXPIRY_PINTEREST = timedelta(hours=24) 
    
    if not all([user_id, pinterest_access_token, pinterest_refresh_token]):
        return jsonify({"message": "Missing required Pinterest token data."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found."}), 404

    try:
        # Store Pinterest tokens and their expiry in the User model
        user.pinterest_access_token = pinterest_access_token
        user.pinterest_refresh_token = pinterest_refresh_token
        user.pinterest_token_expires_at = datetime.utcnow() + ACCESS_EXPIRY_PINTEREST
        
        # NOTE: You should also add a field to the User model to track 
        # when the Pinterest refresh token itself expires, if provided by Pinterest.

        db.session.commit()
        
        return jsonify({
            "message": "Pinterest tokens successfully stored.",
            "pinterest_access_token_expiry": user.pinterest_token_expires_at.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error storing Pinterest tokens: {e}")
        return jsonify({"error": str(e)}), 500

def refresh_pinterest_token(user_id):
    """
    Simulates sending the Pinterest Refresh Token to the Pinterest API 
    to get a new Access Token.
    """
    user = User.query.get(user_id)
    if not user or not user.pinterest_refresh_token:
        return None # User has no Pinterest session
        
    # ⚠️ In a real app, this would involve an HTTP request to Pinterest's token endpoint.
    # The new tokens and expiry would be returned and updated in the database.
    
    try:
        # SIMULATION:
        new_access_token = "new_pinterest_access_token_" + str(uuid.uuid4())
        new_expiry = datetime.utcnow() + timedelta(hours=24)
        
        user.pinterest_access_token = new_access_token
        user.pinterest_token_expires_at = new_expiry
        db.session.commit()
        
        return new_access_token
        
    except Exception as e:
        logger.error(f"Failed to refresh Pinterest token for user {user_id}: {e}")
        db.session.rollback()
        return None
    

@pinterest_bp.route('/pinterest/callback', methods=['GET'])
def pinterest_oauth_callback():
    # 1. Get the Authorization Code and User ID
    auth_code = request.args.get('code')
    user_id = session.get('user_id') 

    if not auth_code or not user_id:
        # Note: 'error_page' must be a defined route/function
        return redirect(url_for('error_page'))

    # Check for critical configuration variables
    if not PINTEREST_CLIENT_ID or not PINTEREST_CLIENT_SECRET:
        print("Error: Pinterest client credentials not loaded from environment.")
        return redirect(url_for('error_page'))

    # 2. Exchange the Code for Tokens
    token_url = TOKEN_URL
    
    # --- CORRECTLY CONSTRUCTING THE AUTHORIZATION HEADER ---
    auth_string = f"{PINTEREST_CLIENT_ID}:{PINTEREST_CLIENT_SECRET}".encode('utf-8')
    encoded_auth = base64.b64encode(auth_string).decode('utf-8')
    
    headers = {
        # This is the required Basic Authentication format: 'Basic <base64(client_id:client_secret)>'
        "Authorization": f"Basic {encoded_auth}", 
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = { # This is the request payload
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": PINTEREST_REDIRECT_URI, # Use the global config variable
    }

    token_response = requests.post(token_url, headers=headers, data=data)

    # CHECK FOR SUCCESS AND GET THE RESPONSE DATA
    if token_response.status_code != 200:
        print(f"Token exchange failed (HTTP {token_response.status_code}): {token_response.text}")
        return redirect(url_for('error_page'))
    
    # Store the successful JSON response
    token_data = token_response.json()

    try:
        # Extract token details using .get() for safety where applicable
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token') # Refresh token may be optional/missing if not requested
        expires_in_seconds = token_data.get('expires_in', 0) # Use 0 as default if missing
        scopes = token_data.get('scope', '') 
        token_type = token_data.get('token_type')

        # Check for mandatory keys
        if not access_token or not token_type:
             raise ValueError("Required token data (access_token or token_type) missing in response.")

        # 3. Calculate the Actual Expiration Datetime
        expiration_datetime = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

        # 4. Save to Database 
        # (Assuming 'Pinterest' model and 'db' are available in this scope)
        pinterest_record = Pinterest.query.filter_by(user_id=user_id).first()

        if pinterest_record:
            # Update existing record
            pinterest_record.access_token = access_token
            pinterest_record.refresh_token = refresh_token
            pinterest_record.expires_in = expiration_datetime
            pinterest_record.scopes = scopes
            pinterest_record.token_type = token_type
        else:
            # Create new record
            new_pinterest_record = Pinterest(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expiration_datetime,
                scopes=scopes,
                token_type=token_type
            )
            db.session.add(new_pinterest_record)

        db.session.commit()

        # 5. Finish
        # Note: 'success_page' must be a defined route/function
        return redirect(url_for('success_page'))

    except Exception as e:
        # Handle API or DB errors
        print(f"Error during Pinterest callback processing: {e}")
        # Only rollback if db.session is available/in use
        if 'db' in globals() or 'db' in locals():
            db.session.rollback() 
        return redirect(url_for('error_page'))


@pinterest_bp.route("/save-pinterest-tokens", methods=["POST"])
def save_pinterest_tokens():
    data = request.get_json()
    
    user_id = data.get("user_id")
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = data.get("expires_in")

    token_entry = Pinterest(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )

    db.session.add(token_entry)
    db.session.commit()

    return jsonify({"message": "Tokens saved successfully"}), 201

import requests
from datetime import datetime, timedelta
import os

# Assume your models.py defines PinterestTokens and db correctly
# from models import PinterestTokens, db 

# Define the Pinterest token endpoint
PINTEREST_TOKEN_URL = TOKEN_URL
CLIENT_ID = os.getenv("PINTEREST_CLIENT_ID")
CLIENT_SECRET = os.getenv("PINTEREST_CLIENT_SECRET")

# --- NEW FUNCTION TO REFRESH TOKEN PROGRAMMATICALLY ---
def refresh_pinterest_token(token_entry: Pinterest):
    """
    Exchanges an expired refresh token for a new access token and refresh token pair.
    Updates the PinterestTokens entry in the database.
    """
    try:
        # 1. Prepare the request data
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": token_entry.refresh_token,
            "scope": "ads:read,pins:read,boards:read" # Use the scopes granted during initial login
        }
        
        # 2. Set Basic Auth headers
        auth = (CLIENT_ID, CLIENT_SECRET)
        
        # 3. Make the API call to Pinterest
        response = requests.post(PINTEREST_TOKEN_URL, data=payload, auth=auth)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        new_tokens = response.json()

        # 4. Update the database entry with the new tokens and expiration time
        token_entry.access_token = new_tokens["access_token"]
        token_entry.refresh_token = new_tokens["refresh_token"]
        token_entry.expires_in = new_tokens["expires_in"]
        # Optional: Calculate and save the absolute expiry time for easier checks
        # token_entry.expiry_time = datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"]) 
        
        db.session.commit()
        return True, token_entry.access_token

    except requests.exceptions.RequestException as e:
        print(f"Pinterest Token Refresh Failed: {e}")
        db.session.rollback()
        # In a real app, you might flag the user's token as invalid and require re-auth
        return False, None
    except Exception as e:
        print(f"Unexpected error during token refresh: {e}")
        db.session.rollback()
        return False, None

# --- Example of how to use it in a protected route (e.g., getting user info) ---

@pinterest_bp.route("/pinterest/me", methods=["GET"])
def get_pinterest_user_info():
    # 1. Retrieve the user's token record (e.g., based on the authenticated user's ID)
    user_id = request.args.get("user_id") # Replace with actual authentication logic
    token_entry = Pinterest.query.filter_by(user_id=user_id).first()

    if not token_entry:
        return jsonify({"message": "User not linked to Pinterest"}), 404
        
    # **2. Token Check and Refresh Logic (Simplified Check)**
    # A real check would use a saved expiry time (expiry_time) to be accurate.
    # Here, we just assume we need to refresh (for demonstration purposes).
    
    # In production, check if the token is near expiration (e.g., within 5 minutes) 
    # OR if an API call fails with a 401 Unauthorized error.
    
    access_token = token_entry.access_token

    # We will simulate a refresh attempt here:
    # Check if the token is old (or use an explicit expiry time check)
    if True: # Replace with check: if token_entry.is_expired():
        success, new_token = refresh_pinterest_token(token_entry)
        if not success:
            return jsonify({"message": "Token refresh failed. Please re-authenticate."}), 401
        access_token = new_token
        
    # 3. Use the valid access token for the actual Pinterest API call
    headers = {"Authorization": f"Bearer {access_token}"}
    pinterest_api_url = TOKEN_URL
    
    try:
        api_response = requests.get(pinterest_api_url, headers=headers)
        api_response.raise_for_status()
        return jsonify(api_response.json()), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"message": f"Pinterest API error: {e}"}), 500
    

#=====================ACCESS TOKEN======================
@pinterest_bp.route("/pinterest/auth", methods=["POST"])
def pinterest_auth():
    data = request.json
    code = data.get("code")

    if not code:
        return jsonify({"error": "Code not provided"}), 400

    token_url = TOKEN_URL

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": PINTEREST_REDIRECT_URI,
        "client_id": PINTEREST_CLIENT_ID,
        "client_secret": PINTEREST_CLIENT_SECRET,
    }

    response = requests.post(token_url, json=payload)
    tokens = response.json()

    if "access_token" not in tokens:
        return jsonify({"error": "Failed to exchange code"}), 400

    # Store into database
    new_token = Pinterest(
        user_id=current_user.id,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token")
    )
    db.session.add(new_token)
    db.session.commit()

    return jsonify({"message": "Tokens stored successfully"}), 200


@pinterest_bp.route("/pinterest/refresh", methods=["POST"])
def refresh_pinterest_token():
    token_obj = Pinterest.query.filter_by(user_id=current_user.id).first()

    refresh_url = TOKEN_URL

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token_obj.refresh_token,
        "client_id": PINTEREST_CLIENT_ID,
        "client_secret": PINTEREST_CLIENT_SECRET,
    }

    response = requests.post(refresh_url, json=payload)
    data = response.json()

    token_obj.access_token = data["access_token"]
    db.session.commit()
    
    return jsonify({"message": "Token refreshed"}), 200


