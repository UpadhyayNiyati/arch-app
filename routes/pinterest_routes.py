"""
pinterest_blueprint.py
Flask blueprint to handle Pinterest OAuth v5 token exchange, refresh, and a simple "me" endpoint.

Assumptions:
- You have Flask, Flask-Login, SQLAlchemy installed and configured.
- Environment variables set: PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET, PINTEREST_REDIRECT_URI
- models.py defines `db` and `Pinterest` model (see comment below for expected fields).
"""

import os
import uuid
import base64
import logging
from datetime import datetime, timedelta
import datetime
from flask import Flask
from models import User  # Assuming you have a User model
from urllib.parse import urlencode
from flask_login import LoginManager
from auth.authhelpers import get_user_from_auth_header , create_access_token , decode_jwt , verify_jwt
from auth.auth import jwt_required 
from flask_jwt_extended import get_jwt_identity
from flask_cors import CORS
import requests
import jwt
from flask import Blueprint, request, jsonify, redirect, url_for, session, current_app
from models import db, Pinterest
from flask_login import current_user, login_required
from flask import Blueprint, request, jsonify, redirect, url_for, session, current_app
from flask_jwt_extended import get_jwt_identity


app = Flask(__name__)




# CORS(app, supports_credentials=True, origins=["http://localhost:5173"])

logger = logging.getLogger(__name__)
pinterest_bp = Blueprint("pinterest", __name__)
CORS(pinterest_bp, supports_credentials=True, origins=["http://localhost:5173"])

def generate_uuid():
    return str(uuid.uuid4())



PINTEREST_CLIENT_ID = os.getenv("PINTEREST_CLIENT_ID")
PINTEREST_CLIENT_SECRET = os.getenv("PINTEREST_CLIENT_SECRET")
# IMPORTANT: this must be the server callback that Pinterest will redirect to
PINTEREST_REDIRECT_URI = os.getenv("PINTEREST_REDIRECT_URI" , "http://localhost:5000/api/pinterest/callback")
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
AUTH_BASE = "https://www.pinterest.com/oauth/"

if not (PINTEREST_CLIENT_ID and PINTEREST_CLIENT_SECRET):
    logger.error("Missing Pinterest client id/secret in env")

def _now_utc():
    return datetime.utcnow()


# Helper: build auth header for Basic (client_id:client_secret)
def _basic_auth_header(client_id: str, client_secret: str) -> dict:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")
    return {"Authorization": f"Basic {encoded}"}
# login_manager = LoginManager()
# login_manager.init_app(app)



# ---------------------------
# 1) Start Pinterest OAuth
# ---------------------------
# @pinterest_bp.route("/pinterest/start", methods=["GET"])
# # @login_required
# def start_pinterest_login():
#     """
#     Initiate OAuth flow:
#     - Store state and the initiating user ID in session
#     - Redirect to Pinterest authorization URL
#     """
#     # Create and store state to validate on callback (CSRF protection)
#     state = str(uuid.uuid4())
#     session["pinterest_oauth_state"] = state
#     # Also store which app user started the flow
#     session["pinterest_oauth_state"] = state

#     params = {
#         "response_type": "code",
#         "client_id": PINTEREST_CLIENT_ID,
#         "redirect_uri": PINTEREST_REDIRECT_URI,
#         # NOTE: Only request the scopes you truly need
#         "scope": "ads:read,pins:read,boards:read,boards:write,pins:write,user_accounts:read,user_accounts:write",
#         "state": state,
#     }
#     auth_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"
    
#     return redirect(auth_url)

def generate_jwt(payload, expires_minutes=10):
    payload["exp"] = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes)
    secret = current_app.config["SECRET_KEY"]
    return jwt.encode(payload, secret, algorithm="HS256")

# def save_user_pinterest_token(user_id, token_data):
#     """
#     Saves/Updates Pinterest tokens for a given user_id in the database.
#     This logic should match your Pinterest model fields (access_token, refresh_token, etc.)
#     """
#     access_token = token_data.get("access_token")
#     refresh_token = token_data.get("refresh_token")
#     token_type = token_data.get("token_type")
#     expires_in = token_data.get("expires_in")
#     scopes = token_data.get("scope")

#     expires_at = None
#     if expires_in and isinstance(expires_in, (int, str)):
#         expires_in = datetime.datetime.utcnow() + timedelta(seconds=int(expires_in))
        
#     # Attempt to get Pinterest Account ID (optional, requires user_accounts:read scope)
#     pinterest_account_id = (token_data.get("user") or {}).get("id")

#     p = Pinterest.query.filter_by(user_id=user_id).first()
#     if p:
#         p.access_token = access_token
#         p.refresh_token = refresh_token or p.refresh_token # Only update if new one is provided
#         p.expires_in = expires_in
#         p.scopes = scopes
#         p.pinterest_account_id = pinterest_account_id
#     else:
#         p = Pinterest(
#             pinterest_id = generate_uuid()
#             user_id=user_id,
#             access_token=access_token,
#             refresh_token=refresh_token,
#             expires_in=expires_in,
#             token_type=token_type,
#             scopes=scopes,
#             pinterest_account_id=pinterest_account_id
#         )
#         db.session.add(p)

#     db.session.commit()

# def save_user_pinterest_token(user_id, company_id , token_data):
#     """
#     Saves or updates Pinterest tokens for a given user_id.
#     Fetches Pinterest Account ID + Username using the access token.
#     """

#     access_token = token_data.get("access_token")
#     refresh_token = token_data.get("refresh_token")
#     token_type = token_data.get("token_type")
#     scopes = token_data.get("scope")

#     # Convert expires_in seconds → datetime
#     expires_in = token_data.get("expires_in")
#     expires_at = None
#     if expires_in:
#         expires_at = datetime.datetime.utcnow() + timedelta(seconds=int(expires_in))

#     # ---------------------------------------
#     # 🔥 Fetch Pinterest user info
#     # ---------------------------------------
#     user_info = get_pinterest_user(access_token)

#     pinterest_account_id = user_info.get("pinterest_account_id")   # REQUIRED (NOT NULL)
#     pinterest_username = user_info.get("pinterest_username")       # optional

#     # ---------------------------------------
#     # 🔥 Fetch existing token row for this user
#     # ---------------------------------------
#     existing = Pinterest.query.filter_by(user_id=user_id).first()

#     if existing:
#         # Update existing token entry
#         existing.access_token = access_token
#         existing.refresh_token = refresh_token or existing.refresh_token
#         existing.token_type = token_type
#         existing.expires_in = expires_at
#         existing.scopes = scopes
#         existing.pinterest_account_id = pinterest_account_id
#         existing.pinterest_username = pinterest_username
#         existing.company_id = company_id

#     else:
#         # ---------------------------------------
#         # 🔥 Create new token entry
#         # ---------------------------------------
#         token_entry = Pinterest(
#             pinterest_id= generate_uuid(),
#             user_id=user_id,
#             company_id = company_id,
#             access_token=access_token,
#             refresh_token=refresh_token,
#             token_type=token_type,
#             expires_in=expires_at,
#             scopes=scopes,
#             pinterest_account_id=pinterest_account_id,   # NOT NULL
#             pinterest_username=pinterest_username
#         )
#         db.session.add(token_entry)

#     db.session.commit()

# def get_pinterest_user(access_token):
#     url = "https://api.pinterest.com/v5/user_account"
#     headers = {"Authorization": f"Bearer {access_token}"}
#     response = requests.get(url, headers=headers)

#     if response.status_code != 200:
#         raise Exception("Failed to fetch Pinterest user info")

#     data = response.json()

#     return {
#         "pinterest_account_id": data.get("id"),
#         "pinterest_username": data.get("username")
#     }

def get_pinterest_user(access_token):
    """
    Fetch authenticated Pinterest account details
    """
    url = "https://api.pinterest.com/v5/user_account"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()

    return {
        "pinterest_account_id": data["id"],          # REQUIRED (UNIQUE)
        "pinterest_username": data.get("username"), # Optional
    }


def save_user_pinterest_token(user_id, company_id, token_data):
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    token_type = token_data.get("token_type")
    scopes = token_data.get("scope")

    # Convert expires_in → datetime
    expires_at = None
    expires_in = token_data.get("expires_in")
    if expires_in:
        expires_at = datetime.datetime.utcnow() + timedelta(seconds=int(expires_in))

    # 🔥 Fetch Pinterest user info
    user_info = get_pinterest_user(access_token)
    pinterest_account_id = user_info["pinterest_account_id"]
    pinterest_username = user_info.get("pinterest_username")

    # 🔍 CRITICAL FIX:
    # Check by pinterest_account_id (UNIQUE)
    token_entry = Pinterest.query.filter_by(
        pinterest_account_id=pinterest_account_id
    ).first()

    if token_entry:
        # 🔄 UPDATE existing Pinterest account
        token_entry.user_id = user_id
        token_entry.company_id = company_id
        token_entry.access_token = access_token
        token_entry.refresh_token = refresh_token or token_entry.refresh_token
        token_entry.token_type = token_type
        token_entry.expires_in = expires_at
        token_entry.scopes = scopes
        token_entry.pinterest_username = pinterest_username
        token_entry.updated_at = datetime.datetime.utcnow()

    else:
        # ➕ INSERT new Pinterest account
        token_entry = Pinterest(
            pinterest_id=str(uuid.uuid4()),
            user_id=user_id,
            company_id=company_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_in=expires_at,
            scopes=scopes,
            pinterest_account_id=pinterest_account_id,
            pinterest_username=pinterest_username,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        db.session.add(token_entry)

    db.session.commit()


@pinterest_bp.route("/start", methods=["GET"])
@jwt_required
def start_pinterest_login():
    """Initiate Pinterest OAuth flow"""

    # 1. Get authenticated user_id from your jwt_required decorator
    user_id = request.current_user_id
    user = User.query.get(user_id)
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    company_id = user.company_id

    # 2. Create state token using your own JWT generator
    state_payload = {
        "pinterest_state": True,
        "user_id": user_id,
        "company_id": company_id
    }

    # MUST use generate_jwt, NOT jwt_required!
    state = generate_jwt(state_payload)
    if isinstance(state, bytes):
        state = state.decode("utf-8")

    # 3. Read config values
    PINTEREST_CLIENT_ID =  os.environ.get("PINTEREST_CLIENT_ID")
    PINTEREST_REDIRECT_URI = os.environ.get("PINTEREST_REDIRECT_URI")

    # 4. Build Pinterest OAuth URL correctly
    params = {
        "response_type": "code",
        "client_id": PINTEREST_CLIENT_ID,
        "redirect_uri": PINTEREST_REDIRECT_URI,
        "scope": "ads:read,pins:read,boards:read,boards:write,pins:write,user_accounts:read",
        "state": state
    }

    auth_url = "https://www.pinterest.com/oauth/?" + urlencode(params)

    # 5. Return to frontend
    return jsonify({"auth_url": auth_url}), 200

# @pinterest_bp.route("/start", methods=["GET"])
# @jwt_required
# def start_pinterest_login():
#     """Initiate Pinterest OAuth flow"""
#     user_id = request.current_user_id
#     if not user_id:
#         return jsonify({"error": "User not authenticated"}), 401

#     # Create state token with JWT (correct method)
#     state_payload = {

#         "pinterest_state": True,
#         "user_id": user_id
#     }

#     state = jwt_required(state_payload)

#     params = {
#         "response_type": "code",
#         "client_id": PINTEREST_CLIENT_ID,
#         "redirect_uri": PINTEREST_REDIRECT_URI,
#         "scope": "ads:read,pins:read,boards:read,boards:write,pins:write,user_accounts:read",
#         "state": state
#     }

#     # auth_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"

#     auth_url = f"https://www.pinterest.com/oauth/?state={state}&client_id={PINTEREST_CLIENT_ID}"
#     return jsonify({"auth_url": auth_url}), 200


# @pinterest_bp.route("/callback", methods=["GET"])
# def pinterest_callback():
#     code = request.args.get("code")
#     state = request.args.get("state")

#     if not code or not state:
#         return jsonify({"error": "Missing code or state"}), 400

#     # Decode state token
#     try:
#         decoded = decode_jwt(
#             state,
#             current_app.config["JWT_SECRET_KEY"]
#         )
#     except Exception as e:
#         return jsonify({"error": "Invalid state token", "details": str(e)}), 400

#     print("Decoded state:", decoded)

#     user_id = decoded.get("user_id")

#     if not user_id:
#         return jsonify({"error": "Invalid decoded state"}), 400

#     # Exchange code for Pinterest access token
#     payload = {
#         "grant_type": "authorization_code",
#         "code": code,
#         "redirect_uri": PINTEREST_REDIRECT_URI,
#         "client_id": PINTEREST_CLIENT_ID,
#         "client_secret": PINTEREST_CLIENT_SECRET,
#     }

#     r = requests.post(TOKEN_URL, json=payload, timeout=10)

#     if r.status_code != 200:
#         return jsonify({
#             "error": "Token exchange failed",
#             "details": r.text
#         }), 400

#     data = r.json()

#     # Save tokens
#     expires_at = None
#     if data.get("expires_in"):
#         expires_at = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))

#     pinterest_user_id = (data.get("user") or {}).get("id")

#     p = Pinterest.query.filter_by(user_id=user_id).first()
#     if p:
#         p.access_token = data.get("access_token")
#         p.refresh_token = data.get("refresh_token")
#         p.expires_at = expires_at
#         p.scopes = data.get("scope")
#         p.pinterest_account_id = pinterest_user_id
#     else:
#         p = Pinterest(
#             user_id=user_id,
#             access_token=data.get("access_token"),
#             refresh_token=data.get("refresh_token"),
#             expires_at=expires_at,
#             scopes=data.get("scope"),
#             pinterest_account_id=pinterest_user_id
#         )
#         db.session.add(p)

#     db.session.commit()

#     # Redirect back to frontend
#     return redirect("http://localhost:5173/")


# Assuming these variables/imports are defined globally or imported:
# PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET, PINTEREST_REDIRECT_URI, TOKEN_URL
# requests, verify_jwt, create_access_token, User, save_user_pinterest_token

@pinterest_bp.route("/callback", methods=["GET"])
def pinterest_callback():
    """Handle Pinterest OAuth callback and exchange code for tokens"""
    code = request.args.get("code")
    state = request.args.get("state")
    
    # 0. Initial checks
    if not code or not state:
        return jsonify({"error": "Missing authorization code or state"}), 400

    SECRET_KEY = current_app.config.get("SECRET_KEY") 
    if not SECRET_KEY:
        SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") 
    if not SECRET_KEY:
        return jsonify({"error": "Internal configuration error: Missing SECRET_KEY"}), 500
    
    # Check Pinterest config consistency (for debugging)
    if not all([PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET, PINTEREST_REDIRECT_URI]):
         logger.error("Missing required Pinterest environment variables.")
         return jsonify({"error": "Internal configuration error: Missing Pinterest credentials"}), 500

    # 1. Verify state token and define decoded_state
    try:
        decoded_state = verify_jwt(state, SECRET_KEY) 
    except Exception as e:
        logger.error(f"State token verification failed: {str(e)}")
        return jsonify({"error": "Invalid or expired state token"}), 400

    user_id = decoded_state.get("user_id")
    if not user_id:
        return jsonify({"error": "Invalid state: missing user_id"}), 400

    # Retrieve user and company_id
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User ID {user_id} not found in database.")
        return jsonify({"error": "Authentication error: User record missing."}), 404
        
    company_id = user.company_id 

    # 2. Token Exchange with Pinterest
    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        # 💡 IMPORTANT: This must EXACTLY match the URI registered with Pinterest.
        "redirect_uri": PINTEREST_REDIRECT_URI, 
    }
    
    try:
        # Use Basic Auth (Client ID and Secret)
        token_response = requests.post(
            TOKEN_URL, 
            data=token_payload,
            auth=(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET),
            timeout=10
        )
        token_response.raise_for_status() 
        token_data = token_response.json() 

    except requests.exceptions.HTTPError as http_exc:
        # Provide more specific error detail from Pinterest's response for better debugging
        pinterest_error = token_response.json().get("message", "Unknown Pinterest error")
        logger.error(f"Pinterest token exchange failed: {pinterest_error}. Status: {token_response.status_code}")
        return jsonify({
            "error": "Failed to get access token from Pinterest",
            "status_code": token_response.status_code,
            "details": pinterest_error,
            "troubleshoot": "Check if the code is expired or if PINTEREST_REDIRECT_URI is exact."
        }), 400
    except requests.RequestException as req_exc:
        logger.error(f"Request error during token exchange: {str(req_exc)}")
        return jsonify({"error": "Network or timeout error during token exchange"}), 500

    # 5. Save tokens and generate app JWT
    access_token = token_data.get("access_token")
    if not access_token:
        # Should be caught by raise_for_status(), but good defensive programming
        return jsonify({"error": "Access token missing in Pinterest response"}), 400
        
    try:
        app_jwt_token = create_access_token(user_id, company_id) 
        save_user_pinterest_token(user_id, company_id , token_data)
        
    except Exception as e:
        logger.exception("Failed to save token to database or create app token")
        return jsonify({"error": "Internal processing error", "details": str(e)}), 500

    # 6. Redirect user to your frontend success page
    frontend_redirect = f"http://localhost:5173/pinterest/success?connected=true&auth_token={app_jwt_token}"
    return redirect(frontend_redirect)


# @pinterest_bp.route("/callback", methods=["GET"])
# def pinterest_callback():
#     """Handle Pinterest OAuth callback and exchange code for tokens"""
#     code = request.args.get("code")
#     state = request.args.get("state")
    
#     if not code or not state:
#         return jsonify({"error": "Missing authorization code or state"}), 400

#     SECRET_KEY = current_app.config.get("SECRET_KEY") 
#     if not SECRET_KEY:
#         # Fallback check (adjust as needed for your app setup)
#         SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") 
    
#     if not SECRET_KEY:
#         return jsonify({"error": "Internal configuration error: Missing SECRET_KEY"}), 500

#     # Verify state token
#     try:
#         decoded_state = verify_jwt(state, SECRET_KEY) 
#     except Exception as e:
#         logger.error(f"State token verification failed: {str(e)}")
#         return jsonify({"error": "Invalid or expired state token"}), 400

#     user_id = decoded_state.get("user_id")
#     if not user_id:
#         return jsonify({"error": "Invalid state: missing user_id"}), 400

#     # Check for missing Pinterest credentials again
#     if not all([PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET, PINTEREST_REDIRECT_URI]):
#         return jsonify({"error": "Internal configuration error: Missing Pinterest credentials"}), 500

#     # 4. Exchange "code" for access token using Basic Auth (FIXED IMPLEMENTATION)
    
#     # Payload as application/x-www-form-urlencoded
#     token_payload = {
#         "grant_type": "authorization_code",
#         "code": code,
#         "redirect_uri": PINTEREST_REDIRECT_URI,
#     }
    
#     # Send request with HTTP Basic Auth and application/x-www-form-urlencoded data
#     try:
#         token_response = requests.post(
#             TOKEN_URL, 
#             data=token_payload,
#             auth=(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET),
#             timeout=10
#         )
#         token_response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
#         token_data = token_response.json()

#     except requests.exceptions.HTTPError as http_exc:
#         logger.error(f"Pinterest token exchange failed with status {token_response.status_code}. Response: {token_response.text}")
#         return jsonify({
#             "error": "Failed to get access token from Pinterest",
#             "status_code": token_response.status_code,
#             "response": token_response.text
#         }), 400
#     except requests.RequestException as req_exc:
#         logger.error(f"Request error during token exchange: {str(req_exc)}")
#         return jsonify({"error": "Network or timeout error during token exchange"}), 500

#     # 5. Save tokens
#     access_token = token_data.get("access_token")
#     if not access_token:
#         return jsonify({"error": "Access token missing in Pinterest response"}), 400
        
#     try:
#         app_jwt_token = create_access_token(identity={"user_id": user_id})
#         save_user_pinterest_token(user_id, token_data)
#     except Exception as e:
#         logger.exception("Failed to save token to database")
#         return jsonify({"error": "Failed to save token to database", "details": str(e)}), 500

#     # 6. Redirect user to your frontend success page
#     frontend_redirect = f"http://localhost:5173/pinterest/success?connected=true"
#     return redirect(frontend_redirect)



# @pinterest_bp.route("/callback", methods=["GET"])
# def pinterest_callback():
#     print("\n------ Pinterest Callback Hit ------")

#     code = request.args.get("code")
#     state = request.args.get("state")

#     print(f"Received code: {code}")
#     print(f"Received state: {state}")

#     if not code or not state:
#         print("❌ Missing code or state")
#         return "Missing code or state", 400

#     # Decode state
#     decoded = decode_jwt(state)
#     print(f"Decoded state: {decoded}")

#     if not decoded or not decoded.get("user_id"):
#         print("❌ Invalid state token")
#         return "Invalid state", 400

#     user_id = decoded.get("user_id")
#     print(f"User ID from state: {user_id}")

#     # Exchange code for tokens
#     payload = {
#         "grant_type": "authorization_code",
#         "code": code,
#         "redirect_uri": PINTEREST_REDIRECT_URI,
#         "client_id": PINTEREST_CLIENT_ID,
#         "client_secret": PINTEREST_CLIENT_SECRET
#     }

#     print("Sending token exchange request to Pinterest...")

#     r = requests.post(TOKEN_URL, json=payload, timeout=10)

#     if r.status_code != 200:
#         print("❌ Token exchange failed:")
#         print(f"Status: {r.status_code}")
#         print(f"Response: {r.text}")
#         return jsonify({"error": "token exchange failed", "details": r.text}), 400

#     data = r.json()

#     # Mask token for logs
#     access_token_preview = (data.get("access_token") or "")[:8] + "******"
#     refresh_token_preview = (data.get("refresh_token") or "")[:8] + "******"

#     print("✅ Token exchange successful!")
#     print(f"Access Token: {access_token_preview}")
#     print(f"Refresh Token: {refresh_token_preview}")
#     print(f"Expires in: {data.get('expires_in')}")
#     print(f"Pinterest User: {data.get('user')}")

#     # Save to DB
#     p = Pinterest.query.filter_by(user_id=user_id).first()
#     expires_at = None
#     if data.get("expires_in"):
#         expires_at = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))

#     if p:
#         print("Updating existing Pinterest token entry in DB...")
#         p.access_token = data.get("access_token")
#         p.refresh_token = data.get("refresh_token")
#         p.expires_at = expires_at
#         p.scopes = data.get("scope")
#         p.pinterest_account_id = (data.get("user") or {}).get("id")
#     else:
#         print("Creating new Pinterest token entry in DB...")
#         p = Pinterest(
#             user_id=user_id,
#             access_token=data.get("access_token"),
#             refresh_token=data.get("refresh_token"),
#             expires_at=expires_at,
#             scopes=data.get("scope"),
#             pinterest_account_id=(data.get("user") or {}).get("id")
#         )
#         db.session.add(p)

#     db.session.commit()
#     print("✅ Tokens saved in database successfully!")

#     # Redirect back to frontend
#     front_success = "http://localhost:5173/settings?connected=pinterest"

#     print(f"Redirecting user to frontend: {front_success}")
#     print("------ End callback ------\n")

#     return redirect(front_success)



# @pinterest_bp.route("/callback", methods=["POST"])
# @jwt_required
# def pinterest_callback():
#     """Handle OAuth callback from Pinterest"""
#     data = request.get_json()
#     if not data:
#         return jsonify({"error": "Invalid request body"}), 400
    
#     code = data.get("code")
#     state = data.get("state")
    
#     if not code:
#         return jsonify({"error": "Missing authorization code"}), 400
    
    
   
#     token_data = {
#         "grant_type": "authorization_code",
#         "code": code,
#         "redirect_uri": PINTEREST_REDIRECT_URI,
#     }
    
#     headers = _basic_auth_header(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET)
#     headers["Content-Type"] = "application/x-www-form-urlencoded"
    
#     try:
#         resp = requests.post(TOKEN_URL, headers=headers, data=token_data, timeout=10)
#         resp.raise_for_status()
#         token_response = resp.json()
#     except requests.RequestException as exc:
#         logger.exception("Token exchange failed")
#         return jsonify({"error": "Token exchange failed", "details": str(exc)}), 502
    
#     access_token = token_response.get("access_token")
#     refresh_token = token_response.get("refresh_token")
#     expires_in = token_response.get("expires_in", 3600)
    
#     if not access_token:
#         return jsonify({"error": "No access token received"}), 502
    
#     expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
    
#     try:
#         token_entry = Pinterest.query.filter_by(user_id=request.current_user_id).first()
        
#         if token_entry:
#             token_entry.access_token = access_token
#             token_entry.refresh_token = refresh_token
#             token_entry.expires_at = expires_at
#             token_entry.scopes = token_response.get("scope", "")
#             token_entry.token_type = token_response.get("token_type", "Bearer")
#         else:
#             token_entry = Pinterest(
#                 user_id=request.current_user_id,
#                 access_token=access_token,
#                 refresh_token=refresh_token,
#                 expires_at=expires_at,
#                 scopes=token_response.get("scope", ""),
#                 token_type=token_response.get("token_type", "Bearer")
#             )
#             db.session.add(token_entry)
        
#         db.session.commit()
        
#         session.pop("pinterest_oauth_state", None)
#         session.pop("pinterest_oauth_user_id", None)
        
#         return jsonify({
#             "success": True,
#             "message": "Pinterest account connected successfully"
#         }), 200
        
#     except Exception as exc:
#         db.session.rollback()
#         logger.exception("Failed to save tokens")
#         return jsonify({"error": "Database error", "details": str(exc)}), 500

# ---------------------------
# 3) Token refresh helper
# ---------------------------
def refresh_pinterest_token(token_entry):
    """
    Given a Pinterest model instance with a refresh_token, attempt to refresh.
    Returns (success: bool, new_access_token_or_none)
    """
    from models import db  # local import to avoid circulars

    if not getattr(token_entry, "refresh_token", None):
        logger.warning("No refresh token present for user %s", getattr(token_entry, "user_id", "<unknown>"))
        return False, None

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token_entry.refresh_token,
        # scope may be optional; include if you want:
        # "scope": token_entry.scopes or "ads:read,pins:read,boards:read",
    }

    # Pinterest allows basic auth (client_id/client_secret) or header — use tuple auth for requests
    try:
        resp = requests.post(TOKEN_URL, data=payload, auth=(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET), timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.exception("Pinterest refresh token request failed")
        return False, None

    new_access = data.get("access_token")
    if not new_access:
        logger.error("Refresh token response did not include access_token")
        return False, None

    try:
        token_entry.access_token = new_access
        if data.get("refresh_token"):
            token_entry.refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")
        if isinstance(expires_in, (int, float)):
            token_entry.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
        else:
            token_entry.expires_at = datetime.utcnow() + timedelta(seconds=3600)
        db.session.commit()
        return True, new_access
    except Exception:
        db.session.rollback()
        logger.exception("Failed to update token entry after refresh")
        return False, None


# ---------------------------
# 4) Protected endpoint: get Pinterest "me"

# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = "auth.login"

# @login_manager.user_loader
# def load_user(user_id):
#     """Flask-Login: load user by ID stored in session."""
#     return User.query.get(user_id)
# ---------------------------
@pinterest_bp.route("/pinterest/me", methods=["GET"])
@jwt_required
def get_pinterest_me():

    user_id = request.current_user_id

    token_entry = Pinterest.query.filter_by(user_id=str(user_id)).first()
    if not token_entry:
        return jsonify({"error": "No Pinterest account linked. Please connect Pinterest."}), 404

    access_token = token_entry.access_token

    # Refresh token if missing or expiring in 5 minutes
    if not token_entry.expires_in or datetime.datetime.utcnow() >= (token_entry.expires_in - timedelta(minutes=5)):
        success, new_token = refresh_pinterest_token(token_entry)
        if not success:
            return jsonify({"error": "Token refresh failed. Please re-authenticate with Pinterest."}), 401
        access_token = new_token

    try:
        resp = requests.get(
            "https://api.pinterest.com/v5/user_account",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        resp.raise_for_status()
        return jsonify(resp.json()), 200

    except requests.RequestException as exc:
        return jsonify({"error": "Pinterest API request failed", "details": str(exc)}), 502


# ---------------------------
# 5) Manual exchange route (for testing)
# ---------------------------
@pinterest_bp.route("/pinterest/exchange_code_manual", methods=["POST"])
@login_required
def exchange_code_manual():
    """
    Exchange an authorization code for tokens using request JSON.
    For testing/debugging: accepts {"code": "..."} in JSON and associates tokens with the logged-in user.
    NOTE: This route requires the user to be logged in (no hardcoded user_id).
    """
    from models import db, Pinterest  # local import

    payload = request.get_json() or {}
    code = payload.get("code")

    if not code:
        return jsonify({"error": "Missing 'code' in request body"}), 400

    user_id = current_user.id

    headers = _basic_auth_header(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET)
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": PINTEREST_REDIRECT_URI,
    }

    try:
        resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
    except requests.RequestException as exc:
        logger.exception("Manual token exchange failed")
        return jsonify({"error": "Token exchange failed", "details": str(exc)}), 502

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    scopes = token_data.get("scope", "")
    token_type = token_data.get("token_type", "")

    if not access_token:
        return jsonify({"error": "No access token returned"}), 502

    expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in)) if expires_in else datetime.utcnow() + timedelta(seconds=3600)

    # Persist
    try:
        record = Pinterest.query.filter_by(user_id=user_id).first()
        if record:
            record.access_token = access_token
            record.refresh_token = refresh_token or record.refresh_token
            record.expires_at = expires_at
            record.scopes = scopes
            record.token_type = token_type
        else:
            new_rec = Pinterest(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scopes=scopes,
                token_type=token_type,
            )
            db.session.add(new_rec)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to save tokens (manual exchange)")
        return jsonify({"error": "DB save failed"}), 500

    return jsonify({"message": "Tokens stored successfully"}), 200


@pinterest_bp.route("/boards", methods=["GET"])
@jwt_required
def get_pinterest_boards():
    from models import Pinterest

    token_entry = Pinterest.query.filter_by(user_id=request.current_user_id).first()
    if not token_entry:
        return jsonify({"error": "No Pinterest account linked"}), 404

    access_token = token_entry.access_token

    url = "https://api.pinterest.com/v5/boards"

    resp = requests.get(url, headers={
        "Authorization": f"Bearer {access_token}"
    })

    if resp.status_code != 200:
        return jsonify({"error": "Failed to fetch boards", "details": resp.text}), 400

    return jsonify(resp.json())


@pinterest_bp.route("/auth/pinterest", methods=["POST"])
def pinterest_auth():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    code = request.json.get("code")
    if not code:
        return jsonify({"error": "Missing code"}), 400

    # Now send Form-URL-Encoded to Pinterest
    token_url = "https://api.pinterest.com/v5/oauth/token"

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": PINTEREST_CLIENT_ID,
        "client_secret": PINTEREST_CLIENT_SECRET,
        "redirect_uri": "http://localhost:5173/auth/pinterest/callback"
    }

    headers = { 
        "Content-Type": "application/x-www-form-urlencoded" 
    }

    try:
        resp = requests.post(token_url, data=payload, headers=headers)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        print(e)
        return jsonify({"error": "An error occurred"}), 400
    

@pinterest_bp.route("/pinterest/exchange_token", methods=["POST"])
def exchange_pinterest_token():
    """
    Expects JSON body with a "code" field.
    Exchanges Pinterest OAuth code for an access token.
    """
    data = request.get_json()
    code = data.get("code")
    
    if not code:
        return jsonify({"error": "Missing 'code' in request body"}), 400

    token_url = "https://api.pinterest.com/v5/oauth/token"

    # Payload as application/x-www-form-urlencoded
    payload = {
        "grant_type": "authorization_code",
        "client_id": PINTEREST_CLIENT_ID,
        "client_secret": PINTEREST_CLIENT_SECRET,
        "code": code,
        "redirect_uri": PINTEREST_REDIRECT_URI
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # POST request to Pinterest
    response = requests.post(token_url, data=payload, headers=headers)

    if response.status_code != 200:
        return jsonify({
            "error": "Token exchange failed",
            "details": response.json()
        }), response.status_code

    return jsonify(response.json())


# @pinterest_bp.route("/boards/lookup_by_url", methods=["GET"])
# @jwt_required
# def get_board_by_url():
#     """
#     Retrieves a Pinterest board using its public URL.
#     Requires 'url' query parameter and 'boards:read' scope.
#     """
#     from models import Pinterest

#     board_url = request.args.get("url")
#     if not board_url:
#         return jsonify({"error": "Missing 'url' query parameter."}), 400

#     user_id = request.current_user_id
#     token_entry = Pinterest.query.filter_by(user_id=user_id).first()

#     # --- 1. Token Check (Using Refresh Helper) ---
#     if not token_entry:
#         return jsonify({"error": "No Pinterest account linked."}), 404

#     access_token = token_entry.access_token
#     # Assuming refresh_pinterest_token is available and works as defined
#     # if token_entry.expires_in and datetime.datetime.utcnow() >= (token_entry.expires_in - timedelta(minutes=5)):
#     #     success, access_token = refresh_pinterest_token(token_entry)
#     #     if not success:
#     #         return jsonify({"error": "Token refresh failed. Re-authenticate."}), 401

#     headers = {"Authorization": f"Bearer {access_token}"}
    
#     # --- 2. Lookup Board ID using URL ---
#     lookup_url = "https://api.pinterest.com/v5/boards/lookup"
#     lookup_params = {
#         "url": board_url,
#         "fields": "id"  # Only need the ID for the next step
#     }

#     try:
#         lookup_resp = requests.get(lookup_url, headers=headers, params=lookup_params, timeout=10)
#         lookup_resp.raise_for_status()
#         lookup_data = lookup_resp.json()
#     except requests.RequestException as exc:
#         logger.error(f"Pinterest Board Lookup failed: {exc}")
#         return jsonify({
#             "error": "Failed to look up board ID from URL.", 
#             "details": lookup_resp.text if 'lookup_resp' in locals() else str(exc)
#         }), 400

#     board_id = lookup_data.get("id")
#     if not board_id:
#         return jsonify({"error": "Could not extract Board ID from the given URL."}), 404
        
#     # --- 3. Fetch Full Board Details using Board ID ---
#     board_fields = "id,name,description,pin_count,follower_count,owner,created_at,privacy"
    
#     board_url_final = f"https://api.pinterest.com/v5/boards/{board_id}"
#     board_params_final = {"fields": board_fields}
    
#     try:
#         final_resp = requests.get(board_url_final, headers=headers, params=board_params_final, timeout=10)
#         final_resp.raise_for_status()
#         board_data = final_resp.json()
        
#         return jsonify(board_data), 200

#     except requests.RequestException as exc:
#         logger.error(f"Pinterest Board Fetch failed for ID {board_id}: {exc}")
#         return jsonify({
#             "error": "Failed to fetch board details.", 
#             "details": final_resp.text if 'final_resp' in locals() else str(exc)
#         }), 502
    

@pinterest_bp.route("/boards/lookup_by_url", methods=["GET"])
@jwt_required
def get_board_by_url():
    """
    Retrieves a Pinterest board using its public URL.
    Requires 'url' query parameter and 'boards:read' scope.
    """
    from models import Pinterest

    board_url = request.args.get("url")
    if not board_url:
        return jsonify({"error": "Missing 'url' query parameter."}), 400

    user_id = request.current_user_id
    token_entry = Pinterest.query.filter_by(user_id=user_id).first()

    # --- 1. Token Check (Using Refresh Helper) ---
    if not token_entry:
        return jsonify({"error": "No Pinterest account linked."}), 404

    access_token = token_entry.access_token
    # Assuming refresh_pinterest_token is available and works as defined
    # if token_entry.expires_in and datetime.datetime.utcnow() >= (token_entry.expires_in - timedelta(minutes=5)):
    #     success, access_token = refresh_pinterest_token(token_entry)
    #     if not success:
    #         return jsonify({"error": "Token refresh failed. Re-authenticate."}), 401

    headers = {"Authorization": f"Bearer {access_token}"}
    
    # --- 2. Lookup Board ID using URL ---
    lookup_url = "https://api.pinterest.com/v5/boards/lookup"
    lookup_params = {
        "url": board_url,
        "fields": "id"  # Only need the ID for the next step
    }

    try:
        lookup_resp = requests.get(lookup_url, headers=headers, params=lookup_params, timeout=10)
        lookup_resp.raise_for_status()
        lookup_data = lookup_resp.json()
    except requests.RequestException as exc:
        logger.error(f"Pinterest Board Lookup failed: {exc}")
        return jsonify({
            "error": "Failed to look up board ID from URL.", 
            "details": lookup_resp.text if 'lookup_resp' in locals() else str(exc)
        }), 400

    board_id = lookup_data.get("id")
    if not board_id:
        return jsonify({"error": "Could not extract Board ID from the given URL."}), 404
        
    # --- 3. Fetch Full Board Details using Board ID ---
    board_fields = "id,name,description,pin_count,follower_count,owner,created_at,privacy"
    
    board_url_final = f"https://api.pinterest.com/v5/boards/{board_id}"
    board_params_final = {"fields": board_fields}
    
    try:
        final_resp = requests.get(board_url_final, headers=headers, params=board_params_final, timeout=10)
        final_resp.raise_for_status()
        board_data = final_resp.json()
        
        return jsonify(board_data), 200

    except requests.RequestException as exc:
        logger.error(f"Pinterest Board Fetch failed for ID {board_id}: {exc}")
        return jsonify({
            "error": "Failed to fetch board details.", 
            "details": final_resp.text if 'final_resp' in locals() else str(exc)
        }), 502
    

@pinterest_bp.route("/boards/import", methods=["POST"])
@jwt_required
def import_pinterest_board():
    """
    1. Looks up the Pinterest Board ID using the provided URL.
    2. Stores the Board ID and metadata in the 'ImportedBoard' table.
    """
    from models import Pinterest, ImportedBoard, db # Ensure models are imported

    data = request.get_json()
    board_url = data.get("board_url")

    if not board_url:
        return jsonify({"error": "Missing 'board_url' in request body."}), 400

    user_id = request.current_user_id
    
    # 1. Fetch Pinterest Token and User Details
    token_entry = Pinterest.query.filter_by(user_id=user_id).first()

    if not token_entry:
        return jsonify({"error": "No Pinterest account linked. Please connect Pinterest."}), 404

    # Refresh token check (omitted here for brevity, but should be included as in /me)
    access_token = token_entry.access_token 
    
    # --- 2. Lookup Board ID using URL (Pinterest API Step 1) ---
    lookup_url = "https://api.pinterest.com/v5/boards/lookup"
    headers = {"Authorization": f"Bearer {access_token}"}
    lookup_params = {"url": board_url, "fields": "id"}

    try:
        lookup_resp = requests.get(lookup_url, headers=headers, params=lookup_params, timeout=10)
        lookup_resp.raise_for_status()
        lookup_data = lookup_resp.json()
        
        pinterest_board_id = lookup_data.get("id")
        if not pinterest_board_id:
             return jsonify({"error": "Invalid board URL or board not found."}), 404

    except requests.RequestException as exc:
        logger.error(f"Pinterest Board Lookup failed: {exc}. Response: {lookup_resp.text}")
        return jsonify({"error": "Failed to resolve board URL.", "details": str(exc)}), 502

    # --- 3. Fetch Board Metadata (Pinterest API Step 2) ---
    # Fetch full name and URL for saving
    board_fields = "id,name,url"
    board_url_final = f"https://api.pinterest.com/v5/boards/{pinterest_board_id}"
    board_params_final = {"fields": board_fields}
    
    try:
        final_resp = requests.get(board_url_final, headers=headers, params=board_params_final, timeout=10)
        final_resp.raise_for_status()
        board_data = final_resp.json()
        board_name = board_data.get("name")
        board_canonical_url = board_data.get("url")
    except requests.RequestException as exc:
        logger.error(f"Pinterest Board Fetch failed: {exc}")
        # Allow import even if metadata fetch fails, or return error
        return jsonify({"error": "Failed to fetch board metadata."}), 502


    # --- 4. Persist Board ID and Metadata to DB ---
    try:
        # Check if the board is already imported by this company
        existing_board = ImportedBoard.query.filter_by(
            pinterest_board_id=pinterest_board_id,
            company_id=token_entry.company_id # Assuming token_entry has company_id
        ).first()

        if existing_board:
            return jsonify({
                "message": "Board already imported.", 
                "board_id": pinterest_board_id
            }), 200

        new_board = ImportedBoard(
            pinterest_board_id=pinterest_board_id,
            pinterest_link_id=token_entry.pinterest_id,
            company_id=token_entry.company_id,
            name=board_name,
            url=board_canonical_url
        )
        db.session.add(new_board)
        db.session.commit()

        return jsonify({
            "message": f"Board '{board_name}' imported successfully.", 
            "board_id": pinterest_board_id
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to save imported board.")
        return jsonify({"error": "Database error during board import.", "details": str(e)}), 500

# @pinterest_bp.route("/boards/<pinterest_board_id>/pins", methods=["GET"])
# @jwt_required
# def get_board_pins(pinterest_board_id):
#     """
#     Retrieves the photos (pins) for a previously imported board ID, 
#     with critical token refresh logic.
#     """
#     # Import necessary models (assumes models is accessible)
#     from models import Pinterest, ImportedBoard, User
#     import requests
#     from datetime import datetime, timedelta
#     # from .pinterest_blueprint import refresh_pinterest_token, logger # Import helper and logger

#     user_id = request.current_user_id

#     # 0. Get User and Company ID
#     user = User.query.get(user_id)
#     if not user:
#         return jsonify({"error": "User not found."}), 404
#     current_user_company_id = user.company_id

    
#     # 1. Verify Board is Imported and get Link ID
#     imported_board = ImportedBoard.query.filter_by(
#         pinterest_board_id=pinterest_board_id,
#         company_id=current_user_company_id
#     ).first()

#     if not imported_board:
#         return jsonify({"error": "Board not found or not imported by your company."}), 404

#     # 2. Get the Access Token Entry
#     token_entry = Pinterest.query.filter_by(pinterest_id=imported_board.pinterest_link_id).first()
    
#     if not token_entry:
#         return jsonify({"error": "Authentication link broken. Please re-import the board."}), 401

#     # --- CRITICAL: Implement Token Refresh using your helper function ---
#     if not token_entry.expires_in or datetime.utcnow() >= (token_entry.expires_in - timedelta(minutes=5)):
#         logger.info(f"Token expiring for user {user_id}. Attempting refresh.")
#         success, new_token = refresh_pinterest_token(token_entry)
        
#         if not success:
#             logger.error(f"Token refresh failed for user {user_id}.")
#             return jsonify({"error": "Token refresh failed. Please re-authenticate."}), 401
        
#         access_token = new_token
#     else:
#         access_token = token_entry.access_token 
#     # -------------------------------------------------------------------
    
#     # 3. Fetch Pins for the Board ID
#     pins_url = f"https://api.pinterest.com/v5/boards/{pinterest_board_id}/pins"
#     pin_fields = "id,media,image_signature,link,title,description,created_at"
#     bookmark = request.args.get('bookmark') 
    
#     params = {
#         "fields": pin_fields,
#         "page_size": 25
#     }
#     if bookmark:
#         params["bookmark"] = bookmark

#     try:
#         resp = requests.get(pins_url, headers={"Authorization": f"Bearer {access_token}"}, params=params, timeout=15)
#         resp.raise_for_status()
        
#         response_data = resp.json()

#         # Format the response to return to the frontend
#         return jsonify({
#             "board_name": imported_board.name,
#             "pins": response_data.get("items", []),
#             "next_bookmark": response_data.get("bookmark")
#         }), 200

#     except requests.RequestException as exc:
#         logger.error(f"Pinterest Pins Fetch failed: {exc}. Response: {resp.text if 'resp' in locals() else 'N/A'}")
#         return jsonify({"error": "Failed to fetch pins from Pinterest.", "details": str(exc)}), 502


# Assuming @pinterest_bp is defined elsewhere
# Assuming 'Pinterest' model and 'requests' are imported

@pinterest_bp.route("/boards/<board_id>/pins", methods=["GET"])
@jwt_required
def get_pins_in_board(board_id):
    """
    Retrieves all Pins in a specified Pinterest Board.
    Requires 'boards:read' scope.
    
    NOTE: In this version, company_id is expected as a query parameter.
    """
    from models import Pinterest
    
    # --- 1. Extract IDs from Authentication and Request ---
    # ASSUMPTION: get_jwt_identity() returns the user_id (the subject 'sub' of the token).
    user_id = request.current_user_id
    
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"error": "User not found."}), 404
    # Retrieve the company_id from the query parameters or request body 
    # since it's no longer being extracted from custom JWT claims.
    # We'll use a query parameter for simplicity here.
    company_id = current_user.company_id

    # if not user_id:
    #     # get_jwt_identity() should always return something if jwt_required passes
    #     return jsonify({"error": "User ID missing from authentication token."}), 401
    
    if not company_id:
        # If company_id is crucial for the lookup, it must be provided
        return jsonify({"error": "Company ID is required in the request parameters."}), 400

    # --- 2. Fetch Token Entry ---
    # Now using the IDs retrieved from the identity and the request
    token_entry = Pinterest.query.filter_by(
        user_id=user_id, 
        company_id=company_id
    ).first()
    
    if not token_entry:
        return jsonify({"error": "Pinterest account not linked for this user/company combination"}), 404

    # --- 3. Pinterest API Call ---
    url = f"https://api.pinterest.com/v5/boards/{board_id}/pins"
    headers = {"Authorization": f"Bearer {token_entry.access_token}"}

    # Set page_size, and you might want to add pagination logic here later
    params = { "page_size": 50 } 

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status() # Raise an exception for HTTP error codes (4xx or 5xx)
        return jsonify(resp.json()), resp.status_code

    except requests.RequestException as exc:
        # Handle errors during the external Pinterest API call
        error_details = resp.text if 'resp' in locals() else str(exc)
        status_code = resp.status_code if 'resp' in locals() else 500
        return jsonify({
            "error": "Failed to retrieve pins from Pinterest.",
            "details": error_details
        }), status_code
    


    

