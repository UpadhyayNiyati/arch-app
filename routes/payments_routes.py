from flask import Flask, request, jsonify , Blueprint
from models import db , Payment
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from decimal import Decimal
import logging

# Initialize Flask App and SQLAlchemy (placeholders)
app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
# db = SQLAlchemy(app)

payments_bp = Blueprint('Payment' , __name__)

# --- Utility Function Placeholder ---
def generate_uuid():
    """Generates a standard UUID-4 string."""
    return str(uuid.uuid4())

# --- Model Definition (as provided) ---
class Payment(db.Model):
    __tablename__ = 'payments'
    # ... (Model columns as you defined them) ...
    payment_id = db.Column(db.String(36), primary_key=True, default=generate_uuid, nullable=False)
    invoice_id = db.Column(db.String(36), db.ForeignKey('invoices.invoice_id'), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount_received = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(100), nullable=False)
    transaction_ref = db.Column(db.String(255), unique=True, nullable=True)
    # invoice = db.relationship('Invoice', backref='payments') # Assuming Invoice model exists

    def to_dict(self):
        """Converts the Payment object to a dictionary for JSON serialization."""
        return {
            'payment_id': self.payment_id,
            'invoice_id': self.invoice_id,
            'payment_date': self.payment_date.isoformat(),
            # Convert Decimal to string for JSON serialization
            'amount_received': str(self.amount_received),
            'payment_method': self.payment_method,
            'transaction_ref': self.transaction_ref
        }
    
@payments_bp.route('/post', methods=['POST'])
def create_payment():
    data = request.get_json()

    # Basic input validation
    if not all(k in data for k in ('invoice_id', 'amount_received', 'payment_method')):
        return jsonify({"message": "Missing required fields"}), 400

    try:
        new_payment = Payment(
            invoice_id=data['invoice_id'],
            # Ensure amount is converted correctly (from string/float to Decimal)
            amount_received=Decimal(str(data['amount_received'])),
            payment_method=data['payment_method'],
            # Optional fields
            transaction_ref=data.get('transaction_ref'),
            # payment_date can be set from the request if provided, otherwise defaults to utcnow
            payment_date=datetime.fromisoformat(data['payment_date']) if 'payment_date' in data else None
        )

        db.session.add(new_payment)
        db.session.commit()
        return jsonify(new_payment.to_dict()), 201 # 201 Created

    except Exception as e:
        db.session.rollback()
        # Handle database constraints or invalid input gracefully
        return jsonify({"message": "Failed to create payment", "error": str(e)}), 400

@payments_bp.route('/get', methods=['GET'])
def get_all_payments():
    # Use .all() to get all payments
    payments = Payment.query.all()
    # Serialize the list of objects
    return jsonify([payment.to_dict() for payment in payments]), 200

@payments_bp.route('/get/<string:payment_id>', methods=['GET'])
def get_payment_by_id(payment_id):
    # Use .first_or_404() for cleaner error handling if using Flask-SQLAlchemy > 3.0
    # or use .get() for primary key lookup
    payment = Payment.query.get(payment_id)

    if payment is None:
        return jsonify({"message": f"Payment with ID {payment_id} not found"}), 404

    return jsonify(payment.to_dict()), 200

@payments_bp.route('/update_payments/<string:payment_id>', methods=['PUT'])
def update_payment(payment_id):
    data = request.get_json()
    payment = Payment.query.get(payment_id)

    if payment is None:
        return jsonify({"message": f"Payment with ID {payment_id} not found"}), 404

    try:
        # Update fields only if they exist in the incoming data
        if 'invoice_id' in data:
            payment.invoice_id = data['invoice_id']
        if 'amount_received' in data:
            # Convert to Decimal
            payment.amount_received = Decimal(str(data['amount_received']))
        if 'payment_method' in data:
            payment.payment_method = data['payment_method']
        if 'transaction_ref' in data:
            payment.transaction_ref = data['transaction_ref']
        if 'payment_date' in data:
            payment.payment_date = datetime.fromisoformat(data['payment_date'])

        db.session.commit()
        return jsonify(payment.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update payment", "error": str(e)}), 400
    
@payments_bp.route('/del_payments/<string:payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    payment = Payment.query.get(payment_id)

    if payment is None:
        return jsonify({"message": f"Payment with ID {payment_id} not found"}), 404

    try:
        db.session.delete(payment)
        db.session.commit()
        # 204 No Content is the standard response for a successful DELETE
        return jsonify({"message": f"Payment with ID {payment_id} successfully deleted"}), 204

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete payment", "error": str(e)}), 500