from flask import Blueprint , jsonify , request , current_app
from models import Templates , db , TemplateCards
import datetime
import uuid
from flask_cors import CORS
import logging

template_cards_bp = Blueprint('template_cards', __name__)
CORS(template_cards_bp)

def generate_uuid():
    return str(uuid.uuid4())

#get all template cards
@template_cards_bp.route('/get' , methods = ['GET'])
def get_all_template_cards():
    try:
        page = request.args.get('page' , 1 , type = int)
        per_page = request.args.get('per_page' , 10 , type = int)
        
        # 🛑 FIX: Query the TemplateCards model 🛑
        template_cards_pagination = TemplateCards.query.paginate(page=page, per_page=per_page, error_out=False)
        template_cards = template_cards_pagination.items
        
        result = []
        for card in template_cards: # Renamed loop variable to 'card' for clarity
            result.append({
                # Include the card's own primary key for clarity
                'template_card_id': card.template_card_id, 
                
                # Fields that exist in TemplateCards model:
                'template_id': card.template_id,
                'card_name': card.card_name,
                'description': card.description,
                'card_type': card.card_type,
                'default_status': card.default_status,
                'sort_order': card.sort_order,
                # 'created_at': card.created_at.isoformat() if card.created_at else None # Include this if 'created_at' is a column
            })
            
        return jsonify({
            'template_cards' : result , 
            'total_template_cards': template_cards_pagination.total,
            'total_pages': template_cards_pagination.pages,
            'current_page': template_cards_pagination.page,
            'has_next': template_cards_pagination.has_next,
            'has_prev': template_cards_pagination.has_prev
        }) , 200
        
    except Exception as e:
        # A 500 status code with an error message is good for debugging
        return jsonify({"error" : str(e)}) , 500
    
#get single template card by id
@template_cards_bp.route('/template_cards/<string:template_id>' , methods = ['GET'])
def get_template_card_by_id(template_id):
    """
    Retrieves all TemplateCards associated with a given template_id.
    """
    
    # 1. Fetch all TemplateCards matching the template_id
    # The query is already correct: it fetches a list of TemplateCards objects.
    template_cards = TemplateCards.query.filter_by(template_id=template_id).all()
    
    # 2. Handle the case where no cards are found
    if not template_cards:
        # It's good practice to clarify the error, e.g., using the ID
        return jsonify({"message": f"No Template Cards found for template ID: {template_id}"}), 404
    
    # 3. Serialize the list of card objects
    cards_list = []
    for card in template_cards:
        cards_list.append({
            # It's usually helpful to include the primary key of the card itself
            'template_card_id': card.template_card_id, 
            'template_id': card.template_id,
            'card_name': card.card_name,
            'description': card.description,
            'card_type': card.card_type,
            'default_status': card.default_status,
            'sort_order': card.sort_order,
            # 'created_at': card.created_at.isoformat() if card.created_at else None # Convert datetime to string
        })
        
        # 🛑 The erroneous line has been REMOVED 🛑
        
    # 4. Return the list of serialized card data
    return jsonify(cards_list) , 200

#add new template card
@template_cards_bp.route('/post', methods=['POST'])
def add_template_card():
    data = request.get_json()

    # 1. Initialize a list to hold the new card objects
    cards_to_add = []

    # 2. Check if the input is a list (multiple cards) or a dict (single card)
    if isinstance(data, list):
        # Input is a list: iterate over each card object
        card_data_list = data
    elif isinstance(data, dict):
        # Input is a dict: wrap it in a list to use the same processing logic
        card_data_list = [data]
    else:
        return jsonify({"error": "Invalid data format", "details": "Expected a JSON object or array"}), 400

    # 3. Loop through the list and create a TemplateCards object for each
    for card_data in card_data_list:
        # ** card_data is now a dictionary (object), so .get() works! **
        try:
            new_card = TemplateCards(
                template_id=card_data.get('template_id'),
                card_name=card_data.get('card_name'),
                description=card_data.get('description'),
                card_type=card_data.get('card_type'),
                default_status=card_data.get('default_status', 'To Do'), # Use default if not provided
                sort_order=card_data.get('sort_order')
                # Include all relevant TemplateCards fields here
            )
            cards_to_add.append(new_card)

        except Exception as e:
            # Handle cases where required fields are missing or types are incorrect
            return jsonify({"error": "Failed to process card data", "details": str(e)}), 400

    # 4. Add all new cards to the session and commit
    if cards_to_add:
        try:
            db.session.add_all(cards_to_add)
            db.session.commit()
            return jsonify({"message": f"Successfully created {len(cards_to_add)} template card(s)"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Failed to save cards to database", "details": str(e)}), 500
    
    return jsonify({"message": "No cards provided"}), 200
    
#update template card
@template_cards_bp.route('/update/<string:template_id>' , methods = ['PUT'])
def update_template_card(template_id):
    template_card = Templates.query.get_or_404(template_id)
    data = request.get_json()
    try:
        template_card.template_name = data.get('template_name' , template_card.template_name)
        template_card.description = data.get('description' , template_card.description)
        template_card.image_url = data.get('image_url' , template_card.image_url)
        db.session.commit()
        return jsonify({"message":"Template Card updated successfully!"}) , 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}) , 500
    
#delete template card
@template_cards_bp.route('/delete/<string:template_id>' , methods = ['DELETE'])
def delete_template_card(template_id):
    template_card = Templates.query.get_or_404(template_id)
    try:
        db.session.delete(template_card)
        db.session.commit()
        return jsonify({"message":"Template Card deleted successfully!"}) , 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}) , 500
    
