import random
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from config import Config, visitors_col, societies_col, format_doc
from middleware import token_required

visitors_bp = Blueprint('visitors', __name__)

@visitors_bp.route('/visitors', methods=['POST'])
@token_required
def schedule_visitor():
    user_id = request.user_data.get('user_id')
    user_name = request.user_data.get('name')
    society_id = request.user_data.get('societyId')
    data = request.json
    
    pass_code = str(random.randint(100000, 999999))
    
    v = {
        "userId": user_id,
        "userName": user_name,
        "societyId": society_id,
        "visitorName": data.get('visitorName'),
        "phone": data.get('phone'),
        "purpose": data.get('purpose'),
        "expectedDate": data.get('expectedDate'),
        "passCode": pass_code,
        "status": "Expected",
        "createdAt": datetime.utcnow().isoformat()
    }
    visitors_col.insert_one(v)
    return jsonify({"message": "Visitor PASS generated", "passCode": pass_code}), 201

@visitors_bp.route('/visitors/my-list', methods=['GET'])
@token_required
def get_my_visitors():
    u_id = request.user_data.get('user_id')
    v_list = list(visitors_col.find({"userId": u_id}).sort("createdAt", -1))
    return jsonify([format_doc(v) for v in v_list])

@visitors_bp.route('/security/verify-pass', methods=['POST'])
def verify_pass():
    pass_code = request.json.get('passCode')
    if not pass_code: return jsonify({"error": "Pass Code required"}), 400
    
    visitor = visitors_col.find_one({"passCode": pass_code, "status": {"$in": ["Expected", "Entered"]}})
    if not visitor: return jsonify({"error": "Invalid or Expired Pass Code"}), 404
        
    society = societies_col.find_one({"_id": ObjectId(visitor["societyId"])})
    return jsonify({
        "visitorId": str(visitor["_id"]),
        "visitorName": visitor["visitorName"],
        "purpose": visitor["purpose"],
        "residentName": visitor["userName"],
        "societyName": society["name"] if society else "Unknown",
        "status": visitor["status"]
    })

@visitors_bp.route('/visitors/<v_id>/check-in', methods=['PUT'])
def check_in_visitor(v_id):
    visitors_col.update_one({"_id": ObjectId(v_id)}, {"$set": {"status": "Entered", "checkInTime": datetime.utcnow().isoformat()}})
    return jsonify({"message": "Access GRANTED"})
