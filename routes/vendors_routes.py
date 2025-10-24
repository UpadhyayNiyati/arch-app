from flask import Blueprint , jsonify , request
from models import Vendors , db , User , OtpCode
from flask_jwt_extended import create_access_token , get_jwt_identity , jwt_required
from datetime import datetime , timezone , timedelta
from werkzeug.security import generate_password_hash , check_password_hash
import random
import datetime
import uuid
from email.message import EmailMessage
import os
import smtplib

vendors_bp = Blueprint('vendors', __name__)

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


# Add your route definitions here
@vendors_bp.route('/vendors', methods=['POST'])
def create_vendor():
    data = request.json
    required_fields = ['company_name' , 'contact_person' ,'vendor_email' , 'trade']
    
    # 1. Check if all required fields are present outside the loop
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'All fields are required'}), 400
        
    try:
        # 2. Instantiate the Vendors model with keyword arguments
        new_vendor = Vendors(
            company_name=data['company_name'],
            contact_person=data['contact_person'],
            vendor_email=data['vendor_email'],
            trade=data['trade']
        )
        
        # 3. Add and commit the new vendor to the database
        db.session.add(new_vendor)
        db.session.commit()
        
        return jsonify({'message': 'Vendor created successfully'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

#get all vendors    
@vendors_bp.route('/vendors', methods=['GET'])
def get_all_vendors():
    try:
        # vendors = Vendors.query.all()
        # result = []
        # for vendor in vendors:
        #     result.append({
        #         'vendor_id':vendor.vendor_id , 
        #         'company_name': vendor.company_name,
        #         'contact_person': vendor.contact_person,
        #         'vendor_email': vendor.vendor_email,
        #         'trade': vendor.trade
        #     })
        page = request.args.get('page' , 1 , type = int)
        per_page = request.args.get('per_page' , 10 , type = int)
        vendors_pagination = Vendors.query.paginate(page = page , per_page = per_page , error_out = False)
        vendors = vendors_pagination.items

        result = []
        for vendor in vendors:
            result.append({
                'vendor_id': vendor.vendor_id,
                'company_name': vendor.company_name,
                'contact_person': vendor.contact_person,
                'vendor_email': vendor.vendor_email,
                'trade': vendor.trade
            })

        return jsonify({
            'vendors': result,
            'total_vendors': vendors_pagination.total,
            'total_pages': vendors_pagination.pages,
            'current_page': vendors_pagination.page,
            'has_next': vendors_pagination.has_next,
            'has_prev': vendors_pagination.has_prev
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#get single vendor by id
@vendors_bp.route('/vendors/<string:vendor_id>', methods=['GET'])
def get_vendor_by_id(vendor_id):
    vendor = Vendors.query.get_or_404(vendor_id)
    if not vendor:
        return jsonify({"message":"Vendor not found"}) , 404
    result = {
        'vendor_id':vendor.vendor_id , 
        'company_name': vendor.company_name,
        'contact_person': vendor.contact_person,
        'vendor_email': vendor.vendor_email,
        'trade': vendor.trade
    }
    return jsonify(result) , 200

#update vendor by id
@vendors_bp.route('/vendors/<string:vendor_id>', methods=['PUT'])
def update_vendor(vendor_id):
    data = request.json
    vendor = Vendors.query.get_or_404(vendor_id)
    if not vendor:
        return jsonify({"message":"Vendor not found"}) , 404
    if 'company_name' in data:
        vendor.company_name = data['company_name'] 
    if 'contact_person' in data:
        vendor.contact_person = data['contact_person']
    if 'vendor_email' in data:
        vendor.vendor_email = data['vendor_email']
    if 'trade' in data:
        vendor.trade = data['trade']
    db.session.commit()
    return jsonify({'message': 'Vendor updated successfully'}), 200

#delete vendor by id
@vendors_bp.route('/del_vendors/<string:vendor_id>' , methods = ['DELETE'])
def delete_vendor(vendor_id):
    vendor = Vendors.query.get_or_404(vendor_id)
    if not vendor:
        return jsonify({"message":"Vendor not found"}) , 404
    db.session.delete(vendor)
    db.session.commit()
    return jsonify({"message" : "Vendor deleted successfully!!"})


@vendors_bp.route('/register', methods=['POST'])
def register_vendor():
    data = request.json
    required_fields = ['company_name', 'contact_person', 'vendor_email', 'trade', 'vendor_password']

    if not all(field in data for field in required_fields):
        return jsonify({'error': 'All fields are required'}), 400

    # 1. Check for existing vendor profile
    existing_vendor = Vendors.query.filter_by(vendor_email=data['vendor_email']).first()
    if existing_vendor:
        return jsonify({"message": "A vendor with this email already exists"}), 409

    try:
        # Prepare data
        hashed_password = generate_password_hash(data['vendor_password'])
        
        # 2. Start Transaction: Create the User account first (for login)
        new_user = User(
            user_email=data['vendor_email'],
            user_password=hashed_password,
            is_verified=False # Set to False, pending OTP verification
        )
        db.session.add(new_user)
        
        # KEY STEP: Execute INSERT for User to get the auto-generated user_id
        db.session.flush()

        # 3. Create the Vendor profile, linking it to the new user_id
        new_vendor = Vendors(
            company_name=data['company_name'],
            contact_person=data['contact_person'],
            vendor_email=data['vendor_email'],
            trade=data['trade'],
            vendor_password=hashed_password, # Storing hash in vendor table per schema
            user_id=new_user.user_id 
        )
        db.session.add(new_vendor)
        
        # 4. Generate Registration OTP
        otp_code = str(random.randint(100000, 999999))
        # Use timezone-aware UTC datetime
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15) 
        
        new_otp = OtpCode(
            user_id=new_user.user_id,
            otp_code=otp_code,
            expires_at=expires_at,
            type='vendor_register' # OTP type for registration
        )
        db.session.add(new_otp)
        
        # Commit all records (User, Vendor, OTP) atomically
        db.session.commit()
        
        # 5. Send Email
        send_email(
            recipients=[data['vendor_email']],
            subject="Vendor Registration Verification",
            body=f"Hello {data['contact_person']},\n\nYour registration verification code is {otp_code}. Please verify your account to log in."
        )

        return jsonify({"message": "Vendor registered successfully. Please verify your email via OTP."}), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Vendor registration error: {e}")
        return jsonify({'error': 'An internal server error occurred during registration.'}), 500

# =========================================================================
# 2. NEW: VENDOR REGISTRATION VERIFICATION
# =========================================================================
@vendors_bp.route('/verify_register', methods=['POST'])
def verify_register_vendor():
    data = request.json
    user_email = data.get("vendor_email")
    otp_code = data.get("otp_code")

    if not all([user_email, otp_code]):
        return jsonify({"message": "Email and OTP code are required"}), 400

    user = User.query.filter_by(user_email=user_email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    current_time_utc = datetime.now(timezone.utc)

    # Find the valid, unused, unexpired OTP for registration
    otp_record = OtpCode.query.filter(
        OtpCode.user_id == user.user_id,
        OtpCode.otp_code == otp_code,
        OtpCode.expires_at > current_time_utc,
        OtpCode.is_used == False,
        OtpCode.type == 'vendor_register'
    ).first()

    if otp_record:
        # Mark OTP as used and verify the user account
        otp_record.is_used = True
        user.is_verified = True # Set the verification flag
        db.session.commit()
        
        return jsonify({"message": "Registration verified successfully. You can now log in."}), 200
    else:
        # Add detailed logging for debugging purposes
        print(f"REG_VERIFY_FAILED: User {user.user_id}. Invalid, expired, or used OTP code for 'vendor_register'.")
        return jsonify({"message": "Invalid, expired, or used OTP code."}), 401

# =========================================================================
# 3. NEW: VENDOR LOGIN (Password Check + OTP Generation)
# =========================================================================
@vendors_bp.route('/login', methods=['POST'])
def login_vendor():
    data = request.json
    vendor_email = data.get("vendor_email")
    vendor_password = data.get("vendor_password")
    
    if not all([vendor_email, vendor_password]):
        return jsonify({"message": "Email and password are required"}), 400
        
    user_account = User.query.filter_by(user_email=vendor_email).first()
    
    # 1. Check if user account exists and password is correct
    if user_account and check_password_hash(user_account.user_password, vendor_password):
        
        # 2. Check if the account is verified
        if not user_account.is_verified:
            return jsonify({"message": "Account not verified. Please verify your email first."}), 403

        try:
            # Delete old OTPs and generate new login OTP
            OtpCode.query.filter_by(user_id=user_account.user_id).delete()
            db.session.commit()
            
            otp_code = str(random.randint(100000, 999999))
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            
            new_otp = OtpCode(
                user_id=user_account.user_id,
                otp_code=otp_code,
                expires_at=expires_at,
                type='vendor_login' # OTP type for login
            )
            db.session.add(new_otp)
            db.session.commit()
            
            # Fetch vendor name for email greeting
            vendor_profile = Vendors.query.filter_by(user_id=user_account.user_id).first()
            vendor_name_to_use = vendor_profile.contact_person if vendor_profile else "Vendor"
            
            send_email(
                recipients=[vendor_email],
                subject="Login Verification OTP",
                body=f"Hello {vendor_name_to_use},\n\nYour login verification code is {otp_code}. It is valid for 5 minutes."
            )
            
            return jsonify({"message": "OTP sent for login verification. Please check your email."}), 200
        
        except Exception as e:
            db.session.rollback()
            print(f"Login OTP generation error: {e}") 
            return jsonify({"error": "An internal server error occurred during login."}), 500
            
    else:
        # User not found OR password check failed
        return jsonify({"message": "Invalid email or password"}), 401

# =========================================================================
# 4. NEW: VENDOR LOGIN VERIFICATION
# =========================================================================
@vendors_bp.route('/verify_login', methods=['POST'])
def verify_login_vendor():
    data = request.json
    user_email = data.get("vendor_email")
    otp_code = data.get("otp_code")

    if not all([user_email, otp_code]):
        return jsonify({"message": "Email and OTP code are required"}), 400

    user = User.query.filter_by(user_email=user_email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    current_time_utc = datetime.now(timezone.utc)

    # Find the valid, unused, and unexpired OTP for this user and type
    otp_record = OtpCode.query.filter(
        OtpCode.user_id == user.user_id,
        OtpCode.otp_code == otp_code,
        OtpCode.expires_at > current_time_utc,
        OtpCode.is_used == False,
        OtpCode.type == 'vendor_login' # Must match login route's type
    ).order_by(OtpCode.created_at.desc()).first()

    if otp_record:
        # Success path
        try:
            # Mark OTP as used
            otp_record.is_used = True
            db.session.commit()
            
            # Generate access token
            access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(days=1))
            
            # Fetch vendor profile for name
            vendor_profile = Vendors.query.filter_by(user_id=user.user_id).first()
            vendor_name_to_use = vendor_profile.contact_person if vendor_profile else "Vendor"

            # Send confirmation email
            send_email(
                recipients=[user_email],
                subject="Successful Vendor Login",
                body=f"Hello {vendor_name_to_use},\n\nYour login attempt at {current_time_utc.strftime('%Y-%m-%d %H:%M:%S')} (UTC) was successful."
            )

            return jsonify({
                "message": "Login successful.",
                "access_token": access_token,
                "user_id": user.user_id
            }), 200
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to finalize login (commit, token, or email): {e}")
            return jsonify({"error": "Login successful, but token generation or email failed."}), 500
            
    else:
        print(f"LOGIN_VERIFY_FAILED: User {user.user_id}. Invalid/expired/used OTP or type mismatch.")
        return jsonify({"message": "Invalid, expired, or used OTP code."}), 401

