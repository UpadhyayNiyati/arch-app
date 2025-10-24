from flask import Flask , jsonify , request
#from architect_mngmnt_app.models import db
from models import db
from dotenv import load_dotenv
from flask_jwt_extended import jwt_required , create_access_token , get_jwt_identity , JWTManager
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# from flask_bcrypt import Bcrypt 
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS


SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


#configure the app
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle':280
}

#Add JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

db.init_app(app)

# Initialize Flask-Migrate after initializing the app and db
migrate = Migrate(app, db)
# bcrypt = Bcrypt(app)

#Register blueprints
from routes.clients_routes import clients_bp
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
app.register_blueprint(upload_bp , url_prefix = '/api/upload_files')
app.register_blueprint(template_cards_bp , url_prefix = '/api/template_cards')
app.register_blueprint(cards_bp , url_prefix = '/api/cards')

#create tables
with app.app_context():
    db.create_all()
    print("✅ Tables created successfully!")


if __name__ == "__main__":
    app.run(debug = True)