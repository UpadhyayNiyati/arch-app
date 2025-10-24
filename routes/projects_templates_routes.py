from flask import Blueprint , jsonify , request
from models import  ProjectTemplates, db

project_templates_bp = Blueprint('project_templates' , __name__)

#get all project_templates
@project_templates_bp.route('/get_all_project_templates' , methods = ['GET'])
def get_all_project_templates():
    try:
        page = request.args.get('page' , 1 , type = int)
        per_page = request.args.get('per_page' , 10 , type = int)
        #use paginate to get a paginated result
        project_templates_pagination = ProjectTemplates.query.paginate(page = page , per_page = per_page , error_out = False)
        project_templates = project_templates_pagination.items
        result = []
        for project_template in project_templates:
            result.append({
                'template_id': project_template.template_id,
                'template_name': project_template.template_name,
                'description': project_template.description,
                # 'template_file_url': project_template.template_file_url,
                # 'created_at': project_template.created_at,
                # 'updated_at': project_template.updated_at,
            })
        return jsonify({
            'project_templates' : result , 
            'total_project_templates':project_templates_pagination.total,
            'total_pages':project_templates_pagination.pages,
            'current_page': project_templates_pagination.page,
            'has_next': project_templates_pagination.has_next,
            'has_prev': project_templates_pagination.has_prev
        }) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#get single project_template by id
@project_templates_bp.route('/get_one_project_template/<string:template_id>' , methods = ['GET'])
def get_project_template_by_id(template_id):
    project_template = ProjectTemplates.query.get_or_404(template_id)
    if not project_template:
        return jsonify({"message":"Project Template not found"}) , 404
    result = {
        'template_id': project_template.template_id,
        'template_name': project_template.template_name,
        'template_description': project_template.template_description,
        # 'template_file_url': project_template.template_file_url,
        # 'created_at': project_template.created_at,
        # 'updated_at': project_template.updated_at,
    }
    return jsonify(result) , 200

#post project_template
@project_templates_bp.route('/post_project_templates', methods=['POST'])
def add_project_template():
    data = request.json
    # --- CORRECTED REQUIRED FIELDS LIST ---
    required_fields = ['project_id', 'template_id', 'template_name', 'description', 'template_file_url']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error' : 'All fields are required'}), 400

    try:
        # --- CORRECTED CONSTRUCTOR ---
        new_project_template = ProjectTemplates(
            project_id=data['project_id'],
            template_id=data['template_id'],
            template_name=data['template_name'],
            description=data['description'],
            template_file_url=data['template_file_url']
        )
        db.session.add(new_project_template)
        db.session.commit()
        return jsonify({'message':'Project Template added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error" : str(e)}), 500
    
#upadte project_template by id
@project_templates_bp.route('/update_project_template/<string:template_id>' , methods = ['PUT'])
def update_project_template(template_id):
    data = request.json
    project_template = ProjectTemplates.query.get_or_404(template_id)
    if not project_template:
        return jsonify({"message":"Project Template not found"}) , 404
    if 'template_name' in data:
        project_template.template_name = data['template_name']
    if 'description' in data:
        project_template.description = data['template_description']
    if 'template_file_url' in data:
        project_template.template_file_url = data['template_file_url']
    
    try:
        db.session.commit()
        return jsonify({'message':'Project Template updated successfully'}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#delete project_template by id
@project_templates_bp.route('/delete_project_template/<string:template_id>' , methods = ['DELETE'])
def delete_project_template(template_id):
    project_template = ProjectTemplates.query.get_or_404(template_id)
    if not project_template:
        return jsonify({"message":"Project Template not found"}) , 404
    try:
        db.session.delete(project_template)
        db.session.commit()
        return jsonify({'message':'Project Template deleted successfully'}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500