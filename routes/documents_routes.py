from flask import Blueprint , jsonify , request
from models import Documents , db
import datetime
import uuid
documents_bp = Blueprint('documents', __name__)

#get all documents
@documents_bp.route('/documents' , methods = ['GET'])
def get_all_documents():
    try:
        documents = Documents.query.all()
        result = []
        for document in documents:
            result.append({
                'document_id' : document.document_id , 
                'project_id' : document.project_id , 
                'document_name' : document.document_name , 
                'document_type' : document.document_type , 
                'uploaded_at' : document.uploaded_at , 
                'file_url' : document.file_url , 
                'task_id'  : document.task_id
            })
        return jsonify(result) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#get singl1e document by id
@documents_bp.route('/documents/<string:document_id>' , methods = ['GET'])
def get_document_by_id(document_id):
    document = Documents.query.get_or_404(document_id)
    if not document:
        return jsonify({"message":"Document not found"}) , 404
    result = {
        'document_id' : document.document_id , 
        'project_id' : document.project_id , 
        'file_name' : document.file_name , 
        'document_type' : document.document_type , 
        'uploaded_at' : document.uploaded_at , 
        'file_url' : document.file_url , 
        'task_id'  : document.task_id
    }
    return jsonify(result) , 200

#post document
@documents_bp.route('/documents' , methods = ['POST'])
def add_documents():
    data = request.json
    required_fields = ['project_id' , 'document_name' , 'document_type' , 'file_url']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"'{field}' is required"}), 400
    try:
        new_document = Documents(
            project_id = data['project_id'] , 
            document_name = data['document_name'] , 
            document_type = data['document_type'] , 
            file_url = data['file_url'] ,
            task_id = data.get('task_id')
        )
        db.session.add(new_document)
        db.session.commit()
        return jsonify({'message':'Document added successfully'}) , 201
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#update document by id
@documents_bp.route('/documents/<string:document_id>' , methods = ['PUT'])
def update_document(document_id):
    data = request.json
    document = Documents.query.get_or_404(document_id)
    if not document:
        return jsonify({"message":"Document not found"}) , 404
    if 'project_id' in data:
        document.project_id = data['project_id']
    if 'document_name' in data:
        document.document_name = data['document_name']
    if 'document_type' in data:
        document.document_type = data['document_type']
    if 'file_url' in data:
        document.file_url = data['file_url']
    if 'task_id' in data:
        document.task_id = data['task_id']
    db.session.commit()
    result = {
        'document_id' : document.document_id , 
        'project_id' : document.project_id , 
        'document_name' : document.document_name , 
        'document_type' : document.document_type , 
        'uploaded_at' : document.uploaded_at , 
        'file_url' : document.file_url , 
        'task_id'  : document.task_id
    }
    return jsonify(result) , 200

#delete document by id
@documents_bp.route('/documents/<string:document_id>' , methods = ['DELETE'])
def delete_document(document_id):
    document = Documents.query.get_or_404(document_id)
    if not document:
        return jsonify({"message":"Document not found"}) , 404
    try:
        db.session.delete(document)
        db.session.commit()
        return jsonify({"message":"Document deleted successfully"}) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500