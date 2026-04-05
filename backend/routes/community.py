from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from config import db, complaints_col, notices_col, sos_col, polls_col, format_doc
from middleware import token_required

community_bp = Blueprint('community', __name__)

@community_bp.route('/notices', methods=['GET'])
@token_required
def get_notices():
    society_id = request.user_data.get('societyId')
    notices = list(notices_col.find({"societyId": society_id}).sort("createdAt", -1))
    return jsonify([format_doc(n) for n in notices])

@community_bp.route('/complaints', methods=['POST'])
@token_required
def raise_complaint():
    data = request.json
    c = {
        "userId": request.user_data.get('user_id'),
        "userName": request.user_data.get('name'),
        "societyId": request.user_data.get('societyId'),
        "title": data.get('title'),
        "description": data.get('description'),
        "category": data.get('category'),
        "status": "Pending",
        "createdAt": datetime.utcnow().isoformat()
    }
    complaints_col.insert_one(c)
    return jsonify({"message": "Complaint lodged successfully"})

@community_bp.route('/complaints/my-list', methods=['GET'])
@token_required
def get_my_complaints():
    u_id = request.user_data.get('user_id')
    c_list = list(complaints_col.find({"userId": u_id}).sort("createdAt", -1))
    return jsonify([format_doc(c) for c in c_list])

@community_bp.route('/sos/trigger', methods=['POST'])
@token_required
def trigger_sos():
    sos = {
        "userId": request.user_data.get('user_id'),
        "userName": request.user_data.get('name'),
        "societyId": request.user_data.get('societyId'),
        "location": request.json.get('location', 'Unknown'),
        "timestamp": datetime.utcnow().isoformat()
    }
    sos_col.insert_one(sos)
    return jsonify({"message": "SOS broadcasted to all residents and security staff!"})
