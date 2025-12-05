from datetime import datetime, timedelta
from functools import wraps
import os

from flask import request
from flask import jsonify
import jwt


ACCESS_TOKEN_SECRET=str(os.getenv('ACCESS_TOKEN_SECRET'))
REFRESH_TOKEN_SECRET=str(os.getenv('REFRESH_TOKEN_SECRET'))


refresh_token_expiry_time=timedelta(days=7)



def create_access_token(user_id, company_id):
    expiration = datetime.utcnow() + timedelta(minutes=30)  # expires in 10 sec
    return jwt.encode(
        {'user_id': user_id, 'company_id': company_id, 'exp': expiration},
        ACCESS_TOKEN_SECRET,
        algorithm='HS256'
    )


def create_refresh_token(user_id,company_id):
    expiration = datetime.utcnow() + timedelta(days=7)  # Refresh token expires in 7 days
    return jwt.encode({'user_id': user_id,'company_id':company_id, 'exp': expiration}, REFRESH_TOKEN_SECRET, algorithm='HS256')


def decode_jwt(jwt_token, secret_key):
    try:
        # Decode the token and verify its signature
        decoded = jwt.decode(jwt_token, secret_key, algorithms=["HS256"])  # Replace HS256 with your algorithm
        return decoded
    except jwt.ExpiredSignatureError:
        # Token has expired
        return {"message": "Token has expired"}
    except jwt.InvalidTokenError:
        # Token is invalid
        return {"message": "Invalid token"}
   



def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authorization header is missing or invalid"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = decode_jwt(token, ACCESS_TOKEN_SECRET)
            
            # Check for token validation errors
            if 'message' in payload:
                return jsonify({"error": payload['message']}), 401
                
            user_id = payload.get("user_id")
            company_id = payload.get("company_id")
            
            if not user_id:
                return jsonify({"error": "Unauthorized Token"}), 401

            # Set the user_id and company_id on the request object
            request.current_user_id = user_id
            request.current_company_id = company_id

        except Exception as e:
            return jsonify({"error": str(e)}), 401

        return f(*args, **kwargs)
    return decorated_function

def get_auth_key_from_request(request):
    pass


import jwt
from flask import request, jsonify

ACCESS_TOKEN_SECRET = "your-secret-key"  # import this from config if needed


def get_user_from_auth_header():
    """
    Extracts and decodes user_id + company_id from a custom JWT.
    Expected header format:
    Authorization: Bearer <token>
    """
    auth_header = request.headers.get("Authorization", None)
    if not auth_header:
        return None, jsonify({"error": "Missing Authorization header"}), 401

    if not auth_header.startswith("Bearer "):
        return None, jsonify({"error": "Invalid Authorization format"}), 401

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=["HS256"])
        # payload contains: {"user_id": ..., "company_id": ..., "exp": ...}
        return payload, None, None

    except jwt.ExpiredSignatureError:
        return None, jsonify({"error": "Token expired"}), 401

    except jwt.InvalidTokenError:
        return None, jsonify({"error": "Invalid token"}), 401
