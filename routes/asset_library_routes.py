from flask import Blueprint, jsonify, request
from models import AssetLibrary, User, db
from datetime import datetime
import uuid
from flask_cors import CORS

assets_bp = Blueprint('assets', __name__)

CORS(assets_bp)

# --- GET all assets ---
@assets_bp.route('/assets', methods=['GET'])
def get_all_assets():
    try:
        assets = AssetLibrary.query.all()
        result = []
        for asset in assets:
            result.append({
                'asset_id': asset.asset_id,
                'asset_name': asset.asset_name,
                'asset_url': asset.asset_url,
                'asset_type': asset.asset_type,
                'uploaded_by': asset.uploaded_by,
                'created_at': asset.created_at.isoformat()
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GET a single asset by ID ---
@assets_bp.route('/assets/<string:asset_id>', methods=['GET'])
def get_one_asset(asset_id):
    try:
        asset = AssetLibrary.query.get_or_404(asset_id)
        result = {
            'asset_id': asset.asset_id,
            'asset_name': asset.asset_name,
            'asset_url': asset.asset_url,
            'asset_type': asset.asset_type,
            'uploaded_by': asset.uploaded_by,
            'created_at': asset.created_at.isoformat()
        }
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST a new asset ---
@assets_bp.route('/assets', methods=['POST'])
def add_asset():
    data = request.json
    required_fields = ['asset_name', 'asset_url', 'asset_type', 'uploaded_by']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "asset_name, asset_url, asset_type, and uploaded_by are required"}), 400
        
    try:
        # Check if the user exists
        if not User.query.get(data['uploaded_by']):
            return jsonify({"error": "User not found"}), 404

        new_asset = AssetLibrary(
            asset_name=data['asset_name'],
            asset_url=data['asset_url'],
            asset_type=data['asset_type'],
            uploaded_by=data['uploaded_by']
        )
        db.session.add(new_asset)
        db.session.commit()
        return jsonify({'message': 'Asset added successfully', 'asset_id': new_asset.asset_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- PUT (update) an existing asset ---
@assets_bp.route('/assets/<string:asset_id>', methods=['PUT'])
def update_asset(asset_id):
    data = request.json
    asset = AssetLibrary.query.get_or_404(asset_id)
    
    try:
        if 'asset_name' in data:
            asset.asset_name = data['asset_name']
        if 'asset_url' in data:
            asset.asset_url = data['asset_url']
        if 'asset_type' in data:
            asset.asset_type = data['asset_type']
            
        db.session.commit()
        return jsonify({'message': 'Asset updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- DELETE an asset ---
@assets_bp.route('/assets/<string:asset_id>', methods=['DELETE'])
def delete_asset(asset_id):
    asset = AssetLibrary.query.get_or_404(asset_id)
    try:
        db.session.delete(asset)
        db.session.commit()
        return jsonify({'message': 'Asset deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500