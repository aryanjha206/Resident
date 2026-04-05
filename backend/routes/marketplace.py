from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from config import db, products_col, orders_col, format_doc
from middleware import token_required

marketplace_bp = Blueprint('marketplace', __name__)

@marketplace_bp.route('/marketplace/products', methods=['GET'])
@token_required
def get_products():
    p_list = list(products_col.find({"status": "Active"}).sort("createdAt", -1))
    return jsonify([format_doc(p) for p in p_list])

@marketplace_bp.route('/marketplace/products', methods=['POST'])
@token_required
def add_product():
    data = request.json
    p = {
        "sellerId": request.user_data.get('user_id'),
        "name": data.get('name'),
        "price": float(data.get('price', 0)),
        "category": data.get('category'),
        "image": data.get('image'),
        "status": "Active",
        "createdAt": datetime.utcnow().isoformat()
    }
    products_col.insert_one(p)
    return jsonify({"message": "Product active in market"})

@marketplace_bp.route('/marketplace/orders', methods=['POST'])
@token_required
def place_order():
    data = request.json
    order = {
        "userId": request.user_data.get('user_id'),
        "userName": request.user_data.get('name'),
        "societyId": request.user_data.get('societyId'),
        "productId": data.get('productId'),
        "productName": data.get('productName'),
        "price": data.get('price'),
        "sellerId": data.get('sellerId'),
        "status": "Pending",
        "paymentStatus": "Pending",
        "createdAt": datetime.utcnow().isoformat()
    }
    orders_col.insert_one(order)
    return jsonify({"message": "Order placed successfully"})

@marketplace_bp.route('/marketplace/my-orders', methods=['GET'])
@token_required
def get_my_orders():
    orders = list(orders_col.find({"userId": request.user_data.get('user_id')}).sort("createdAt", -1))
    return jsonify([format_doc(o) for o in orders])
