from flask import Blueprint , jsonify , request
from models import SiteMaps , db , Upload_Files
import logging
import datetime
import uuid
from flask_cors import CORS

site_maps_bp = Blueprint('site_maps', __name__)

CORS(site_maps_bp)

def generate_uuid():
    return str(uuid.uuid4())

# --- POST create a new site map ---
@site_maps_bp.route('/site_maps' , methods = ['POST'])
def craete_site_map():
    data = request.json
    try:
        new_site_map = SiteMaps(
            project_id = data.get('project_id'),
            name = data.get('name'),
            description = data.get('description')
        )
        db.session.add(new_site_map)
        db.session.commit()
        return jsonify({'message':'Site map created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create site map", "error": str(e)}), 400
    
# --- GET all site maps ---
@site_maps_bp.route('/site_maps' , methods = ['GET'])
def get_all_site_maps():
    try:
        site_maps = SiteMaps.query.all()
        result = []
        for site_map in site_maps:
            site_map_dict = {
                'site_map_id' : site_map.site_map_id,
                'project_id' : site_map.project_id,
                'name' : site_map.name,
                'description' : site_map.description,
                'uploaded_at' : site_map.uploaded_at
            }
            result.append(site_map_dict)
        return jsonify(result) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
# --- GET single site map by id ---
@site_maps_bp.route('/site_maps/<string:site_map_id>' , methods = ['GET'])
def get_site_map_by_id(site_map_id):
    try:
        site_map = SiteMaps.query.get_or_404(site_map_id)
        site_map_dict = {
            'site_map_id' : site_map.site_map_id,
            'project_id' : site_map.project_id,
            'name' : site_map.name,
            'description' : site_map.description,
            'uploaded_at' : site_map.uploaded_at
        }
        return jsonify(site_map_dict) , 200
    except Exception as e:
        return jsonify({"error" : str(e)}) , 500
    
#---GET site maps by project id ---
