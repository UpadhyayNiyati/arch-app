from flask import Flask, request, jsonify , Blueprint
from flask_sqlalchemy import SQLAlchemy
from models import db , VendorPayment
from datetime import datetime
import uuid
from decimal import Decimal

# --- Utility Function Placeholder ---
def generate_uuid():
    """Generates a standard UUID-4 string."""
    return str(uuid.uuid4())

vendor_payments_bp = Blueprint('VendorPayment' , __name__)


    # def to_dict(self):
    #     """Converts the VendorPayment object to a dictionary for JSON serialization."""
    #     return {
    #         'vendor_payment_id': self.vendor_payment_id,
    #         'bill_id': self.bill_id,
    #         'vendor_id': self.vendor_id,
    #         'payment_date': self.payment_date.isoformat(),
    #         'amount_paid': str(self.amount_paid), # Convert Decimal to string
    #         'payment_method': self.payment_method,
    #         'notes': self.notes
    #     }
    
@vendor_payments_bp.route('/post', methods=['POST'])
def create_vendor_payment():
    data = request.get_json()

    # Basic input validation for required fields
    if not all(k in data for k in ('bill_id', 'vendor_id', 'amount_paid', 'payment_method')):
        return jsonify({"message": "Missing required fields (bill_id, vendor_id, amount_paid, payment_method)"}), 400

    try:
        new_payment = VendorPayment(
            bill_id=data['bill_id'],
            vendor_id=data['vendor_id'],
            amount_paid=Decimal(str(data['amount_paid'])),
            payment_method=data['payment_method'],
            notes=data.get('notes'),
            payment_date=datetime.fromisoformat(data['payment_date']) if 'payment_date' in data else None
        )

        db.session.add(new_payment)
        db.session.commit()
        return jsonify(new_payment.to_dict()), 201 # 201 Created

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create vendor payment", "error": str(e)}), 400
    
@vendor_payments_bp.route('/get', methods=['GET'])
def get_all_vendor_payments():
    payments = VendorPayment.query.all()
    # Serialize the list
    return jsonify([payment.to_dict() for payment in payments]), 200


    
@vendor_payments_bp.route('/api/vendor_payments/<string:vendor_payment_id>', methods=['GET'])
def get_vendor_payment_by_id(vendor_payment_id):
    # Use .get() for primary key lookup
    payment = VendorPayment.query.get(vendor_payment_id)

    if payment is None:
        return jsonify({"message": f"Vendor Payment with ID {vendor_payment_id} not found"}), 404

    return jsonify(payment.to_dict()), 200


@vendor_payments_bp.route('/update/<string:vendor_payment_id>', methods=['PUT'])
def update_vendor_payment(vendor_payment_id):
    data = request.get_json()
    payment = VendorPayment.query.get(vendor_payment_id)

    if payment is None:
        return jsonify({"message": f"Vendor Payment with ID {vendor_payment_id} not found"}), 404

    try:
        # Update fields only if they exist in the incoming data
        if 'bill_id' in data:
            payment.bill_id = data['bill_id']
        if 'vendor_id' in data:
            payment.vendor_id = data['vendor_id']
        if 'amount_paid' in data:
            payment.amount_paid = Decimal(str(data['amount_paid']))
        if 'payment_method' in data:
            payment.payment_method = data['payment_method']
        if 'notes' in data:
            payment.notes = data['notes']
        if 'payment_date' in data:
            payment.payment_date = datetime.fromisoformat(data['payment_date'])

        db.session.commit()
        return jsonify(payment.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update vendor payment", "error": str(e)}), 400
    

@vendor_payments_bp.route('/api/vendor_payments/<string:vendor_payment_id>', methods=['DELETE'])
def delete_vendor_payment(vendor_payment_id):
    payment = VendorPayment.query.get(vendor_payment_id)

    if payment is None:
        return jsonify({"message": f"Vendor Payment with ID {vendor_payment_id} not found"}), 404

    try:
        db.session.delete(payment)
        db.session.commit()
        # 204 No Content is the standard response for a successful DELETE with no body
        return '', 204

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete vendor payment", "error": str(e)}), 500