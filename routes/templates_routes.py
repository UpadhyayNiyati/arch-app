from flask import Blueprint , jsonify , request
from models import Templates , db
import datetime
import uuid

templates_bp = Blueprint('templates', __name__)

#get all templates
@templates_bp.route('/templates' , methods = ['GET'])
def get_all_templates():
    try:
        # templates = Templates.query.all()
        # result = []
        # for template in templates:
        #     result.append({
        #         'template_id' : template.template_id , 
        #         'template_name' : template.template_name , 
        #         'description' : template.description , 
        #         'created_at' : template.created_at , 
        #         'image_url' : template.image_url , 
                
        #     })
        page = request.args.get('page' , 1 , type = int)
        per_page = request.args.get('per_page' , 10 , type = int)
        #use paginate to get a paginated result
        templates_pagination = Templates.query.paginate(page = page , per_page = per_page , error_out = False)
        templates = templates_pagination.items
        result = []
        for template in templates:
            result.append({
                'template_id':template.template_id , 
                'template_name': template.template_name,
                'description': template.description,
                'created_at': template.created_at,
                # 'image_url': template.image_url,
            })
        return jsonify({
            'templates' : result , 
            'total_templates':templates_pagination.total,
            'total_pages':templates_pagination.pages,
            'current_page': templates_pagination.page,
            'has_next': templates_pagination.has_next,
            'has_prev': templates_pagination.has_prev
        }) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500

#get single template by id
@templates_bp.route('/templates/<string:template_id>' , methods = ['GET'])
def get_template_by_id(template_id):
    template = Templates.query.get_or_404(template_id)
    if not template:
        return jsonify({"message":"Template not found"}) , 404
    result = {
        'template_id' : template.template_id , 
        'template_name' : template.template_name , 
        'description' : template.description , 
        'created_at' : template.created_at , 
        # 'image_url' : template.image_url
    }
    return jsonify(result) , 200

#post template
@templates_bp.route('/templates' , methods = ['POST'])
def add_templates():
    data = request.json
    required_fields = ['template_name' , 'description' , 'image_url']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"'{field}' is required"}), 400
    try:
        new_template = Templates(
            template_name = data['template_name'] , 
            description = data['description'] , 
            image_url = data['image_url']
        )
        db.session.add(new_template)
        db.session.commit()
        return jsonify({'message':'Template added successfully'}) , 201
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#update template by id
@templates_bp.route('/templates/<string:template_id>' , methods = ['PUT'])
def update_template(template_id):
    data = request.json
    template = Templates.query.get_or_404(template_id)
    if not template:
        return jsonify({"message":"Template not found"}) , 404
    if 'template_name' in data:
        template.template_name = data['template_name']
    if 'description' in data:
        template.description = data['description']
    if 'image_url' in data:
        template.image_url = data['image_url']
    db.session.commit()
    result = {
        'template_id' : template.template_id , 
        'template_name' : template.template_name , 
        'description' : template.description , 
        'created_at' : template.created_at , 
        'image_url' : template.image_url
    }

    return jsonify(result) , 200

#delete template by id
@templates_bp.route('/templates/<string:template_id>' , methods = ['DELETE'])
def delete_template(template_id):
    template = Templates.query.get_or_404(template_id)
    if not template:
        return jsonify({"message":"Template not found"}) , 404
    db.session.delete(template)
    db.session.commit()
    result = {
        'template_id' : template.template_id , 
        'template_name' : template.template_name , 
        'description' : template.description , 
        'created_at' : template.created_at , 
        'image_url' : template.image_url
    }
    return jsonify({"message":"Template deleted successfully!!"}) , 200

    