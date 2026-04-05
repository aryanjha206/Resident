from flask import Blueprint, request, jsonify
from datetime import datetime
from config import db, users_col, complaints_col, payments_col, visitors_col, bookings_col, orders_col, format_doc
from middleware import token_required

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics', methods=['GET'])
@token_required
def get_analytics():
    society_id = request.user_data.get('societyId')
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    
    if role == 'admin':
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
    else:
        query = {"societyId": society_id}
        
    total_users = users_col.count_documents(query)
    total_complaints = complaints_col.count_documents(query)
    pending_complaints = complaints_col.count_documents({**query, "status": "Pending"})
    resolved_complaints = complaints_col.count_documents({**query, "status": "Resolved"})
    
    # Financials
    dues = list(payments_col.find(query))
    collected = sum([float(d.get('amount', 0)) for d in dues if d.get('status') == 'Paid'])
    pending = sum([float(d.get('amount', 0)) for d in dues if d.get('status') == 'Pending'])

    # Marketplace Sales
    orders = list(orders_col.find(query))
    total_sales = sum([o.get('price', 0) for o in orders if o.get('paymentStatus') == 'Paid'])
    
    return jsonify({
        "users": total_users,
        "complaints": total_complaints,
        "complaintStatus": {"Pending": pending_complaints, "Resolved": resolved_complaints},
        "financials": {"collected": collected, "pending": pending},
        "marketplace": {"totalSales": total_sales},
        "visitorsToday": visitors_col.count_documents({**query, "expectedDate": {"$regex": "^" + datetime.utcnow().strftime('%Y-%m-%d')}}),
        "activeBookings": bookings_col.count_documents({**query, "status": "Confirmed"})
    })
