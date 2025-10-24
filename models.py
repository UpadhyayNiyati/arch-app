#from sqlalchemy import SQLAlchemy
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

class User(db.Model):
    __tablename__  = 'user'
    user_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    user_name = db.Column(db.String(255) , nullable = False)
    user_email = db.Column(db.String(255) , unique = True , nullable =False)
    user_phone = db.Column(db.String(255) , nullable = False , unique = True)
    user_password = db.Column(db.String(255) , nullable = False)
    user_address = db.Column(db.String(255) , nullable = False)
    created_at = db.Column(db.DateTime , default = datetime.utcnow , nullable = True)
    user_roles = db.relationship('UserRole', backref='user', lazy=True, cascade='all, delete-orphan')


    team_memberships = db.relationship(
        'TeamMembership',  
        back_populates='member', 
        cascade='all, delete-orphan' # Cascades deletion from User to memberships
    )
class UserRole(db.Model):
    __tablename__ = 'user_roles'
    user_role_id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    # Correct the foreign key to match the primary key of the 'user' table
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    # The foreign key for 'roles' table is already correct
    role_id = db.Column(db.String(64), db.ForeignKey('roles.role_id'), nullable=False)

class Clients(db.Model):
    __tablename__ = 'clients'
    client_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    client_name = db.Column(db.String(255) , nullable = False)
    client_email = db.Column(db.String(255) , unique = True , nullable =False)
    client_phone = db.Column(db.String(255) , nullable = False , unique = True)
    client_address = db.Column(db.String(255) , nullable = False)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    client_password = db.Column(db.String(255), nullable=False) 


    # Optional: Define the relationship for easier querying
    user = db.relationship('User', backref=db.backref('clients', lazy=True))


class Vendors(db.Model):
    __tablename__ = 'vendors'
    vendor_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    company_name = db.Column(db.String(255) , nullable = False)
    contact_person = db.Column(db.String(255) , nullable = False)
    contact_number = db.Column(db.String(50), nullable=True) 
    vendor_email = db.Column(db.String(255) , unique = True , nullable =True)
    trade = db.Column(db.String(255) , nullable = False)

class Templates(db.Model):
    __tablename__ = 'templates'
    template_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    template_name = db.Column(db.String(255) , nullable = False)
    description = db.Column(db.Text , nullable = True)
    created_at = db.Column(db.DateTime , default = datetime.utcnow , nullable = True)
    # image_url = db.Column(db.String(300) , nullable = True)

class Projects(db.Model):
    __tablename__ = 'projects'
    project_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    project_name = db.Column(db.String(255) , nullable = False)
    site_area = db.Column(db.Float , nullable = False)
    location = db.Column(db.String(255) , nullable = False)
    budget = db.Column(db.Float , nullable = False)
    start_date = db.Column(db.Date , nullable = False)
    due_date = db.Column(db.Date , nullable = False)
    status = db.Column(db.String(50) , nullable = False)
    project_description = db.Column(db.Text, nullable=True)

    team_id = db.Column(db.String(50), db.ForeignKey('teams.team_id'), nullable=True) 
    client_id = db.Column(db.String(50), db.ForeignKey('clients.client_id'), nullable=False)

    client = db.relationship('Clients', backref=db.backref('projects_client', lazy=True))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)

class ProjectAssignments(db.Model):
    __tablename__ = 'project_assignments'
    assignment_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    project_id = db.Column(db.String(50) , db.ForeignKey('projects.project_id') , nullable = False)
    user_id = db.Column(db.String(50) , db.ForeignKey('user.user_id') , nullable = False)
    role = db.Column(db.String(100) , nullable = False)
    assigned_at = db.Column(db.DateTime , default = datetime.utcnow , nullable = True)   

class ProjectTemplates(db.Model):
    __tablename__ = 'project_templates'
    id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    project_id = db.Column(db.String(50) , db.ForeignKey('projects.project_id') , nullable = False)
    template_id = db.Column(db.String(50) , db.ForeignKey('templates.template_id') , nullable = False)   
    description = db.Column(db.Text , nullable = True)
    created_at = db.Column(db.DateTime , default = datetime.utcnow , nullable = True)
    template_name = db.Column(db.String(255), nullable=True)
    # template_file_url = db.Column(db.String(300), nullable=True)

class Tasks(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    project_id = db.Column(db.String(50) , db.ForeignKey('projects.project_id') , nullable =  False)
    task_name = db.Column(db.String(255) , nullable = False)
    description = db.Column(db.Text , nullable = True)
    status = db.Column(db.String(50) , nullable = False)
    estimated_hours = db.Column(db.Float , nullable = False)
    logged_hours = db.Column(db.Float , nullable = False , default = 0)
    due_date = db.Column(db.Date , nullable = False)
    completed_at = db.Column(db.DateTime , nullable = True)
    created_at = db.Column(db.DateTime , default = datetime.utcnow , nullable = True)
    priority = db.Column(db.String(50) , nullable = False)
    assigned_to = db.Column(db.String(50) , db.ForeignKey('user.user_id') , nullable = True)
    updated_at = db.Column(db.DateTime , default = datetime.utcnow , onupdate = datetime.utcnow , nullable = True)
    actual_hours = db.Column(db.Float , nullable = True)
     # Used to categorize the task (e.g., 'Construction', 'Meeting', 'Site Visit', 'Procurement')
    task_type = db.Column(db.String(50), nullable=True, default='General')
    location = db.Column(db.String(255), nullable=True) 
    #add this new column
    assigned_vendor = db.Column(db.String(50), db.ForeignKey('vendors.vendor_id'), nullable=True)
    assigned_team = db.Column(db.String(50), db.ForeignKey('teams.team_id'), nullable=True)

     # --- EXISTING FIELDS ---
    # requires_site_visit = db.Column(db.Boolean, nullable=True, default=False)
    space_id = db.Column(db.String(50), db.ForeignKey('spaces.space_id'), nullable=True)

class Projectvendor(db.Model):
    __tablename__ = 'project_vendor'
    project_vendor_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    project_id = db.Column(db.String(50) , db.ForeignKey('projects.project_id') , nullable = False)
    vendor_id = db.Column(db.String(50) , db.ForeignKey('vendors.vendor_id') , nullable = False)
    role = db.Column(db.String(50), nullable=True)
    assigned_date = db.Column(db.Date, default=datetime.today, nullable=True)

class Documents(db.Model):
    __tablename__ = 'documents'
    document_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    project_id = db.Column(db.String(50) , db.ForeignKey('projects.project_id') , nullable = False)
    file_name = db.Column(db.String(255) , nullable = False)
    # file_url = db.Column(db.String(300) , nullable = False)
    uploaded_at = db.Column(db.DateTime , default = datetime.utcnow , nullable = True)
    task_id = db.Column(db.String(50) , db.ForeignKey('tasks.task_id') , nullable = True)
    document_type = db.Column(db.String(50), nullable=True)
    named_by = db.Column(db.String(50) , db.ForeignKey('user.user_id') , nullable = True)

class OtpCode(db.Model):
    __tablename__ = 'otp_codes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64) , db.ForeignKey("user.user_id") , nullable=False , default = generate_uuid)
    otp_code = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, nullable=False, default=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    type = db.Column(db.String(50), nullable=True)

class Boards(db.Model):
    __tablename__ = 'boards'
    board_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    project_id = db.Column(db.String(64), db.ForeignKey('projects.project_id'), nullable=False)
    board_name = db.Column(db.String(255), nullable=False)
    board_description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # image_url = db.Column(db.String(300), nullable=True)

class Role(db.Model):
    __tablename__ = 'roles'
    role_id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    role_permissions = db.relationship('RolePermission', backref='role', lazy=True, cascade='all, delete-orphan')

class Permission(db.Model):
    __tablename__ = 'permissions'
    permission_id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    permission_name = db.Column(db.String(50), unique=True, nullable=False)
    permission_roles = db.relationship('RolePermission', backref='permission', lazy=True)

class RolePermission(db.Model):
    __tablename__ = 'role_permissions'
    role_permission_id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    role_id = db.Column(db.String(50), db.ForeignKey('roles.role_id'), nullable=False)
    permission_id = db.Column(db.String(50), db.ForeignKey('permissions.permission_id'), nullable=False)

class Pin(db.Model):
    __tablename__ = 'pins'
    pin_id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    board_id = db.Column(db.String(50), db.ForeignKey('boards.board_id'), nullable=False)
    pin_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    position_x = db.Column(db.Integer, nullable=True)
    position_y = db.Column(db.Integer, nullable=True)
    # created_by = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    #there will be images inside pin also

class Comment(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    pin_id = db.Column(db.String(50), db.ForeignKey('pins.pin_id'), nullable=True)
    board_id = db.Column(db.String(50), db.ForeignKey('boards.board_id'), nullable=False)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AssetLibrary(db.Model):
    __tablename__ = 'asset_library'
    asset_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    asset_name = db.Column(db.String(255), nullable=False)
    # asset_url = db.Column(db.String(300), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    uploaded_by = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tag(db.Model):
    __tablename__ = 'tags'
    tag_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    tag_name = db.Column(db.String(50), unique=True, nullable=False)

class PinTag(db.Model):
    __tablename__ = 'pin_tags'
    pin_id = db.Column(db.String(50), db.ForeignKey('pins.pin_id'), primary_key=True)
    tag_id = db.Column(db.String(50), db.ForeignKey('tags.tag_id'), primary_key=True)

class Notification(db.Model):
    __tablename__ = 'notifications'
    notification_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read_status = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    log_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    target_entity = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Spaces(db.Model):
    __tablename__ = "spaces"
    space_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    project_id = db.Column(db.String(50) , db.ForeignKey(Projects.project_id) , nullable = False)
    space_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    space_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="To Do")
    category = db.Column(db.String(100), nullable=True , default = "Custom")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)

class Drawings(db.Model):
    __tablename__ = "drawings"
    drawing_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    space_id = db.Column(db.String(50), db.ForeignKey('spaces.space_id'), nullable=False)
    drawing_name = db.Column(db.String(255), nullable=False)
    # drawing_url = db.Column(db.String(255), nullable=False)#only url will be updated if we put new drawing not name and revision_number 
    revision_number = db.Column(db.Integer, default=1, nullable=False)#allows to track every single change made to our file each new version gets a new number with new record
    uploaded_at = db.Column(db.TIMESTAMP, server_default=db.func.now(), nullable=False)

class Inspiration(db.Model):
    __tablename__ = "inspiration"
    
    inspiration_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)

    space_id = db.Column(db.String(50), db.ForeignKey('spaces.space_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    # url = db.Column(db.String(512), nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.String(255)) # Storing tags as a comma-separated string
    
    # Optional: A relationship to the Spaces table
    space = db.relationship('Spaces', backref=db.backref('inspirations', lazy=True))

class Upload_Files(db.Model):
    __tablename__ = "upload_files"
    file_id=db.Column(db.String(40),primary_key=True)
    filename=db.Column(db.String(255),nullable=False)
    file_path=db.Column(db.String(500),nullable=False)
    file_type=db.Column(db.String(255),nullable=True)
    created_at=db.Column(db.DateTime, default=datetime.utcnow)
    file_size=db.Column(db.String(150),nullable=False)
    board_id = db.Column(db.String(50), db.ForeignKey('boards.board_id'), nullable=True)
    template_id = db.Column(db.String(50), db.ForeignKey('templates.template_id'), nullable=True)
    project_templates_id = db.Column(db.String(50), db.ForeignKey('project_templates.id'), nullable=True)
    document_id = db.Column(db.String(50), db.ForeignKey('documents.document_id'), nullable=True)
    asset_id = db.Column(db.String(50), db.ForeignKey('asset_library.asset_id'), nullable=True)
    drawing_id = db.Column(db.String(50), db.ForeignKey('drawings.drawing_id'), nullable=True)
    inspiration_id = db.Column(db.String(50), db.ForeignKey('inspiration.inspiration_id'), nullable=True)
    space_id = db.Column(db.String(50), db.ForeignKey('spaces.space_id'), nullable=True)
    pin_id = db.Column(db.String(64), db.ForeignKey('pins.pin_id'), nullable = True)
    project_id = db.Column(db.String(50), db.ForeignKey('projects.project_id'), nullable = True) 
    task_id = db.Column(db.String(50) , db.ForeignKey('tasks.task_id') , nullable = True)

# --- NEW: Team Membership Association Table ---
# This table manages the Many-to-Many relationship between User and Teams.
class TeamMembership(db.Model):
    __tablename__ = 'team_members'
    membership_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)   
    team_id = db.Column(db.String(50), db.ForeignKey('teams.team_id'), nullable=False)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    team_role = db.Column(db.String(50), nullable=True) 
    contact_number = db.Column(db.String(50) , nullable = False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    team = db.relationship('Teams', back_populates='memberships')
    member = db.relationship('User', back_populates='team_memberships')
    


# --- NEW: Teams Model ---
class Teams(db.Model):
    __tablename__ = 'teams'
    
    # Core Team Columns
    team_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    team_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone_number = db.Column(db.String(45), nullable=True)
    # Link to the User who owns/leads the team
    owner_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=False)
    # Relationships
    # 1. Memberships (One-to-Many to the Association Object)
    memberships = db.relationship('TeamMembership', back_populates='team', cascade='all, delete-orphan')
    # 2. Owner (Many-to-One to User)
    owner = db.relationship('User', foreign_keys=[owner_id], backref=db.backref('owned_teams', lazy='dynamic'))
    # 3. Projects (One-to-Many, linked via Projects.team_id)
    projects_managed = db.relationship('Projects', backref='team_manager', lazy=True)


class Invoice(db.Model):
    __tablename__ = 'invoices'
    invoice_id = db.Column(db.String(36), primary_key=True, default=generate_uuid,nullable=False)
    client_id = db.Column(db.String(36), db.ForeignKey('clients.client_id'), nullable=False)
    project_id = db.Column(db.String(36), db.ForeignKey('projects.project_id'), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    due_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), nullable=False, default=0.00)
    # Current status (e.g., 'Draft', 'Sent', 'Paid', 'Overdue').
    status = db.Column(db.String(50), nullable=False, default='Draft')
    # Timestamp of creation.
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # --- Relationships (assuming Clients and Projects models exist) ---
    client = db.relationship('Clients', backref='invoices')
    project = db.relationship('Projects', backref='invoices')


class Payment(db.Model):
    __tablename__ = 'payments'
    # --- Primary Key (UUID) ---
    payment_id = db.Column(db.String(36), primary_key=True, default=generate_uuid,nullable=False)
    invoice_id = db.Column(db.String(36), db.ForeignKey('invoices.invoice_id'), nullable=False)
    # The date the payment was received/processed.
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # The amount of the payment (can be partial). Numeric(10, 2) for currency.
    amount_received = db.Column(db.Numeric(10, 2), nullable=False)
    # How the client paid (e.g., 'Bank Transfer', 'Credit Card').
    payment_method = db.Column(db.String(100), nullable=False)
    # External reference number (e.g., Stripe ID, check number).
    transaction_ref = db.Column(db.String(255), unique=True, nullable=True)
    # Establishes a link to the Invoice model.
    invoice = db.relationship('Invoice', backref='payments')

class Bill(db.Model):
    """
    SQLAlchemy model representing a Bill (vendor invoice) received by the firm.
    This tracks amounts owed to vendors, linked to a vendor and optionally a project.
    """
    __tablename__ = 'bills'
    bill_id = db.Column(db.String(50), primary_key=True, default=generate_uuid,nullable=False)
    # Links to the Vendor who sent the bill.
    vendor_id = db.Column(db.String(36), db.ForeignKey('vendors.vendor_id'), nullable=False)
    # Links to the Project this bill is associated with (can be nullable if for overhead/non-project costs).
    project_id = db.Column(db.String(36), db.ForeignKey('projects.project_id'), nullable=True)
    # The reference number given by the vendor (often unique or primary key for tracking).
    vendor_invoice_ref = db.Column(db.String(100), unique=True, nullable=False)
    # The date the bill was received by your firm.
    received_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    # The date the payment is owed to the vendor.
    due_date = db.Column(db.Date, nullable=False)
    # The total amount owed to the vendor. Numeric(10, 2) for currency.
    total_owed = db.Column(db.Numeric(10, 2), nullable=False)
    # Current status (e.g., 'Pending Payment', 'Paid', 'Disputed').
    status = db.Column(db.String(50), nullable=False, default='Pending Payment')
    # --- Relationships ---
    # Assuming Vendor and Project models exist.
    vendor = db.relationship('Vendors', backref='bills')
    project = db.relationship('Projects', backref='bills')

    # def __repr__(self):
        # return f"<Bill {self.vendor_invoice_ref} | Status: {self.status}>"



class VendorPayment(db.Model):
    """
    SQLAlchemy model representing a payment transaction made by the firm to a vendor.
    This links to a specific bill and the vendor that was paid.
    """
    __tablename__ = 'vendor_payments'
    vendor_payment_id = db.Column(db.String(36), primary_key=True, default=generate_uuid,nullable=False)
    bill_id = db.Column(db.String(36), db.ForeignKey('bills.bill_id'), nullable=False)
    vendor_id = db.Column(db.String(36), db.ForeignKey('vendors.vendor_id'), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    bill = db.relationship('Bill', backref='vendor_payments')
    vendor = db.relationship('Vendors', backref='payments_made')

    # def __repr__(self):
        # return f"<VendorPayment {self.vendor_payment_id} | Paid: ${self.amount_paid}>"

class Cards(db.Model):
    __tablename__ = 'cards'
    card_id = db.Column(db.String(50) , primary_key = True , default = generate_uuid)
    board_id = db.Column(db.String(50), db.ForeignKey('boards.board_id'), nullable=False)
    card_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='To Do')
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id'), nullable=True) # Assigned User
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    card_type = db.Column(db.String(50), nullable=True) # e.g., 'site', 'vendor', 'inspiration', 'note'


class TemplateCards(db.Model):
    __tablename__ = 'template_cards'
    
    # Primary Key
    template_card_id = db.Column(db.String(50), primary_key=True, default=generate_uuid)
    
    # Foreign Key to the parent template
    template_id = db.Column(db.String(50), db.ForeignKey('templates.template_id'), nullable=False)
    
    # Card Details (matching the structure of a real Card)
    card_name = db.Column(db.String(255), nullable=False) # e.g., 'Demolition Phase'
    description = db.Column(db.Text, nullable=True) # e.g., 'Remove existing cabinets, countertops...'
    
    # The 'Type' or 'Context' seen on the image (site, vendor, inspiration, note)
    card_type = db.Column(db.String(50), nullable=True) # e.g., 'site', 'vendor', 'inspiration', 'note'
    
    # Optional fields for default settings
    default_status = db.Column(db.String(50), default='To Do')
    sort_order = db.Column(db.Integer, nullable=True) # To maintain the order of cards

    # Relationship to Templates
    template = db.relationship('Templates', backref=db.backref('template_cards', lazy='dynamic'))


