from flask import Blueprint , jsonify , request
from models import Vendors , db , User , OtpCode , Vendors , Projectvendor
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
from flask_cors import cross_origin
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
    """
    Creates a new single vendor record (Global).
    ---
    tags:
      - Vendors - CRUD
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - company_name
            - contact_person
            - vendor_email
          properties:
            company_name: {type: string}
            contact_person: {type: string}
            vendor_email: {type: string, format: email}
            trade: {type: string}
            contact_number: {type: string}
            tags: {type: string, description: Comma-separated tags}
    responses:
      201:
        description: Vendor created successfully.
      500:
        description: Internal server error.
    """
    data = request.json
    vendor_email = data.get('vendor_email')
    space_id = getattr(Vendors, 'space_id', None)  # Default to None for global vendors

    if not vendor_email:
        return jsonify({'error': 'vendor_email is a required field.'}), 400
    # required_fields = ['contact_number' , 'contact_person' , 'company_name' , 'vendor_email' , 'trade']

    existing_vendor = Vendors.query.filter_by(vendor_email=vendor_email , space_id=space_id).first()
    if existing_vendor:
        # If the email exists, check if it's a global entry (space_id is null/None).
        # We assume if the user is using the /vendors route, they intend to create a global record (space_id=None).
        # The database unique constraint is failing because the email already exists somewhere.
        return jsonify({
            "error": f"Vendor with email '{vendor_email}' already exists globally or is registered."
        }), 409
    
    # 1. Check if all required fields are present outside the loop
    # if not all(field in data for field in required_fields):
    # return jsonify({'error': 'All fields are required'}), 400
        
    try:
        # 2. Instantiate the Vendors model with keyword arguments
        new_vendor = Vendors(
            company_name=data.get('company_name'),
            contact_person=data.get('contact_person'),
            # vendor_email=data.get('vendor_email'),
            # trade=data.get('trade'),
            contact_number = data.get('contact_number'),
            tags = data.get('tags'),
            # space_id =  getattr(Vendors, 'space_id', None)  # Optional: Include space_id if provided
            # project_id = data.get('project_id')  # Optional: Include project_id if provided 
        )
        
        # 3. Add and commit the new vendor to the database
        db.session.add(new_vendor)
        db.session.commit()
        
        return jsonify({'message': 'Vendor created successfully'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@vendors_bp.route('/vendors/post/space/<string:space_id>', methods=['POST'])
def create_vendor_for_space(space_id):
    """
    Creates a new vendor associated with a specific space.
    ---
    tags:
      - Vendors - Space Management
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
        description: ID of the space to link the vendor to.
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - vendor_email
          properties:
            company_name: {type: string}
            contact_person: {type: string}
            vendor_email: {type: string, format: email}
            trade: {type: string}
            contact_number: {type: string}
            tags: {type: string, description: Comma-separated tags}
    responses:
      201:
        description: Vendor created successfully and linked to space.
      400:
        description: Missing required field (vendor_email).
      409:
        description: Vendor with that email already exists in the space.
      500:
        description: Internal server error.
    """
    # 1. Get the JSON data from the request body
    data = request.json
    
    # 2. Extract the required vendor email
    vendor_email = data.get('vendor_email') 

    # --- INPUT VALIDATION ---
    if not vendor_email:
        return jsonify({"error": "vendor_email is a required field."}), 400

    # 3. Check for Existing Vendor (using email and space_id for multi-tenant check)
    # This check ensures that the SAME email is not used for a vendor within the SAME space.
    # If the email must be globally unique across ALL spaces, remove the 'space_id' filter.
    existing_vendor = Vendors.query.filter_by(
        vendor_email=vendor_email, 
        space_id=space_id
    ).first()

    if existing_vendor:
        # Return a 409 Conflict status code
        return jsonify({
            "error": f"Vendor with email '{vendor_email}' already exists in space '{space_id}'."
        }), 409

    # --- DATABASE INSERTION ---
    try:
        # 4. Instantiate the Vendors model
        new_vendor = Vendors(
            company_name=data.get('company_name'),
            contact_person=data.get('contact_person'),
            vendor_email=vendor_email,  
            trade=data.get('trade'),
            contact_number = data.get('contact_number'),
            tags = data.get('tags'),
            # *** KEY ADDITION: Assign the space_id from the URL ***
            space_id=space_id
        )
        
        # 5. Add and commit the new vendor to the database
        db.session.add(new_vendor)
        db.session.commit()
        
        return jsonify({'message': 'Vendor created successfully', 'vendor_id': new_vendor.vendor_id}), 201
        
    except Exception as e:
        db.session.rollback()
        # Log the error for debugging purposes (optional but recommended)
        print(f"Vendor creation error: {e}") 
        # Return a 500 for general server/database errors
        return jsonify({'error': 'An internal server error occurred during vendor creation.'}), 500

#get all vendors    
@vendors_bp.route('/vendors', methods=['GET'])
def get_all_vendors():
    """
    Retrieves all vendors with pagination.
    ---
    tags:
      - Vendors - CRUD
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 10
    responses:
      200:
        description: A list of vendor records.
        schema:
          type: object
          properties:
            vendors:
              type: array
              items:
                type: object
                properties:
                  vendor_id: {type: string}
                  company_name: {type: string}
                  vendor_email: {type: string, format: email}
            total_vendors: {type: integer}
            total_pages: {type: integer}
            current_page: {type: integer}
            has_next: {type: boolean}
            has_prev: {type: boolean}
      500:
        description: Internal server error.
    """
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
                # 'trade': vendor.trade,
                'contact_number':vendor.contact_number,
                'tags' : vendor.tags.split(',') if vendor.tags else []
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
    """
    Retrieves a single vendor by its ID.
    ---
    tags:
      - Vendors - CRUD
    parameters:
      - name: vendor_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Vendor details.
        schema:
          type: object
          properties:
            vendor_id: {type: string}
            company_name: {type: string}
            vendor_email: {type: string, format: email}
      404:
        description: Vendor not found.
    """
    vendor = Vendors.query.get_or_404(vendor_id)
    if not vendor:
        return jsonify({"message":"Vendor not found"}) , 404
    result = {
        'vendor_id':vendor.vendor_id , 
        'company_name': vendor.company_name,
        'contact_person': vendor.contact_person,
        'vendor_email': vendor.vendor_email,
        # 'trade': vendor.trade,
        'contact_number':vendor.contact_number,
        'tags' : vendor.tags.split(',') if vendor.tags else []
    }
    return jsonify(result) , 200

@vendors_bp.route('/vendors/space/<string:space_id>', methods=['GET'])
def get_vendors_by_space_id(space_id):
    """
    Retrieves all vendors associated with a specific space_id.
    ---
    tags:
      - Vendors - Space Management
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of vendors for the space.
      404:
        description: No vendors found for that space ID.
      500:
        description: Internal server error.
    """
    # """
    # Retrieves all vendors associated with a specific space_id.
    # """
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
                # 'trade': vendor.trade,
                'tags': vendor.tags.split(',') if vendor.tags else []
                # Add other vendor fields here
            }
            all_vendors_data.append(vendor_dict)

        return jsonify(all_vendors_data), 200

    except Exception as e:
        # logger.error(f"Error retrieving vendors for space ID {space_id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred."}), 500

#update vendor by id
@vendors_bp.route('/vendors/<string:vendor_id>', methods=['PUT'])
@cross_origin()
def update_vendor(vendor_id):

    """
    Updates all fields of an existing vendor by ID (PUT).
    ---
    tags:
      - Vendors - CRUD
    parameters:
      - name: vendor_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            company_name: {type: string}
            contact_person: {type: string}
            vendor_email: {type: string, format: email}
            trade: {type: string}
            contact_number: {type: string}
            tags: {type: string, description: Comma-separated tags}
    responses:
      200:
        description: Vendor updated successfully.
      404:
        description: Vendor not found.
    """
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
    # if 'trade' in data:
        # vendor.trade = data['trade']
    if 'contact_number' in data:
        vendor.contact_number = data['contact_number']
    if 'tags' in data:
        vendor.tags = data['tags']
    db.session.commit()
    response_data = {
        'message' : 'Vendor updated successfully',
        'vendor' : {
            'vendor_id' : vendor.vendor_id,
            'company_name' : vendor.company_name,
            'contact_person' : vendor.contact_person,
            'vendor_email' : vendor.vendor_email,
            # 'trade' : vendor.trade,
            'contact_number' : vendor.contact_number,
            'tags' : vendor.tags
        }
    }
    return jsonify( response_data) , 200

@vendors_bp.route('/vendors/space/<string:space_id>', methods=['PUT'])
@cross_origin()
def update_vendor_by_space_id(space_id):
    """
    Updates a vendor identified by vendor_id within a specific space (PUT).
    ---
    tags:
      - Vendors - Space Management
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [vendor_id]
          properties:
            vendor_id: {type: string, description: ID of the vendor to update.}
            company_name: {type: string}
            contact_person: {type: string}
            vendor_email: {type: string, format: email}
            trade: {type: string}
            contact_number: {type: string}
            tags: {type: string, description: Comma-separated tags}
    responses:
      200:
        description: Vendor updated successfully within the space.
      400:
        description: Missing vendor_id in body.
      404:
        description: Vendor ID not found in the specified space ID.
      500:
        description: Internal server error.
    """
    # """
    # Updates a single vendor that belongs to the given space_id.
    # Requires 'vendor_id' in the JSON body to identify which vendor to update.
    # """
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
        # if 'trade' in data:
            # vendor.trade = data['trade']
        if 'tags' in data:
            vendor.tags = data['tags']
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
    """
    Deletes a vendor by ID, including related Projectvendor entries.
    ---
    tags:
      - Vendors - CRUD
    parameters:
      - name: vendor_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Vendor deleted successfully.
      404:
        description: Vendor not found.
      500:
        description: Internal server error.
    """
    vendor = Vendors.query.get_or_404(vendor_id)
    if not vendor:
        return jsonify({"message":"Vendor not found"}) , 404
    try:
        db.session.query(Projectvendor).filter(Projectvendor.vendor_id == vendor_id).delete(synchronize_session='fetch')
        db.session.delete(vendor)
        db.session.commit()
        return jsonify({"message" : "Vendor deleted successfully!!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@vendors_bp.route('/vendors/space/<string:space_id>', methods=['DELETE'])
def delete_vendor_by_space_id(space_id):
    """
    Deletes a vendor identified by vendor_id within a specific space.
    ---
    tags:
      - Vendors - Space Management
    parameters:
      - name: space_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [vendor_id]
          properties:
            vendor_id: {type: string, description: ID of the vendor to delete.}
    responses:
      200:
        description: Vendor deleted successfully from the space.
      400:
        description: Missing vendor_id in body.
      404:
        description: Vendor ID not found in the specified space ID.
      500:
        description: Internal server error.
    """
    # """
    # Deletes a single vendor that belongs to the given space_id.
    # Requires 'vendor_id' in the JSON body to identify which vendor to delete.
    # """
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
    """
    Registers a new vendor and sends an OTP for verification.
    ---
    tags:
      - Vendors - Auth & OTP
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [company_name, contact_person, vendor_email, trade, vendor_password]
          properties:
            company_name: {type: string}
            contact_person: {type: string}
            vendor_email: {type: string, format: email}
            trade: {type: string}
            vendor_password: {type: string, format: password}
    responses:
      201:
        description: Registration successful, check email for OTP.
      400:
        description: Missing required fields.
      409:
        description: Vendor with this email already exists.
      500:
        description: Internal server error (database or email issue).
    """
    data = request.json
    required_fields = ['company_name', 'contact_person', 'vendor_email',  'vendor_password']

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
            # trade=data['trade'],
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
    """
    Verifies a newly registered vendor using the sent OTP code.
    ---
    tags:
      - Vendors - Auth & OTP
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [vendor_email, otp_code]
          properties:
            vendor_email: {type: string, format: email}
            otp_code: {type: string}
    responses:
      200:
        description: Registration verified successfully.
      400:
        description: Missing email or OTP code.
      401:
        description: Invalid, expired, or used OTP code.
      404:
        description: User not found.
    """
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
    """
    Authenticates vendor credentials and sends an OTP for 2FA login.
    ---
    tags:
      - Vendors - Auth & OTP
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [vendor_email, vendor_password]
          properties:
            vendor_email: {type: string, format: email}
            vendor_password: {type: string, format: password}
    responses:
      200:
        description: Credentials correct, OTP sent to email.
      400:
        description: Missing email or password.
      401:
        description: Invalid email or password.
      403:
        description: Account not verified.
      500:
        description: Internal server error during OTP generation/email send.
    """
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
    """
    Verifies the login OTP and grants an access token upon success.
    ---
    tags:
      - Vendors - Auth & OTP
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required: [vendor_email, otp_code]
          properties:
            vendor_email: {type: string, format: email}
            otp_code: {type: string}
    responses:
      200:
        description: Login successful, returns access token.
        schema:
          type: object
          properties:
            message: {type: string}
            access_token: {type: string}
            user_id: {type: integer}
      400:
        description: Missing email or OTP code.
      401:
        description: Invalid, expired, or used OTP code.
      404:
        description: User not found.
      500:
        description: Internal server error during token generation or final commit.
    """
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
    """
    Partially updates fields of an existing vendor by ID (PATCH).
    ---
    tags:
      - Vendors - CRUD
    parameters:
      - name: vendor_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            company_name: {type: string}
            contact_person: {type: string}
            contact_number: {type: string}
            vendor_email: {type: string, format: email}
            trade: {type: string}
            tags: {type: string, description: Comma-separated tags}
    responses:
      200:
        description: Vendor partially updated successfully.
      400:
        description: No valid fields provided to update.
      404:
        description: Vendor not found.
      500:
        description: Internal server error.
    """
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


# =========================================================================
# NEW: Search Vendor by Contact Number
# =========================================================================
# @vendors_bp.route('/vendors/search/contact_number', methods=['GET'])
# def search_vendor_by_contact_number():
#     """
#     Retrieves a single vendor by their contact number.
#     ---
#     tags:
#       - Vendors - CRUD
#     parameters:
#       - name: contact_number
#         in: query
#         type: string
#         required: true
#         description: The full contact number of the vendor to retrieve.
#     responses:
#       200:
#         description: Vendor details retrieved successfully.
#         schema:
#           type: object
#           properties:
#             vendor_id: {type: string}
#             company_name: {type: string}
#             vendor_email: {type: string, format: email}
#             contact_number: {type: string}
#             tags: {type: array, items: {type: string}}
#       404:
#         description: Vendor not found with the provided contact number.
#       500:
#         description: Internal server error.
#     """
#     # Get the contact_number from the query parameters
#     contact_number = request.args.get('contact_number')

#     if not contact_number:
#         return jsonify({"error": "The 'contact_number' query parameter is required."}), 400

#     try:
#         # Query the database for a vendor matching the contact_number
#         vendor = Vendors.query.filter_by(contact_number=contact_number).first()

#         if not vendor:
#             return jsonify({"message": f"Vendor not found with contact number: {contact_number}"}), 404
        
#         # Prepare the response data (similar to get_vendor_by_id)
#         result = {
#             'vendor_id': vendor.vendor_id,
#             'company_name': vendor.company_name,
#             'contact_person': vendor.contact_person,
#             'vendor_email': vendor.vendor_email,
#             'contact_number': vendor.contact_number,
#             'tags': vendor.tags.split(',') if vendor.tags else []
#         }
        
#         return jsonify(result), 200

#     except Exception as e:
#         # Log the error for debugging
#         logging.error(f"Error searching vendor by contact number: {e}", exc_info=True)
#         return jsonify({"error": "An unexpected server error occurred during search."}), 500


# =========================================================================
# MODIFIED: Search Vendor by Contact Number (Now supports partial/prefix search)
# =========================================================================
@vendors_bp.route('/vendors/search/contact_number', methods=['GET'])
def search_vendor_by_contact_number():
    """
    Retrieves vendors by matching the starting digits (prefix) of their contact number.
    ---
    tags:
      - Vendors - CRUD
    parameters:
      - name: contact_number
        in: query
        type: string
        required: true
        description: A partial or full contact number (e.g., '555' will find '5551234567').
    responses:
      200:
        description: List of vendor details matching the prefix.
        schema:
          type: array
          items:
            type: object
            # ... (properties remain the same)
      404:
        description: No vendors found matching the provided contact number prefix.
      500:
        description: Internal server error.
    """
    # Get the contact_number from the query parameters
    contact_number_prefix = request.args.get('contact_number')

    if not contact_number_prefix:
        return jsonify({"error": "The 'contact_number' query parameter is required."}), 400

    try:
        # --- KEY CHANGE: Use .like() with the SQL wildcard '%' ---
        # This will search for any number that starts with the provided prefix.
        search_term = f"{contact_number_prefix}%"
        
        # We use .filter() for more complex LIKE queries and .all() to get multiple potential matches
        vendors = Vendors.query.filter(
            Vendors.contact_number.like(search_term)
        ).all()
        
        if not vendors:
            return jsonify({"message": f"No vendors found with contact number starting with: {contact_number_prefix}"}), 404
        
        # Prepare the response data (must be a list since we expect multiple results)
        results = []
        for vendor in vendors:
            results.append({
                'vendor_id': vendor.vendor_id,
                'company_name': vendor.company_name,
                'contact_person': vendor.contact_person,
                'vendor_email': vendor.vendor_email,
                'contact_number': vendor.contact_number,
                'tags': vendor.tags.split(',') if vendor.tags else []
            })
        
        return jsonify(results), 200

    except Exception as e:
        # Log the error for debugging
        logging.error(f"Error searching vendor by contact number prefix: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred during search."}), 500