from flask import Blueprint , jsonify , request
from models import Templates , db
import datetime
import uuid

template_cards_bp = Blueprint('template_cards', __name__)

def generate_uuid():
    return str(uuid.uuid4())

#get all template cards
@template_cards_bp.route('/get' , methods = ['GET'])
def get_all_template_cards():
    try:
        page = request.args.get('page' , 1 , type = int)
        per_page = request.args.get('per_page' , 10 , type = int)
        #use paginate to get a paginated result
        template_cards_pagination = Templates.query.paginate(page = page , per_page = per_page , error_out = False)
        template_cards = template_cards_pagination.items
        result = []
        for template_card in template_cards:
            result.append({
                'template_id':template_card.template_id , 
                'template_name': template_card.template_name,
                'description': template_card.description,
                'created_at': template_card.created_at,
                'default_status':template_card.default_status,
                'card_type':template_card.card_type,
                'sort_order':template_card.sort_order,
                'card_name':template_card.card_name
                
            })
        return jsonify({
            'template_cards' : result , 
            'total_template_cards':template_cards_pagination.total,
            'total_pages':template_cards_pagination.pages,
            'current_page': template_cards_pagination.page,
            'has_next': template_cards_pagination.has_next,
            'has_prev': template_cards_pagination.has_prev
        }) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#get single template card by id
@template_cards_bp.route('/template_cards/<string:template_id>' , methods = ['GET'])
def get_template_card_by_id(template_id):
    template_card = Templates.query.get_or_404(template_id)
    if not template_card:
        return jsonify({"message":"Template Card not found"}) , 404
    result = {
        'template_id' : template_card.template_id , 
        'template_name' : template_card.template_name , 
        'description' : template_card.description , 
        'created_at' : template_card.created_at , 
        # 'image_url' : template_card.image_url
        'card_name': template_card.card_name,
        'card_type': template_card.card_type,
        'default_status': template_card.default_status,
        'sort_order': template_card.sort_order
    }
    return jsonify(result) , 200

#add new template card
@template_cards_bp.route('/add' , methods = ['POST'])
def add_template_card():
    data = request.get_json()
    new_template_card = Templates(
        template_id = generate_uuid(),
        template_name = data.get('template_name'),
        description = data.get('description'),
        created_at = datetime.datetime.utcnow(),
        card_name = data.get('card_name' ),
        card_type = data.get('card_type' ),
        default_status = data.get('default_status'),
        sort_order = data.get('sort_order')
    )
    try:
        db.session.add(new_template_card)
        db.session.commit()
        return jsonify({"message":"Template Card added successfully!"}) , 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}) , 500
    
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
    
