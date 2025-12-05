from flask import Flask , jsonify , request
#from architect_mngmnt_app.models import db
from models import db , User
from dotenv import load_dotenv
from flask_jwt_extended import jwt_required , create_access_token , get_jwt_identity , JWTManager
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flasgger import Swagger
from flask_login import LoginManager
# from flask_bcrypt import Bcrypt 
import os




import time
import datetime
import platform
import sys

# print("Python:", sys.version)
# print("Platform:", platform.platform())
# print("time.time() =", time.time())
# print("utcnow timestamp =", datetime.datetime.utcnow().timestamp())
# print("difference =", datetime.datetime.utcnow().timestamp() - time.time())




# Load environment variables
load_dotenv()

app = Flask(__name__)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

login_manager = LoginManager()
login_manager.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
# login_manager.login_view = "auth.login"
login_manager.login_view = "user.login_user"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.config['SWAGGER'] = {
    'title': 'My Free Flask API Docs',
    'uiversion': 3,  # Use OpenAPI 3.0
    'specs_route': '/apidocs/' # The URL path to access the docs
}

swagger = Swagger(app)

CORS(app)

PINTEREST_TOKEN = os.environ.get('PINTEREST_ACCESS_TOKEN')

# --- Configuration (These would be stored securely in config or environment variables) ---
TOKEN_URL = os.getenv("TOKEN_URI")  # Replace with the real Token Endpoint
CLIENT_ID = os.getenv("CLIENT_ID")            # Your application's client ID
CLIENT_SECRET = os.getenv("CLIENT_SECRET")   # Your application's client secret
REDIRECT_URI = os.getenv("REDIRECT_URI") # Must match the one registered with the server
# --------------------------------------------------------------------------------------

database_uri = os.getenv('DATABASE_URI')
if not database_uri:
    raise RuntimeError("DATABASE_URI not found. Check your .env file!")
#configure the app
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle':280
}

#configure the app
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT" , "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
# db.init_app(app)


SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT" , "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# --------------------------------------------------------------------------------------
# --- Database and JWT Configuration (MUST be set before db.init_app) ---


#Add JWT Configuration
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

db.init_app(app)

@app.route('/hello', methods=['GET'])
def hello_world():
    """
    A simple Hello World endpoint.
    ---
    tags:
      - Basic Endpoints
    responses:
      200:
        description: A successful welcome message.
        schema:
          type: object
          properties:
            message:
              type: string
              example: Hello from Flasgger!
    """
    return jsonify({'message': 'Hello from Flasgger!'})

@app.route('/create_user', methods=['POST'])
def create_user():
    """
    Creates one or more new user accounts.
    ---
    tags:
      - Users
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: array
          description: A list of users to create.
          items:
            type: object
            required:
              - username
              - email
            properties:
              username:
                type: string
                description: The user's desired username.
              email:
                type: string
                format: email
                description: The user's email address.
    responses:
      201:
        description: User(s) created successfully.
        schema:
          type: object
          properties:
            message:
              type: string
            created_users:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  username:
                    type: string
                  status:
                    type: string
      400:
        description: Invalid input data or no valid users provided.
    """
    data = request.get_json()
    
    if not isinstance(data, list):
        data = [data] if data else []

    created_users = []
    
    for index,user_data in enumerate(data):
        username = user_data.get('username')
        email = user_data.get('email')
        
        if username and email:
            # --- Mocking the DB logic for example ---
            base_mock_id = int(datetime.now().timestamp() * 1000) % 10000 
            mock_id = base_mock_id + index
            
            created_users.append({
                "id": mock_id, 
                "username": username,
                "status": "Created"
            })
            
    if created_users:
        return jsonify({
            "message": f"Successfully created {len(created_users)} user(s).",
            "created_users": created_users
        }), 201
    else:
        return jsonify({
            "message": "No valid user data found in the request."
        }), 400
    
@app.route('/update_user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Updates an existing user account by ID.
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: The ID of the user to update.
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              description: The new username. (Optional)
            email:
              type: string
              format: email
              description: The new email address. (Optional)
    responses:
      200:
        description: User updated successfully.
        schema:
          type: object
          properties:
            id:
              type: integer
            message:
              type: string
      400:
        description: Invalid input data.
      404:
        description: User not found.
    """
    data = request.get_json()
    
    # --- Start Update Logic ---
    
    # 1. Check if data is present
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    # 2. In a real application, you would:
    #    a. Query the database to find the user by user_id.
    #    b. If user not found, return jsonify({"message": "User not found"}), 404
    #    c. Update the user's fields with the data received.
    #    d. Commit the changes to the database (db.session.commit()).
    
    # --- Mock Response for testing ---
    if user_id == 999:
        return jsonify({"message": f"User with ID {user_id} not found"}), 404

    # Simulate a successful update
    updated_fields = ", ".join(data.keys())
    
    return jsonify({
        "id": user_id, 
        "message": f"User ID {user_id} updated successfully. Fields updated: {updated_fields}"
    }), 200

# Initialize Flask-Migrate after initializing the app and db
migrate = Migrate(app, db)
# bcrypt = Bcrypt(app)

#Register blueprints
from routes.clients_routes import clients_bp
from routes.roles_routes import roles_bp
from routes.user_routes import user_bp
from routes.documents_routes import documents_bp
from routes.project_assignments_routes import project_assignments_bp
from routes.project_vendor_routes import project_vendor_bp
from routes.projects_routes import projects_bp
from routes.tasks_routes import tasks_bp
from routes.templates_routes import templates_bp
from routes.vendors_routes import vendors_bp
from routes.projects_templates_routes import project_templates_bp
from routes.otp_routes import otp_bp
from routes.boards_routes import boards_bp
from routes.pins_routes import pins_bp
from routes.tags_routes import tags_bp
from routes.spaces_routes import spaces_bp
from routes.drawings_routes import drawings_bp
from routes.inspiration_routes import inspiration_bp
from routes.upload_files_routes import upload_bp
from routes.template_cards_routes import template_cards_bp
from routes.cards_routes import cards_bp
from routes.companies_routes import companies_bp
from routes.super_user_routes import super_user_bp
from routes.teams_routes import teams_bp
# from routes.payments_routes import payments_bp
from routes.invoices_routes import invoices_bp
from routes.preset_routes import preset_bp
from routes.pinterest_routes import pinterest_bp
from auth.auth import auth_bp
from routes.user_roles_routes import user_roles_bp
from routes.invite_routes import invite_bp

app.register_blueprint(teams_bp , url_prefix = "/api/teams")
app.register_blueprint(roles_bp, url_prefix="/api/roles")
# app.register_blueprint(payments_bp, url_prefix="/api/payments")
app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
app.register_blueprint(clients_bp, url_prefix="/api/clients")
app.register_blueprint(user_bp, url_prefix="/api/user")
app.register_blueprint(documents_bp, url_prefix="/api/documents")
app.register_blueprint(project_assignments_bp, url_prefix="/api/project_assignments")
app.register_blueprint(project_vendor_bp, url_prefix="/api/project_vendor")
app.register_blueprint(projects_bp, url_prefix="/api/projects")
app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
app.register_blueprint(templates_bp, url_prefix="/api/templates")
app.register_blueprint(vendors_bp, url_prefix="/api/vendors")
app.register_blueprint(project_templates_bp, url_prefix="/api/project_templates")
app.register_blueprint(otp_bp, url_prefix="/api/otp")
app.register_blueprint(boards_bp , url_prefix = "/api/boards")
app.register_blueprint(pins_bp , url_prefix = "/api/pins")
app.register_blueprint(tags_bp , url_prefix = "/api/tags")
app.register_blueprint(spaces_bp , url_prefix = "/api/spaces")
app.register_blueprint(drawings_bp , url_prefix = "/api/drawings")
app.register_blueprint(inspiration_bp , url_prefix = "/api/inspiration")
app.register_blueprint(upload_bp , url_prefix = '/api')
app.register_blueprint(template_cards_bp , url_prefix = '/api/template_cards')
app.register_blueprint(cards_bp , url_prefix = '/api/cards')
app.register_blueprint(companies_bp , url_prefix = '/api/companies')
app.register_blueprint(super_user_bp , url_prefix = '/api/super_user')
app.register_blueprint(preset_bp , url_prefix = '/api/preset')
app.register_blueprint(pinterest_bp , url_prefix = '/api/pinterest')
app.register_blueprint(auth_bp , url_prefix = '/api/auth')
app.register_blueprint(invite_bp , url_prefix = '/api/invite')
app.register_blueprint(user_roles_bp , url_prefix = '/api/user_roles')

#create tables
with app.app_context():
    db.create_all()
    print("✅ Tables created successfully!")



# print(os.path.exists("uploads/inspiration_uploads/2a59677d-b072-4570-925c-255a85efe195/Screenshot_2025-01-21_155435.png"))

# print(app.url_map)

if __name__ == "__main__":
    app.run(debug = True)