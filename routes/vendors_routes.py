from flask import Blueprint , jsonify , request
from models import Vendors , db , User , OtpCode , Vendors
from flask_jwt_extended import create_access_token , get_jwt_identity , jwt_required 
from datetime import datetime , timezone , timedelta
from werkzeug.security import generate_password_hash , check_password_hash
import random
import datetime
import uuid
from email.message import EmailMessage
import os
import smtplib
from flask_cors import CORS
import logging

vendors_bp = Blueprint('vendors', __name__)
CORS(vendors_bp)

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
    required_fields = ['company_name' , 'contact_person' ,'vendor_email' , 'trade', 'contact_number']
    
    # 1. Check if all required fields are present outside the loop
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'All fields are required'}), 400
        
    try:
        # 2. Instantiate the Vendors model with keyword arguments
        new_vendor = Vendors(
            company_name=data['company_name'],
            contact_person=data['contact_person'],
            vendor_email=data['vendor_email'],
            trade=data['trade'],
            contact_number = data['contact_number']
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
                'trade': vendor.trade,
                'contact_number':vendor.contact_number
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
        'trade': vendor.trade,
        'contact_number':vendor.contact_number
    }
    return jsonify(result) , 200

@vendors_bp.route('/vendors/space/<string:space_id>', methods=['GET'])
def get_vendors_by_space_id(space_id):
    """
    Retrieves all vendors associated with a specific space_id.
    """
    try:
        # 1. Query the Vendors table using the space_id
        vendors = Vendors.query.filter_by(space_id=space_id).all()
        
        if not vendors:
            # Return a 404 if no vendors are found for that space_id
            return jsonify({"message": f"No vendors found for space ID '{space_id}'"}), 404

        all_vendors_data = []
        for vendor in vendors:
            vendor_dict = {
                'vendor_id': vendor.vendor_id,
                'space_id': vendor.space_id,  # Assuming this field exists
                # 'vendor_name': vendor.vendor_name,  # Adjust fields based on your actual model
                'contact_person': vendor.contact_person,
                'contact_number': vendor.contact_number,
                'vendor_email': vendor.vendor_email,
                'company_name': vendor.company_name,
                'trade': vendor.trade,
                # Add other vendor fields here
            }
            all_vendors_data.append(vendor_dict)

        return jsonify(all_vendors_data), 200

    except Exception as e:
        # logger.error(f"Error retrieving vendors for space ID {space_id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred."}), 500

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
    if 'contact_number' in data:
        vendor.contact_number = data['contact_number']
    db.session.commit()
    return jsonify({'message': 'Vendor updated successfully'}), 200

@vendors_bp.route('/vendors/space/<string:space_id>', methods=['PUT'])
def update_vendor_by_space_id(space_id):
    """
    Updates a single vendor that belongs to the given space_id.
    Requires 'vendor_id' in the JSON body to identify which vendor to update.
    """
    data = request.get_json()
    vendor_id = data.get('vendor_id')

    if not vendor_id:
        return jsonify({"error": "vendor_id is required in the body to identify the vendor to update."}), 400

    try:
        # 1. Find the vendor by vendor_id AND space_id for security and correctness
        vendor = Vendors.query.filter_by(vendor_id=vendor_id, space_id=space_id).first_or_404(
            description=f"Vendor ID '{vendor_id}' not found in space ID '{space_id}'"
        )

        # 2. Update fields
        if 'copmany_name' in data:
            vendor.company_name = data['company_name']
        if 'contact_person' in data:
            vendor.contact_person = data['contact_person']
        if 'contact_number' in data:
            vendor.contact_number = data['contact_number']
        if 'vendor_email' in data:
            vendor.vendor_email = data['vendor_email']
        if 'trade' in data:
            vendor.trade = data['trade']
        # Add logic for other fields here...
        
        # Prevent updating the space_id via PUT if it's meant to be immutable
        # if 'space_id' in data: 
        #    vendor.space_id = data['space_id'] 

        # 3. Commit changes
        db.session.commit()
        return jsonify({'message': f'Vendor ID {vendor_id} in space {space_id} updated successfully'}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 404

    except Exception as e:
        db.session.rollback()
        # logger.error(f"Error updating vendor ID {vendor_id} in space {space_id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred."}), 500

#delete vendor by id
@vendors_bp.route('/del_vendors/<string:vendor_id>' , methods = ['DELETE'])
def delete_vendor(vendor_id):
    vendor = Vendors.query.get_or_404(vendor_id)
    if not vendor:
        return jsonify({"message":"Vendor not found"}) , 404
    db.session.delete(vendor)
    db.session.commit()
    return jsonify({"message" : "Vendor deleted successfully!!"})

@vendors_bp.route('/vendors/space/<string:space_id>', methods=['DELETE'])
def delete_vendor_by_space_id(space_id):
    """
    Deletes a single vendor that belongs to the given space_id.
    Requires 'vendor_id' in the JSON body to identify which vendor to delete.
    """
    data = request.get_json()
    vendor_id = data.get('vendor_id')

    if not vendor_id:
        return jsonify({"error": "vendor_id is required in the body to identify the vendor to delete."}), 400

    try:
        # 1. Find the vendor by vendor_id AND space_id for security and correctness
        vendor = Vendors.query.filter_by(vendor_id=vendor_id, space_id=space_id).first_or_404(
            description=f"Vendor ID '{vendor_id}' not found in space ID '{space_id}'"
        )

        # 2. Delete the vendor
        db.session.delete(vendor)
        db.session.commit()
        
        return jsonify({"message": f"Vendor ID {vendor_id} successfully deleted from space {space_id}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 404

    except Exception as e:
        db.session.rollback()
        # logger.error(f"Error deleting vendor ID {vendor_id} in space {space_id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred."}), 500


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
            access_token = create_access_token(identity=Vendors.vendor_id, expires_delta=timedelta(minutes=15))
            # refresh_tokens = create_refresh_tokens(identity = Vendors.vendor_id , expires_delta = timedelta(days = 7))
            
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
    
@vendors_bp.route('/patch/<string:vendor_id>' , methods = ['PATCH'])
def patch_vendor(vendor_id):
    data = request.json
    vendors = Vendors.query.get(vendor_id)
    if not vendors:
        return jsonify({"message":"Vendor not found"}) , 404
    
    try:
        updated_fields = []
        if 'company_name' in data:
            vendors.company_name = data['company_name']
            updated_fields.append('company_name')

        if 'contact_person' in data:
            vendors.contact_person = data['contact_person']
            updated_fields.append('contact_person')

        if 'contact_number' in data:
            vendors.contact_number = data['contact_number']
            updated_fields.append('contact_number')

        if 'vendor_email' in data:
            vendors.vendor_email = data['vendor_email']
            updated_fields.append('vendor_email')

        if 'trade' in data:
            vendors.trade = data['trade']
            updated_fields.append('trade')

        if not updated_fields:
            return jsonify({"message":"No valid fields provided to upgrade"}),400
        
        db.session.commit()
        return jsonify({
            'message': 'Vendor updated successfully (PATCH).',
            'updated_fields': updated_fields
        }), 200
        
    except Exception as e:
        db.session.rollback()
        # Log the error for debugging purposes
        print(f"Vendor PATCH error for ID {vendor_id}: {e}") 
        return jsonify({'error': 'An internal server error occurred during the update.'}), 500


