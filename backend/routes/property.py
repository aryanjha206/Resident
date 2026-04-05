from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from config import properties_col, format_doc
from middleware import token_required

property_bp = Blueprint('property', __name__)

@property_bp.route('/properties', methods=['GET'])
@token_required
def get_properties():
    # Only show active properties
    p_list = list(properties_col.find({"status": "Active"}).sort("createdAt", -1))
    return jsonify([format_doc(p) for p in p_list])

@property_bp.route('/properties', methods=['POST'])
@token_required
def list_property():
    data = request.json
    p = {
        "userId": request.user_data.get('user_id'),
        "userName": request.user_data.get('name'),
        "societyId": request.user_data.get('societyId'),
        "title": data.get('title'),
        "price": data.get('price'),
        "type": data.get('type'), # BHK
        "image": data.get('image'),
        "description": data.get('description'),
        "status": "Active",
        "createdAt": datetime.utcnow().isoformat()
    }
    properties_col.insert_one(p)
    return jsonify({"message": "Property listed successfully"})

@property_bp.route('/properties/my-list', methods=['GET'])
@token_required
def my_property_list():
    u_id = request.user_data.get('user_id')
    p_list = list(properties_col.find({"userId": u_id}).sort("createdAt", -1))
    return jsonify([format_doc(p) for p in p_list])
