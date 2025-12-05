"""
pinterest_blueprint.py
Flask blueprint to handle Pinterest OAuth v5 - CORS handled at app level
"""

import os
import uuid
import base64
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests
from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import get_jwt_identity, jwt_required
from models import db, Pinterest

logger = logging.getLogger(__name__)

# Create blueprint WITHOUT CORS
pinterest_bp = Blueprint("pinterest", __name__)

# Environment variables
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
PINTEREST_CLIENT_ID = os.getenv("PINTEREST_CLIENT_ID")
PINTEREST_CLIENT_SECRET = os.getenv("PINTEREST_CLIENT_SECRET")
# PINTEREST_REDIRECT_URI = os.getenv("PINTEREST_REDIRECT_URI", "http://localhost:5173/auth/pinterest/callback")
PINTEREST_REDIRECT_URI = os.getenv("PINTEREST_REDIRECT_URI" , "http://localhost:5000/api/pinterest/callback")

if not all([PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET]):
    logger.error("Missing Pinterest config: PINTEREST_CLIENT_ID / PINTEREST_CLIENT_SECRET")


def _basic_auth_header(client_id: str, client_secret: str) -> dict:
    """Build Basic auth header for Pinterest token requests"""
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")
    return {"Authorization": f"Basic {encoded}"}


@pinterest_bp.route("/start", methods=["GET"])
@jwt_required()
def start_pinterest_login():
    """Initiate Pinterest OAuth flow"""
    state = str(uuid.uuid4())
    
    identity = get_jwt_identity()
    user_id = identity.get("user_id")
    
    session["pinterest_oauth_state"] = state
    session["pinterest_oauth_user_id"] = str(user_id)
    
    params = {
        "response_type": "code",
        "client_id": PINTEREST_CLIENT_ID,
        "redirect_uri": PINTEREST_REDIRECT_URI,
        "scope": "ads:read,pins:read,boards:read,boards:write,pins:write,user_accounts:read",
        "state": state,
    }
    
    auth_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"
    
    return jsonify({"auth_url": auth_url}), 200


@pinterest_bp.route("/callback", methods=["POST"])
def pinterest_callback():
    """Handle OAuth callback from Pinterest"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400
    
    code = data.get("code")
    state = data.get("state")
    
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400
    
    stored_state = session.get("pinterest_oauth_state")
    if not stored_state or stored_state != state:
        return jsonify({"error": "Invalid state parameter"}), 400
    
    user_id = session.get("pinterest_oauth_user_id")
    if not user_id:
        return jsonify({"error": "User session not found"}), 400
    
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": PINTEREST_REDIRECT_URI,
    }
    
    headers = _basic_auth_header(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    
    try:
        resp = requests.post(TOKEN_URL, headers=headers, data=token_data, timeout=10)
        resp.raise_for_status()
        token_response = resp.json()
    except requests.RequestException as exc:
        logger.exception("Token exchange failed")
        return jsonify({"error": "Token exchange failed", "details": str(exc)}), 502
    
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in", 3600)
    
    if not access_token:
        return jsonify({"error": "No access token received"}), 502
    
    expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
    
    try:
        token_entry = Pinterest.query.filter_by(user_id=user_id).first()
        
        if token_entry:
            token_entry.access_token = access_token
            token_entry.refresh_token = refresh_token
            token_entry.expires_at = expires_at
            token_entry.scopes = token_response.get("scope", "")
            token_entry.token_type = token_response.get("token_type", "Bearer")
        else:
            token_entry = Pinterest(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scopes=token_response.get("scope", ""),
                token_type=token_response.get("token_type", "Bearer")
            )
            db.session.add(token_entry)
        
        db.session.commit()
        
        session.pop("pinterest_oauth_state", None)
        session.pop("pinterest_oauth_user_id", None)
        
        return jsonify({
            "success": True,
            "message": "Pinterest account connected successfully"
        }), 200
        
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to save tokens")
        return jsonify({"error": "Database error", "details": str(exc)}), 500


def refresh_pinterest_token(token_entry):
    """Refresh Pinterest access token"""
    if not token_entry.refresh_token:
        logger.warning(f"No refresh token for user {token_entry.user_id}")
        return False, None
    
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token_entry.refresh_token,
    }
    
    try:
        resp = requests.post(
            TOKEN_URL,
            data=payload,
            auth=(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET),
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        logger.exception("Token refresh failed")
        return False, None
    
    new_access = data.get("access_token")
    if not new_access:
        logger.error("No access_token in refresh response")
        return False, None
    
    try:
        token_entry.access_token = new_access
        if data.get("refresh_token"):
            token_entry.refresh_token = data["refresh_token"]
        
        expires_in = data.get("expires_in", 3600)
        token_entry.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
        
        db.session.commit()
        return True, new_access
    except Exception:
        db.session.rollback()
        logger.exception("Failed to update refreshed tokens")
        return False, None


@pinterest_bp.route("/pinterest/me", methods=["GET"])
@jwt_required()
def get_pinterest_me():
    """Get Pinterest user account information"""
    identity = get_jwt_identity()
    user_id = str(identity.get("user_id"))
    
    token_entry = Pinterest.query.filter_by(user_id=user_id).first()
    if not token_entry:
        return jsonify({"error": "No Pinterest account linked"}), 404
    
    access_token = token_entry.access_token
    
    if not token_entry.expires_at or datetime.utcnow() >= (token_entry.expires_at - timedelta(minutes=5)):
        success, new_token = refresh_pinterest_token(token_entry)
        if not success:
            return jsonify({"error": "Token refresh failed. Please reconnect Pinterest."}), 401
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
        return jsonify({"error": "Pinterest API error", "details": str(exc)}), 502


@pinterest_bp.route("/pinterest/boards", methods=["GET"])
@jwt_required()
def get_pinterest_boards():
    """Get user's Pinterest boards"""
    identity = get_jwt_identity()
    user_id = str(identity.get("user_id"))
    
    token_entry = Pinterest.query.filter_by(user_id=user_id).first()
    if not token_entry:
        return jsonify({"error": "No Pinterest account linked"}), 404
    
    access_token = token_entry.access_token
    
    if not token_entry.expires_at or datetime.utcnow() >= (token_entry.expires_at - timedelta(minutes=5)):
        success, new_token = refresh_pinterest_token(token_entry)
        if not success:
            return jsonify({"error": "Token refresh failed"}), 401
        access_token = new_token
    
    try:
        resp = requests.get(
            "https://api.pinterest.com/v5/boards",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        resp.raise_for_status()
        return jsonify(resp.json()), 200
    except requests.RequestException as exc:
        logger.exception("Failed to fetch boards")
        return jsonify({"error": "Failed to fetch boards", "details": str(exc)}), 502


@pinterest_bp.route("/pinterest/disconnect", methods=["DELETE"])
@jwt_required()
def disconnect_pinterest():
    """Remove Pinterest connection for current user"""
    identity = get_jwt_identity()
    user_id = str(identity.get("user_id"))
    
    token_entry = Pinterest.query.filter_by(user_id=user_id).first()
    if not token_entry:
        return jsonify({"error": "No Pinterest account linked"}), 404
    
    try:
        db.session.delete(token_entry)
        db.session.commit()
        return jsonify({"success": True, "message": "Pinterest disconnected"}), 200
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to disconnect Pinterest")
        return jsonify({"error": "Database error"}), 500