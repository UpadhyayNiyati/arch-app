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
from urllib.parse import urlencode
from flask_login import LoginManager
import requests
from flask import Blueprint, request, jsonify, redirect, url_for, session, current_app
from models import db, Pinterest
from flask_login import current_user, login_required
from flask import Blueprint, request, jsonify, redirect, url_for, session, current_app

# Import your application's db and Pinterest model
# from models import db, Pinterest
# Expected Pinterest model fields (example):
# class Pinterest(db.Model):
#     __tablename__ = "pinterest_tokens"
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
#     access_token = db.Column(db.Text, nullable=False)
#     refresh_token = db.Column(db.Text, nullable=True)
#     expires_at = db.Column(db.DateTime, nullable=True)  # UTC datetime when access token expires
#     scopes = db.Column(db.String(512), nullable=True)
#     token_type = db.Column(db.String(64), nullable=True)
#     pinterest_account_id = db.Column(db.String(128), nullable=True)

# If you use a different model / column names, adapt the code below.

logger = logging.getLogger(__name__)
pinterest_bp = Blueprint("pinterest", __name__)



# Config / env (do not hardcode in code; set environment variables in production)
TOKEN_URL = os.getenv("TOKEN_URI", "https://api.pinterest.com/v5/oauth/token")
PINTEREST_CLIENT_ID = os.getenv("PINTEREST_CLIENT_ID")
PINTEREST_CLIENT_SECRET = os.getenv("PINTEREST_CLIENT_SECRET")
PINTEREST_REDIRECT_URI = os.getenv("REDIRECT_URI")

# Basic sanity check
if not all([PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET, PINTEREST_REDIRECT_URI]):
    logger.error("Missing Pinterest config: PINTEREST_CLIENT_ID / PINTEREST_CLIENT_SECRET / PINTEREST_REDIRECT_URI")

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
@pinterest_bp.route("/pinterest/start", methods=["GET"])
# @login_required
def start_pinterest_login():
    """
    Initiate OAuth flow:
    - Store state and the initiating user ID in session
    - Redirect to Pinterest authorization URL
    """
    # Create and store state to validate on callback (CSRF protection)
    state = str(uuid.uuid4())
    session["pinterest_oauth_state"] = state
    # Also store which app user started the flow
    session["pinterest_auth_user_id"] = "40e03e23-27fb-47db-ab65-cff79891ec47"

    params = {
        "response_type": "code",
        "client_id": PINTEREST_CLIENT_ID,
        "redirect_uri": PINTEREST_REDIRECT_URI,
        # NOTE: Only request the scopes you truly need
        "scope": "ads:read,pins:read,boards:read",
        "state": state,
    }
    auth_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"
    
    return redirect(auth_url)


# ---------------------------
# 2) OAuth Callback
# ---------------------------
@pinterest_bp.route("/pinterest/callback", methods=["GET"])
def pinterest_callback():
    """
    Pinterest will redirect here with ?code=...&state=...
    Exchange code for tokens and persist them.
    """
    from models import db, Pinterest  # imported here to avoid circular import at module load
    
    code = request.args.get("code")
    state = request.args.get("state")
    user_id = session.pop("pinterest_auth_user_id", None)
    saved_state = session.pop("pinterest_oauth_state", None)

    if not code:
        logger.error("Pinterest callback missing 'code' param")
        return jsonify({"error": "Missing authorization code"}), 400

    # Validate state
    if not state or state != saved_state:
        logger.error("Invalid or missing OAuth state")
        return jsonify({"error": "Invalid OAuth state"}), 400

    if not user_id:
        logger.error("No initiating user stored in session for Pinterest OAuth")
        return jsonify({"error": "No user session found for this authorization flow"}), 400

    # Prepare exchange request
    headers = _basic_auth_header(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET)
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": PINTEREST_REDIRECT_URI,
    }

    try:
        resp = requests.post(TOKEN_URL, headers=headers, data=payload, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
    except requests.RequestException as exc:
        logger.exception("Failed to exchange code for tokens")
        return jsonify({"error": "Token exchange failed", "details": str(exc)}), 502

    # Extract token info
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", None)  # seconds
    scopes = token_data.get("scope", "")
    token_type = token_data.get("token_type", "")

    if not access_token:
        logger.error("Token exchange succeeded but no access_token returned")
        return jsonify({"error": "No access token returned from provider"}), 502

    expires_at = None
    if isinstance(expires_in, (int, float)):
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
    else:
        # If provider doesn't return expires_in, set a conservative expiry (1 hour)
        expires_at = datetime.utcnow() + timedelta(seconds=3600)

    # Try to fetch user account info (Pinterest account id)
    pinterest_account_id = None
    try:
        profile_resp = requests.get(
            "https://api.pinterest.com/v5/user_account",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        profile_resp.raise_for_status()
        pinterest_account_id = profile_resp.json().get("id")
    except requests.RequestException:
        logger.warning("Could not fetch Pinterest user_account; continuing without pinterest_account_id")

    # Save or update Pinterest record for the app user
    try:
        record = Pinterest.query.filter_by(user_id=user_id).first()
        if record:
            record.access_token = access_token
            record.refresh_token = refresh_token or record.refresh_token
            record.expires_at = expires_at
            record.scopes = scopes
            record.token_type = token_type
            if pinterest_account_id:
                record.pinterest_account_id = pinterest_account_id
        else:
            record = Pinterest(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scopes=scopes,
                token_type=token_type,
                pinterest_account_id=pinterest_account_id,
            )
            db.session.add(record)

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception("DB save failed for Pinterest tokens")
        return jsonify({"error": "Failed to save tokens"}), 500

    # Redirect or return JSON (choose depending on your app)
    # Example: redirect to a client page that shows success
    try:
        return redirect(url_for("main.pinterest_success"))
    except Exception:
        # Fallback JSON response if the named route is not present
        return jsonify({"message": "Pinterest linked successfully"}), 200


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
def get_pinterest_me():
    """
    Fetch the Pinterest user account info for the current authenticated user.
    Automatically refreshes the access token if it is near expiry.
    """
    if not current_user.is_authenticated:
        return jsonify({"error": "User not authenticated"}), 401

    user_id = str(current_user.id)
    token_entry = Pinterest.query.filter_by(user_id=user_id).first()

    if not token_entry:
        return jsonify({"error": "No Pinterest account linked. Please connect Pinterest."}), 404

    access_token = token_entry.access_token

    # Refresh token if missing expiry or about to expire (5-minute buffer)
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
        logger.exception("Pinterest API request failed")
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
        "client_id": os.environ.get("PINTEREST_CLIENT_ID"),
        "client_secret": os.environ.get("PINTEREST_CLIENT_SECRET"),
        "redirect_uri": "https://yourapp.com/auth/pinterest/callback"
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