from flask import Flask, request, jsonify , Blueprint
from flask_sqlalchemy import SQLAlchemy
from models import db , Bill
from datetime import datetime
import uuid
from models import db , Bill
from decimal import Decimal

# Initialize Flask App and SQLAlchemy (placeholders)
app = Flask(__name__)
# db = SQLAlchemy(app) # Assume db is initialized elsewhere

# --- Utility Function Placeholder ---
def generate_uuid():
    """Generates a standard UUID-4 string."""
    return str(uuid.uuid4())

bills_bp = Blueprint("Bill" , __name__)


# --- Placeholder Bill Model (Replace with your actual Bill class if needed) ---
class Bill(db.Model):
    __tablename__ = 'bills'
    bill_id = db.Column(db.String(50), primary_key=True, default=generate_uuid, nullable=False)
    vendor_id = db.Column(db.String(36), db.ForeignKey('vendors.vendor_id'), nullable=False)
    project_id = db.Column(db.String(36), db.ForeignKey('projects.project_id'), nullable=True)
    vendor_invoice_ref = db.Column(db.String(100), unique=True, nullable=False)
    received_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    due_date = db.Column(db.Date, nullable=False)
    total_owed = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending Payment')
    # Relationships are assumed to link correctly

    def to_dict(self):
        """Converts the Bill object to a dictionary for JSON serialization."""
        return {
            'bill_id': self.bill_id,
            'vendor_id': self.vendor_id,
            'project_id': self.project_id,
            'vendor_invoice_ref': self.vendor_invoice_ref,
            # Convert Date objects to ISO format strings
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'total_owed': str(self.total_owed), # Convert Decimal to string
            'status': self.status
        }
    
@bills_bp.route('/api/bills', methods=['POST'])
def create_bill():
    data = request.get_json()

    # Basic validation for required fields
    required_fields = ['vendor_id', 'vendor_invoice_ref', 'due_date', 'total_owed']
    if not all(k in data for k in required_fields):
        return jsonify({"message": f"Missing required fields: {', '.join(required_fields)}"}), 400

    try:
        new_bill = Bill(
            vendor_id=data['vendor_id'],
            project_id=data.get('project_id'),
            vendor_invoice_ref=data['vendor_invoice_ref'],
            # Dates from ISO string or use default
            received_date=datetime.fromisoformat(data['received_date']).date() if 'received_date' in data else None,
            due_date=datetime.fromisoformat(data['due_date']).date(),
            total_owed=Decimal(str(data['total_owed'])),
            status=data.get('status', 'Pending Payment')
        )

        db.session.add(new_bill)
        db.session.commit()
        return jsonify(new_bill.to_dict()), 201 # 201 Created

    except Exception as e:
        db.session.rollback()
        # Catches unique constraint violations (e.g., vendor_invoice_ref) and other DB errors
        return jsonify({"message": "Failed to create bill", "error": str(e)}), 400
    
@bills_bp.route('/api/bills', methods=['GET'])
def get_all_bills():
    bills = Bill.query.all()
    # Serialize the list of objects
    return jsonify([bill.to_dict() for bill in bills]), 200

@app.route('/api/bills/<string:bill_id>', methods=['GET'])
def get_bill_by_id(bill_id):
    bill = Bill.query.get(bill_id)

    if bill is None:
        return jsonify({"message": f"Bill with ID {bill_id} not found"}), 404

    return jsonify(bill.to_dict()), 200

@bills_bp.route('/api/bills/<string:bill_id>', methods=['PUT'])
def update_bill(bill_id):
    data = request.get_json()
    bill = Bill.query.get(bill_id)

    if bill is None:
        return jsonify({"message": f"Bill with ID {bill_id} not found"}), 404

    try:
        # Update fields if they are provided in the data
        if 'vendor_id' in data:
            bill.vendor_id = data['vendor_id']
        if 'project_id' in data:
            bill.project_id = data['project_id']
        if 'vendor_invoice_ref' in data:
            bill.vendor_invoice_ref = data['vendor_invoice_ref']
        if 'received_date' in data:
            bill.received_date = datetime.fromisoformat(data['received_date']).date()
        if 'due_date' in data:
            bill.due_date = datetime.fromisoformat(data['due_date']).date()
        if 'total_owed' in data:
            bill.total_owed = Decimal(str(data['total_owed']))
        if 'status' in data:
            bill.status = data['status']

        db.session.commit()
        return jsonify(bill.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update bill", "error": str(e)}), 400
    
@bills_bp.route('/api/bills/<string:bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    bill = Bill.query.get(bill_id)

    if bill is None:
        return jsonify({"message": f"Bill with ID {bill_id} not found"}), 404

    try:
        db.session.delete(bill)
        db.session.commit()
        # 204 No Content is standard for a successful DELETE
        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete bill", "error": str(e)}), 500
    
