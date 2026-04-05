from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from config import db, societies_col, users_col, notices_col, payments_col, complaints_col, format_doc
from middleware import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/societies', methods=['GET', 'POST'])
@admin_required
def admin_societies():
    if request.method == 'POST':
        data = request.json
        s = {
            "name": data.get('name'),
            "code": f"SOC-{int(datetime.utcnow().timestamp()) % 10000}",
            "address": data.get('address'),
            "createdAt": datetime.utcnow().isoformat()
        }
        societies_col.insert_one(s)
        return jsonify({"message": "Society registered", "code": s["code"]})
    
    s_list = list(societies_col.find().sort("createdAt", -1))
    return jsonify([format_doc(s) for s in s_list])

@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    u_list = list(users_col.find().sort("joinedAt", 1))
    return jsonify([format_doc(u) for u in u_list])

@admin_bp.route('/admin/notices', methods=['POST'])
@admin_required
def add_notice():
    data = request.json
    n = {
        "societyId": data.get('societyId'),
        "title": data.get('title'),
        "content": data.get('content'),
        "category": data.get('category'), # 'Event', 'Emergency', 'General'
        "createdAt": datetime.utcnow().isoformat()
    }
    notices_col.insert_one(n)
    return jsonify({"message": "Official notice published"})

@admin_bp.route('/admin/complaints/<c_id>', methods=['PUT'])
@admin_required
def resolve_complaint(c_id):
    status = request.json.get('status', 'Resolved')
    complaints_col.update_one({"_id": ObjectId(c_id)}, {"$set": {"status": status, "resolvedAt": datetime.utcnow().isoformat()}})
    return jsonify({"message": "Complaint status updated"})
