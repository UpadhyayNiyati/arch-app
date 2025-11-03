import requests
from flask import Flask, request, session, redirect, url_for, abort,jsonify
import os
import json
from dotenv import load_dotenv
import secrets
import base64

load_dotenv()

TOKEN_URL = os.getenv("TOKEN_URI")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")





def exchange_code_for_tokens(code):
    """
    Makes a secure POST request to the Authorization Server's Token Endpoint
    to exchange the one-time authorization code for an access token.
    """
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    base64_auth = base64.b64encode(auth_string.encode()).decode()
    # 1. Define the parameters for the POST request
    payload = {
        'grant_type': 'authorization_code', # Specifies the OAuth 2.0 flow
        'code': code,                      # The code received from the redirect
        'redirect_uri': REDIRECT_URI,      # Must match the original redirect_uri
        # 'client_id': CLIENT_ID,            # Your application's ID
        # 'client_secret': CLIENT_SECRET     # Your application's secret (kept secure on the backend!)
    }

    # 2. Make the POST request
    try:
        response = requests.post(
            TOKEN_URL,
            data=payload,
            headers={
                'Accept': 'application/json',
                'Authorization': f'Basic {base64_auth}'
                }
        )
        response.raise_for_status()  # Raise an exception for HTTP error codes (4xx or 5xx)

        # 3. Process the successful response
        token_data = response.json()
        return token_data

    except requests.exceptions.HTTPError as err:
        print(f"Token exchange failed with HTTP error: {err}")
        print(f"Server response: {response.text}")
        raise

# --- Integration into your Flask application ---

app = Flask(__name__)
app.secret_key = os.getenv("JWT_SECRET_KEY") # Required for using Flask's session object

@app.route('/callback')
def oauth_callback():
    authorization_code = request.args.get('code')
    state_from_auth_server = request.args.get('state')
    expected_state = session.pop('oauth_state', None) # Pop the state sent in Step 1

    if not authorization_code or not expected_state or state_from_auth_server != expected_state:
        # State mismatch or missing code/error
        abort(403) # Forbidden
    
    try:
        # 🚀 Perform the token exchange 🚀
        tokens = exchange_code_for_tokens(authorization_code)

        # Store the tokens securely in the session or a database
        session['access_token'] = tokens.get('access_token')
        session['refresh_token'] = tokens.get('refresh_token')
        session['token_type'] = tokens.get('token_type')
        
        # Optionally, check for an ID Token if using OpenID Connect
        # session['id_token'] = tokens.get('id_token') 

        # Redirect the user to their profile/dashboard page
        return redirect(url_for('profile'))

    except Exception as e:
        print(f"Fatal Error during token exchange: {e}")
        return "Authentication failed. Please try again.", 500

# Placeholder for a protected route
@app.route('/profile')
def profile():
    if 'access_token' not in session:
        return redirect(url_for('login')) # Redirect to login if no token
    return f"Welcome! Your Access Token is: {session['access_token'][:10]}..."

if __name__ == '__main__':
    # Add a simple login route to initiate the flow for a complete example
    @app.route('/login')
    def login():
        # This is where you would redirect the user to the Authorization Server
        # You'd generate and store the state here first!
        import secrets
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        auth_url = f"https://authorization-server.com/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state={state}"
        return redirect(auth_url)

    app.run(debug=True)