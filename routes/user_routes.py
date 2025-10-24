from flask import Blueprint , jsonify , request
from models import User , db , OtpCode , ProjectAssignments , Clients , Projects , Tasks , Projectvendor , Vendors , Boards ,Pin , ProjectTemplates , Templates
from flask_jwt_extended import jwt_required , create_access_token , get_jwt_identity
from flask_migrate import Migrate
# from flask_bcrypt import bcrypt
from flask_bcrypt import Bcrypt
from email.message import EmailMessage
from werkzeug.security import generate_password_hash , check_password_hash
import smtplib
import random
import os

# from architect_mngmnt_app.archs import bcrypt as Bcrypt
from datetime import datetime , timedelta
import uuid

user_bp = Blueprint('user' , __name__)
bcrypt = Bcrypt()


# class OtpCode(db.Model):
#     __tablename__ = 'otp_codes'
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, nullable=False)
#     otp_code = db.Column(db.String(64), nullable=False)
#     created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
#     expires_at = db.Column(db.DateTime, nullable=False)
#     is_used = db.Column(db.Boolean, nullable=False, default=False)
#     attempts = db.Column(db.Integer, nullable=False, default=0)
#     type = db.Column(db.String(50), nullable=True)

# Helper function to send email
def send_email(recipients, subject, body):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = os.getenv('EMAIL_SENDER')
    msg['To'] = ', '.join(recipients)
    msg.set_content(body)
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.login(os.getenv('EMAIL_SENDER'), os.getenv('EMAIL_PASSWORD'))
        smtp.send_message(msg)



#get all users
@user_bp.route('/get_users' , methods = ['GET'])
def get_all_users():
    try:
        users = User.query.all()
        result = []
        for user in users:
            result.append({
                'user_id' : user.user_id , 
                'user_name' : user.user_name , 
                'user_email' : user.user_email , 
                'user_password' : user.user_password , 
                'user_address' : user.user_address , 
                'created_at' : user.created_at
            })
        return jsonify(result) , 200

    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#get single user by id
@user_bp.route('/get_one_user/<string:user_id>' , methods = ['GET'])
def get_user_by_id(user_id):
    user = User.query.get_or_404(user_id)
    if not user:
        return jsonify({"message":"User not found"}) , 404
    result = {
        'user_id' : user.user_id , 
        'user_name' : user.user_name , 
        'user_email' : user.user_email , 
        'user_password' : user.user_password , 
        'user_address' : user.user_address , 
        'created_at' : user.created_at
    }
    return jsonify(result) , 200

#post user
@user_bp.route('/post_user' , methods = ['POST'])
def post_user():
    data = request.json
    required_fields = ['user_name' , 'user_email' , 'user_phone' , 'user_password' , 'user_address']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"'{field}' is required"}), 400
        hashed_password = bcrypt.generate_password_hash(data['user_password']).decode('utf-8')
        try:
            new_user = User(
                user_name = data['user_name'] , 
                user_email = data['user_email'] ,
                user_phone = data['user_phone'] ,
                user_password = hashed_password ,
                user_address = data['user_address'] 
            )
            db.session.add(new_user)
            db.session.commit()
            return jsonify({"message" : "User added successfully"}) , 201
        except Exception as e:
            return jsonify({"error" : str(e)}) , 500
        

#user registration route
@user_bp.route('/register' , methods = ['POST'])
def register_user():
    data = request.json
    user_name = data.get("user_name")
    user_email = data.get("user_email")
    user_phone = data.get("user_phone")
    user_address = data.get("user_address")
    user_password = data.get("user_password")

    if not all([user_name, user_email, user_phone, user_address, user_password]):
        return jsonify({"message": "All fields are required"}), 400

    existing_user = User.query.filter_by(user_email=user_email).first()
    if existing_user:
        return jsonify({"message": "User with this email already exists"}), 409

    try:
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(user_password).decode('utf-8')

        new_user = User(
            user_name=user_name,
            user_email=user_email,
            user_phone=user_phone,
            user_address=user_address,
            user_password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        
        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now() + timedelta(minutes = 5)
        new_otp = OtpCode(
            user_id=new_user.user_id,
            otp_code=otp_code,
            expires_at=expires_at,
            type='registration'
        )
        db.session.add(new_otp)
        db.session.commit()

        # Send OTP via email
        send_email(
            recipients=[user_email],
            subject="Your Registration OTP",
            body=f"Hello {user_name},\n\nYour OTP code is {otp_code}. It is valid for 5 minutes."
        )

        return jsonify({"message": "User registered. Please check your email for the OTP."}), 201
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#user login route
@user_bp.route("/login" , methods = ['POST'])
def login_user():
    data = request.json
    user_email = data.get("user_email")
    user_password = data.get("user_password")

    if not all([user_email , user_password]):
        return jsonify({"message":"Email and password are required"}) , 400
    
    user = User.query.filter_by(user_email=user_email).first()

    if user and bcrypt.check_password_hash(user.user_password , user_password):
        try:
            OtpCode.query.filter_by(user_id = user.user_id).delete()
            db.session.commit()

            #generate new otp
            otp_code = str(random.randint(100000 , 999999))
            expires_at = datetime.now() + timedelta(minutes = 5)

            new_otp = OtpCode(
                user_id = user.user_id,
                otp_code = otp_code ,
                expires_at = expires_at,
                type = 'login'
            )
            db.session.add(new_otp)
            db.session.commit()

            send_email(
                recipients=[user_email],
                subject="Login Verification OTP",
                body=f"Hello {user.user_name},\n\nYour login verification code is {otp_code}. It is valid for 5 minutes."
            )

            return jsonify({"message": "OTP sent for login verification. Please check your email."}), 200
        
        except Exception as e:
            return jsonify({"error" : str(e)}) , 500
    else:
        return jsonify({"message" : "Invalid email or password"}) , 401
    
#protected_route
@user_bp.route('/protected' , methods = ['GET'])
@jwt_required()
def protected_route():
    current_user_id = get_jwt_identity()
    return jsonify({"message" : "You have access to this protected resource."}) , 200


#update user    
@user_bp.route('/update_user/<string:user_id>' , methods = ['PUT'])
def update_user(user_id):           
    data = request.json
    user = User.query.get_or_404(user_id)
    if not user:
        return jsonify({"message" : "User not found"}) , 404
    if "user_name" in data:
        user.user_name =data["user_name"]
    if "user_email" in data:
        user.user_email = data["user_email"]
    if "user_phone" in data:
        user.user_phone = data["user_phone"]
    if "user_password" in data:
        hashed_password = bcrypt.generate_password_hash(data['user_password']).decode('utf-8')
        user.user_password = hashed_password
    if "user_address" in data:
        user.user_address = data["user_address"]
    db.session.commit()
    return jsonify({"message" : "User updated successfully!!"}) , 200

#delete user
@user_bp.route('/del_user/<string:user_id>' , methods = ['DELETE'])
def del_user(user_id):
    user = User.query.get_or_404(user_id)
    if not user:
        return jsonify({"message":"User not found"}) , 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message" : "User deleted successfully!!"}) , 200

# Assuming all other imports and code from your prompt are present

# @user_bp.route('/dashboard/<string:user_id>', methods=['GET'])
# def get_user_dashboard(user_id):
#     try:
#         # Check if the user exists
#         user = User.query.get(user_id)
#         if not user:
#             return jsonify({"message": "User not found."}), 404

#         # Query all project assignments for the given user
#         assignments = ProjectAssignments.query.filter_by(user_id=user_id).all()
#         dashboard_data = []

#         # Iterate through each project assignment
#         for assignment in assignments:
#             # Get the project details
#             project = Projects.query.get(assignment.project_id)
#             if not project:
#                 continue

#             # Find the client for this project
#             client_info = None
#             client_assignment = ProjectAssignments.query.filter_by(
#                 project_id=project.project_id,
#                 role='client'
#             ).first()
#             if client_assignment:
#                 client = Clients.query.filter_by(user_id=client_assignment.user_id).first()
#                 if client:
#                     client_info = {
#                         "client_name": client.client_name,
#                         "client_email": client.client_email,
#                         "client_phone": client.client_phone
#                     }

#             # Get all tasks for this project
#             tasks = Tasks.query.filter_by(project_id=project.project_id).all()
#             task_list = []
#             for task in tasks:
#                 task_list.append({
#                     "task_id": task.task_id,
#                     "task_name": task.task_name,
#                     "status": task.status,
#                     "due_date": task.due_date.isoformat(),
#                     "priority": task.priority,
#                     "assigned_to": task.assigned_to 
#                 })
            
#             # --- NEW: Get all templates for this project ---
#             project_templates = ProjectTemplates.query.filter_by(project_id=project.project_id).all()
#             template_list = []
#             for pt in project_templates:
#                 template = Templates.query.get(pt.template_id)
#                 if template:
#                     template_list.append({
#                         "template_id": template.template_id,
#                         "template_name": template.template_name,
#                         "file_url": pt.template_file_url  # Assuming this is the project-specific URL
#                     })

#             # --- NEW: Get all vendors for this project ---
#             project_vendors = Projectvendor.query.filter_by(project_id=project.project_id).all()
#             vendor_list = []
#             for pv in project_vendors:
#                 vendor = Vendors.query.get(pv.vendor_id)
#                 if vendor:
#                     vendor_list.append({
#                         "vendor_id": vendor.vendor_id,
#                         "company_name": vendor.company_name,
#                         "role": pv.role
#                     })

#             # --- NEW: Get all boards and pins for this project ---
#             project_boards = Boards.query.filter_by(project_id=project.project_id).all()
#             board_list = []
#             for board in project_boards:
#                 pins = Pin.query.filter_by(board_id=board.board_id).all()
#                 pin_list = []
#                 for pin in pins:
#                     pin_list.append({
#                         "pin_id": pin.pin_id,
#                         "pin_type": pin.pin_type,
#                         "content": pin.content,
#                         "position_x": pin.position_x,
#                         "position_y": pin.position_y
#                     })
                
#                 board_list.append({
#                     "board_id": board.board_id,
#                     "board_name": board.board_name,
#                     "board_description": board.board_description,
#                     "pins": pin_list
#                 })

#             # Combine all the data for this project
#             project_data = {
#                 "project_id": project.project_id,
#                 "project_name": project.project_name,
#                 "project_status": project.status,
#                 "assigned_client": client_info,
#                 "assigned_tasks": task_list,
#                 "assigned_templates": template_list,
#                 "assigned_vendors": vendor_list,
#                 "project_boards": board_list
#             }
#             dashboard_data.append(project_data)

#         return jsonify(dashboard_data), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

# The rest of your user_bp blueprint...

@user_bp.route('/dashboard/<string:user_id>', methods=['GET'])
def get_user_dashboard(user_id):
    try:
        # Get optional search parameters from the URL
        project_name_query = request.args.get('project_name')
        task_status_query = request.args.get('task_status')
        vendor_name_query = request.args.get('vendor_name')

        # Check if the user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

        # Start with a base query for the user's project assignments
        assignments_query = ProjectAssignments.query.filter_by(user_id=user_id)
        
        # Apply filters to the project assignments query if parameters are provided
        if project_name_query:
            # We need to join with the Projects table to filter by project name
            assignments_query = assignments_query.join(Projects).filter(
                Projects.project_name.ilike(f'%{project_name_query}%')
            )

        # Apply vendor filter
        if vendor_name_query:
            # Join with Projectvendor and Vendors to filter by vendor name
            assignments_query = assignments_query.join(Projectvendor).join(Vendors).filter(
                Vendors.company_name.ilike(f'%{vendor_name_query}%')
            )
            
        assignments = assignments_query.all()
        dashboard_data = []

        for assignment in assignments:
            project = Projects.query.get(assignment.project_id)
            if not project:
                continue

            # Your existing logic to get client, templates, etc.
            client_info = None
            client_assignment = ProjectAssignments.query.filter_by(
                project_id=project.project_id,
                role='client'
            ).first()
            if client_assignment:
                client = Clients.query.filter_by(user_id=client_assignment.user_id).first()
                if client:
                    client_info = {
                        "client_name": client.client_name,
                        "client_email": client.client_email,
                        "client_phone": client.client_phone
                    }

            # --- Apply task status filter here ---
            tasks_query = Tasks.query.filter_by(project_id=project.project_id)
            if task_status_query:
                tasks_query = tasks_query.filter(Tasks.status.ilike(f'%{task_status_query}%'))
            
            tasks = tasks_query.all()
            task_list = []
            for task in tasks:
                task_list.append({
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "status": task.status,
                    "due_date": task.due_date.isoformat(),
                    "priority": task.priority,
                    "assigned_to": task.assigned_to
                })

            # Existing logic for templates, vendors, boards, and pins
            project_templates = ProjectTemplates.query.filter_by(project_id=project.project_id).all()
            template_list = []
            for pt in project_templates:
                template = Templates.query.get(pt.template_id)
                if template:
                    template_list.append({
                        "template_id": template.template_id,
                        "template_name": template.template_name,
                        "file_url": pt.template_file_url
                    })

            project_vendors = Projectvendor.query.filter_by(project_id=project.project_id).all()
            vendor_list = []
            for pv in project_vendors:
                vendor = Vendors.query.get(pv.vendor_id)
                if vendor:
                    vendor_list.append({
                        "vendor_id": vendor.vendor_id,
                        "company_name": vendor.company_name,
                        "role": pv.role
                    })

            project_boards = Boards.query.filter_by(project_id=project.project_id).all()
            board_list = []
            for board in project_boards:
                pins = Pin.query.filter_by(board_id=board.board_id).all()
                pin_list = []
                for pin in pins:
                    pin_list.append({
                        "pin_id": pin.pin_id,
                        "pin_type": pin.pin_type,
                        "content": pin.content,
                        "position_x": pin.position_x,
                        "position_y": pin.position_y
                    })
                
                board_list.append({
                    "board_id": board.board_id,
                    "board_name": board.board_name,
                    "board_description": board.board_description,
                    "pins": pin_list
                })

            project_data = {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "project_status": project.status,
                "assigned_client": client_info,
                "assigned_tasks": task_list,
                "assigned_templates": template_list,
                "assigned_vendors": vendor_list,
                "project_boards": board_list
            }
            dashboard_data.append(project_data)

        return jsonify(dashboard_data), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@user_bp.route('/verify_registration_otp', methods=['POST'])
def verify_registration_otp():
    data = request.json
    user_email = data.get("user_email")
    otp_code = data.get("otp_code")

    if not all([user_email, otp_code]):
        return jsonify({"message": "Email and OTP code are required"}), 400

    user = User.query.filter_by(user_email=user_email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Find the valid, unused, and unexpired OTP for this user and type
    otp_record = OtpCode.query.filter(
        OtpCode.user_id == user.user_id,
        OtpCode.otp_code == otp_code,
        OtpCode.expires_at > datetime.now(),
        OtpCode.is_used == False,
        OtpCode.type == 'registration'
    ).order_by(OtpCode.created_at.desc()).first()

    if otp_record:
        # Mark OTP as used
        otp_record.is_used = True
        db.session.commit()

        # You might want to 'activate' the user here if you have an 'is_active' column
        # user.is_active = True 
        # db.session.commit()

        # Generate access token
        access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(days=1))
        
        # Send confirmation email
        send_email(
            recipients=[user_email],
            subject="Registration Successful!",
            body=f"Hello {user.user_name},\n\nYour account has been successfully verified and registered."
        )

        return jsonify({
            "message": "Registration complete and OTP verified. Login successful.",
            "access_token": access_token,
            "user_id": user.user_id
        }), 200
    else:
        # Increment attempt counter (optional, for brute-force protection)
        failed_otp = OtpCode.query.filter(
            OtpCode.user_id == user.user_id,
            OtpCode.otp_code == otp_code,
            OtpCode.type == 'user_registration'
        ).first()
        if failed_otp:
            failed_otp.attempts += 1
            db.session.commit()
            
        return jsonify({"message": "Invalid, expired, or used OTP code."}), 401

# --- NEW: OTP Verification for Login ---
@user_bp.route('/verify_login_otp', methods=['POST'])
def verify_login_otp():
    data = request.json
    user_email = data.get("user_email")
    otp_code = data.get("otp_code")

    if not all([user_email, otp_code]):
        return jsonify({"message": "Email and OTP code are required"}), 400

    user = User.query.filter_by(user_email=user_email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Find the valid, unused, and unexpired OTP for this user and type
    otp_record = OtpCode.query.filter(
        OtpCode.user_id == user.user_id,
        OtpCode.otp_code == otp_code,
        OtpCode.expires_at > datetime.now(),
        OtpCode.is_used == False,
        OtpCode.type == 'login'
    ).order_by(OtpCode.created_at.desc()).first()

    if otp_record:
        # Mark OTP as used
        otp_record.is_used = True
        db.session.commit()
        
        # Generate access token
        access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(days=1))
        
        # Send confirmation email
        send_email(
            recipients=[user_email],
            subject="Successful Login Notification",
            body=f"Hello {user.user_name},\n\nYour login attempt at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} was successful."
        )

        return jsonify({
            "message": "Login successful.",
            "access_token": access_token,
            "user_id": user.user_id
        }), 200
    else:
        # Increment attempt counter (optional, for brute-force protection)
        failed_otp = OtpCode.query.filter(
            OtpCode.user_id == user.user_id,
            OtpCode.otp_code == otp_code,
            OtpCode.type == 'user_login'
        ).first()
        if failed_otp:
            failed_otp.attempts += 1
            db.session.commit()
            
        return jsonify({"message": "Invalid, expired, or used OTP code."}), 401