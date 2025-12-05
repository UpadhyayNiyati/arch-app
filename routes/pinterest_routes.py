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
from flask import Flask
from urllib.parse import urlencode
from flask_login import LoginManager
from auth.authhelpers import get_user_from_auth_header , create_access_token , decode_jwt
from auth.auth import jwt_required 
from flask_jwt_extended import get_jwt_identity
from flask_cors import CORS
import requests
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

@pinterest_bp.route("/start", methods=["GET"])
@jwt_required
def start_pinterest_login():
    """Initiate Pinterest OAuth flow"""
    user_id = request.current_user_id
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    # Create state token with JWT (correct method)
    state = create_access_token(
        str(user_id),   # identity
        additional_claims={
            "user_id": user_id,
            "pinterest_state": True
        }
    )

    params = {
        "response_type": "code",
        "client_id": PINTEREST_CLIENT_ID,
        "redirect_uri": PINTEREST_REDIRECT_URI,
        "scope": "ads:read,pins:read,boards:read,boards:write,pins:write,user_accounts:read",
        "state": state
    }

    auth_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"

    return jsonify({"auth_url": auth_url}), 200


@pinterest_bp.route("/callback", methods=["GET"])
def pinterest_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        return jsonify({"error": "Missing code or state"}), 400

    # Decode state token
    try:
        decoded = decode_jwt(
            state,
            current_app.config["JWT_SECRET_KEY"]
        )
    except Exception as e:
        return jsonify({"error": "Invalid state token", "details": str(e)}), 400

    print("Decoded state:", decoded)

    user_id = decoded.get("user_id")

    if not user_id:
        return jsonify({"error": "Invalid decoded state"}), 400

    # Exchange code for Pinterest access token
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": PINTEREST_REDIRECT_URI,
        "client_id": PINTEREST_CLIENT_ID,
        "client_secret": PINTEREST_CLIENT_SECRET,
    }

    r = requests.post(TOKEN_URL, json=payload, timeout=10)

    if r.status_code != 200:
        return jsonify({
            "error": "Token exchange failed",
            "details": r.text
        }), 400

    data = r.json()

    # Save tokens
    expires_at = None
    if data.get("expires_in"):
        expires_at = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))

    pinterest_user_id = (data.get("user") or {}).get("id")

    p = Pinterest.query.filter_by(user_id=user_id).first()
    if p:
        p.access_token = data.get("access_token")
        p.refresh_token = data.get("refresh_token")
        p.expires_at = expires_at
        p.scopes = data.get("scope")
        p.pinterest_account_id = pinterest_user_id
    else:
        p = Pinterest(
            user_id=user_id,
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            scopes=data.get("scope"),
            pinterest_account_id=pinterest_user_id
        )
        db.session.add(p)

    db.session.commit()

    # Redirect back to frontend
    return redirect("http://localhost:5173/")




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
# @jwt_required
def get_pinterest_me():
    identity = get_jwt_identity()
    user_id = identity["user_id"]

    token_entry = Pinterest.query.filter_by(user_id=str(user_id)).first()
    if not token_entry:
        return jsonify({"error": "No Pinterest account linked. Please connect Pinterest."}), 404

    access_token = token_entry.access_token

    # Refresh token if missing or expiring in 5 minutes
    if not token_entry.expires_at or datetime.utcnow() >= (token_entry.expires_at - timedelta(minutes=5)):
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
@login_required
def get_pinterest_boards():
    from models import Pinterest

    token_entry = Pinterest.query.filter_by(user_id=current_user.id).first()
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

