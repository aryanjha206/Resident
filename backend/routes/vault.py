from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from config import Config, documents_col, format_doc
from middleware import token_required

vault_bp = Blueprint('vault', __name__)

@vault_bp.route('/vault/upload', methods=['POST'])
@token_required
def upload_vault_doc():
    data = request.json
    doc = {
        "userId": request.user_data.get('user_id'),
        "userName": request.user_data.get('name'),
        "societyId": request.user_data.get('societyId'),
        "documentType": data.get("documentType"),
        "fileName": data.get("fileName"),
        "fileData": data.get("fileData"), # Base64
        "status": "Submitted",
        "createdAt": datetime.utcnow().isoformat()
    }
    documents_col.insert_one(doc)
    return jsonify({"message": "Document uploaded successfully"}), 201

@vault_bp.route('/vault/my-documents', methods=['GET'])
@token_required
def get_my_vault_docs():
    u_id = request.user_data.get('user_id')
    docs = list(documents_col.find({"userId": u_id}).sort("createdAt", -1))
    return jsonify([format_doc(d) for d in docs])
