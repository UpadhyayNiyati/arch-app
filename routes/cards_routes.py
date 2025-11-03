from flask import Flask, request, jsonify , Blueprint
from flask_sqlalchemy import SQLAlchemy
from models import db , Cards , Clients
from datetime import datetime
import uuid
from decimal import Decimal
from flask_cors import CORS

# --- Utility Function Placeholder ---
def generate_uuid():
    return str(uuid.uuid4())

cards_bp = Blueprint('Cards' , __name__)

CORS(cards_bp)

@cards_bp.route('/post', methods=['POST'])
def create_card():
    data = request.json

    # Basic input validation for required fields
    if not all(k in data for k in ('card_name', 'description', 'status' , 'client_name' , 'due_date' , 'location' , 'cardscount')):
        return jsonify({"message": "Missing required fields (card_name, card_type, status)"}), 400

    try:
        client_name = data['client_name']

        client = Clients.query.filter_by(client_name=client_name).first()
        if client is None:
            new_client = Clients(client_name = client_name)
            db.session.add(new_client)
            db.session.commit()
            client_id = new_client.client_id
        else:
            client_id = client.client_id

        new_card = Cards(
            card_name=data['card_name'],
            # card_type=data['card_type'],
            status=data['status'],
            description=data.get('description'),
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date() if 'due_date' in data else None,
            location=data.get('location'),
            cardscount=int(data['cardscount']) if 'cardscount' in data else None,
            client_id = client_id

            # created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None
        )

        db.session.add(new_card)
        db.session.commit()
        return jsonify({'message':'card added successfully'}), 201 # 201 Created

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create card", "error": str(e)}), 400
    
@cards_bp.route('/get', methods=['GET'])
def get_all_cards():
    cards = Cards.query.all()
    # Serialize the list
    return jsonify([card.to_dict() for card in cards]), 200

@cards_bp.route('/get/<string:card_id>', methods=['GET'])
def get_card_by_id(card_id):
    card = Cards.query.get(card_id)
    if not card:
        return jsonify({"message": "Card not found"}), 404
    return jsonify(card.to_dict()), 200

@cards_bp.route('/update/<string:card_id>', methods=['PUT'])
def update_card(card_id):
    card = Cards.query.get(card_id)
    if not card:
        return jsonify({"message": "Card not found"}), 404

    data = request.json
    try:
        card.card_name = data.get('card_name', card.card_name)
        card.card_type = data.get('card_type', card.card_type)
        card.status = data.get('status', card.status)
        card.description = data.get('description', card.description)
        db.session.commit()
        return jsonify({"message": "Card updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update card", "error": str(e)}), 400
    
@cards_bp.route('/delete/<string:card_id>', methods=['DELETE'])
def delete_card(card_id):
    card = Cards.query.get(card_id)
    if not card:
        return jsonify({"message": "Card not found"}), 404

    try:
        db.session.delete(card)
        db.session.commit()
        return jsonify({"message": "Card deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete card", "error": str(e)}), 400
    
