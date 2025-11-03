import uuid
import logging
from datetime import datetime, date
from flask_cors import CORS
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import NotFound


# --- ASSUMED IMPORTS (Adjust based on your project structure) ---
# Assuming db (SQLAlchemy instance), Invoice model, and generate_uuid are available
# from your models file or main app module.
# Example placeholders:
class Invoice:
    # Minimal representation for function signatures
    @classmethod
    def query(cls): return None 
    def __init__(self, **kwargs): pass
    def __repr__(self): return "<Invoice>"
    def __dict__(self): return {}

class Clients: pass
class Projects: pass

# --- Mock DB Setup for context ---
class MockDB:
    def session(self): return self
    def add(self, obj): pass
    def commit(self): pass
    def rollback(self): pass
    def flush(self): pass

db = MockDB()

def generate_uuid():
    return str(uuid.uuid4())

# --- BLUEPRINT INITIALIZATION ---
invoices_bp = Blueprint('invoices_bp', __name__)
CORS(invoices_bp)
logger = logging.getLogger(__name__)

# --- HELPER FUNCTIONS ---

def safe_cast(value, target_type, default=None):
    """Safely casts a string value to the target type."""
    if value is None:
        return default
    try:
        if target_type == date:
            return datetime.strptime(str(value), '%Y-%m-%d').date()
        elif target_type == Decimal:
            # Use strict Decimal creation
            return Decimal(str(value))
        elif target_type == float:
            return float(str(value))
        return target_type(value)
    except (ValueError, TypeError, InvalidOperation):
        return default

def invoice_to_dict(invoice):
    """Converts an Invoice object to a dictionary for JSON response."""
    return {
        'invoice_id': invoice.invoice_id,
        'client_id': invoice.client_id,
        'project_id': invoice.project_id,
        'invoice_number': invoice.invoice_number,
        'issue_date': invoice.issue_date.isoformat() if invoice.issue_date else None,
        'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
        # Convert Decimal types to float or string for JSON serialization
        'total_amount': float(invoice.total_amount) if invoice.total_amount else 0.0,
        'tax_rate': float(invoice.tax_rate) if invoice.tax_rate else 0.0,
        'status': invoice.status,
        'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
    }


# =========================================================================
# 1. POST (Create New Invoice)
# =========================================================================
@invoices_bp.route('/invoices/add', methods=['POST'])
def create_invoice():
    data = request.get_json()
    logger.info("Received POST request for new invoice.")

    required_fields = ['client_id', 'project_id', 'invoice_number', 'issue_date', 'due_date', 'total_amount', 'tax_rate']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"Missing required field: {field}"}), 400

    try:
        # Convert date strings to date objects
        issue_date_obj = safe_cast(data['issue_date'], date)
        due_date_obj = safe_cast(data['due_date'], date)
        
        # Convert monetary fields to Decimal for accuracy
        total_amount_dec = safe_cast(data['total_amount'], Decimal)
        tax_rate_dec = safe_cast(data['tax_rate'], Decimal)

        if not all([issue_date_obj, due_date_obj, total_amount_dec is not None, tax_rate_dec is not None]):
             return jsonify({'error': "Invalid date or numeric format for required fields."}), 400

        new_invoice = Invoice(
            invoice_id=generate_uuid(),
            client_id=data['client_id'],
            project_id=data['project_id'],
            invoice_number=data['invoice_number'],
            issue_date=issue_date_obj,
            due_date=due_date_obj,
            total_amount=total_amount_dec,
            tax_rate=tax_rate_dec,
            status=data.get('status', 'Draft') # Default to 'Draft' if not provided
        )

        db.session.add(new_invoice)
        db.session.commit()
        logger.info("Invoice %s created successfully.", new_invoice.invoice_id)
        return jsonify(invoice_to_dict(new_invoice)), 201

    except IntegrityError as e:
        db.session.rollback()
        logger.error("Integrity error creating invoice: %s", str(e.orig))
        return jsonify({'error': 'Integrity constraint failed (e.g., duplicate invoice number or invalid FK).'}), 409
    except Exception as e:
        db.session.rollback()
        logger.exception("Unexpected error creating invoice.")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


# =========================================================================
# 2. GET ALL
# =========================================================================
@invoices_bp.route('/invoices', methods=['GET'])
def get_all_invoices():
    logger.info("Fetching all invoices.")
    try:
        # NOTE: This assumes Invoice.query.all() works via your imported db instance
        invoices = Invoice.query.all() 
        return jsonify([invoice_to_dict(inv) for inv in invoices]), 200
    except Exception as e:
        logger.exception("Error fetching all invoices.")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


# =========================================================================
# 3. GET BY ID
# =========================================================================
@invoices_bp.route('/invoices/<string:invoice_id>', methods=['GET'])
def get_invoice_by_id(invoice_id):
    logger.info("Fetching invoice with ID: %s", invoice_id)
    try:
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            raise NotFound(description=f"Invoice with ID {invoice_id} not found.")

        return jsonify(invoice_to_dict(invoice)), 200
    except NotFound as e:
        return jsonify({'error': str(e.description)}), 404
    except Exception as e:
        logger.exception("Error fetching invoice by ID.")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


# =========================================================================
# 4. PUT (Update Existing Invoice)
# =========================================================================
@invoices_bp.route('/invoices/<string:invoice_id>', methods=['PUT'])
def update_invoice(invoice_id):
    data = request.get_json()
    logger.info("Received PUT request for invoice ID: %s", invoice_id)

    try:
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            raise NotFound(description=f"Invoice with ID {invoice_id} not found.")

        # Update fields only if they are present in the request data
        if 'invoice_number' in data:
            invoice.invoice_number = data['invoice_number']
        if 'issue_date' in data:
            invoice.issue_date = safe_cast(data['issue_date'], date, invoice.issue_date)
        if 'due_date' in data:
            invoice.due_date = safe_cast(data['due_date'], date, invoice.due_date)
        if 'total_amount' in data:
            invoice.total_amount = safe_cast(data['total_amount'], Decimal, invoice.total_amount)
        if 'tax_rate' in data:
            invoice.tax_rate = safe_cast(data['tax_rate'], Decimal, invoice.tax_rate)
        if 'status' in data:
            invoice.status = data['status']
        if 'client_id' in data:
            invoice.client_id = data['client_id']
        if 'project_id' in data:
            invoice.project_id = data['project_id']

        db.session.commit()
        logger.info("Invoice %s updated successfully.", invoice_id)
        return jsonify(invoice_to_dict(invoice)), 200

    except NotFound as e:
        db.session.rollback()
        return jsonify({'error': str(e.description)}), 404
    except IntegrityError as e:
        db.session.rollback()
        logger.error("Integrity error updating invoice: %s", str(e.orig))
        return jsonify({'error': 'Integrity constraint failed (e.g., duplicate invoice number).'}), 409
    except Exception as e:
        db.session.rollback()
        logger.exception("Unexpected error updating invoice.")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


# =========================================================================
# 5. DELETE
# =========================================================================
@invoices_bp.route('/invoices/<string:invoice_id>', methods=['DELETE'])
def delete_invoice(invoice_id):
    logger.warning("Received DELETE request for invoice ID: %s", invoice_id)
    try:
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            raise NotFound(description=f"Invoice with ID {invoice_id} not found.")

        db.session.delete(invoice)
        db.session.commit()
        logger.warning("Invoice %s deleted successfully.", invoice_id)
        return jsonify({'message': f'Invoice {invoice_id} deleted successfully'}), 204

    except NotFound as e:
        db.session.rollback()
        return jsonify({'error': str(e.description)}), 404
    except Exception as e:
        db.session.rollback()
        logger.exception("Error deleting invoice.")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
