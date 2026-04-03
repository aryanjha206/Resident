from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import jwt
import smtplib
from email.mime.text import MIMEText
import random
import os
from functools import wraps
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'society-hub-2026-secret')
MONGODB_URI = os.environ.get('MONGODB_URI')

try:
    client = MongoClient(MONGODB_URI)
    db = client['society_hub']
    
    users_col = db['users'] 
    notices_col = db['notices']
    payments_col = db['payments']
    complaints_col = db['complaints']
    services_col = db['services']
    properties_col = db['properties']
    otps_col = db['otps']
    societies_col = db['societies']
    visitors_col = db['visitors']
    bookings_col = db['bookings']
    polls_col = db['polls']
    sos_col = db['sos']
    vehicles_col = db['vehicles']
    products_col = db['products']
    orders_col = db['orders']
    messages_col = db['messages']
    attendance_col = db['attendance']
    documents_col = db['documents']
    print("Connected to MongoDB database successfully!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

def format_doc(doc):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    if doc and 'societyId' in doc and type(doc['societyId']) == ObjectId:
        doc['societyId'] = str(doc['societyId'])
    return doc

# -------------- MIDDLEWARE --------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            token = token.split(" ")[1] # Bearer Token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_data = data
        except Exception as e:
            return jsonify({'error': 'Token is invalid'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            if data.get('role') != 'admin':
                return jsonify({'error': 'Admin privileges required'}), 403
            request.user_data = data
        except Exception as e:
            return jsonify({'error': 'Token is invalid'}), 401
        return f(*args, **kwargs)
    return decorated

# -------------- AUTHENTICATION & OTP --------------

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

def send_otp_email(recipient_email, otp):
    msg = MIMEText(f"Your Society Hub verification OTP is: {otp}. Valid for 10 minutes.")
    msg['Subject'] = 'Login/Signup Verification OTP'
    msg['From'] = EMAIL_HOST_USER
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.sendmail(EMAIL_HOST_USER, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    if not email: return jsonify({"error": "Email required"}), 400
        
    otp = str(random.randint(100000, 999999))
    otps_col.update_one({"email": email}, {"$set": {"otp": otp, "createdAt": datetime.utcnow()}}, upsert=True)
    
    success = send_otp_email(email, otp)
    if success: return jsonify({"message": "OTP sent"})
    return jsonify({"error": "Failed to send OTP email"}), 500

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    name = data.get('name') 
    society_code = data.get('societyCode')
    
    record = otps_col.find_one({"email": email, "otp": otp})
    if not record: return jsonify({"error": "Invalid or expired OTP"}), 401
    
    user = users_col.find_one({"email": email})
    if not user:
        if not society_code:
            return jsonify({"error": "Society Code is required for new signup"}), 400
        if not name:
            return jsonify({"error": "Name is required for new signup"}), 400
            
        society = societies_col.find_one({"code": society_code})
        if not society:
            return jsonify({"error": "Invalid Society Code"}), 404
            
        new_user = {
            "email": email,
            "name": name,
            "role": "resident",
            "societyId": str(society["_id"]),
            "societyName": society["name"],
            "joinedAt": datetime.utcnow().isoformat()
        }
        res = users_col.insert_one(new_user)
        user = users_col.find_one({"_id": res.inserted_id})

    # Delete OTP only after full verification and user validation is successful
    otps_col.delete_one({"_id": record["_id"]})
        
    token = jwt.encode(
        {'user_id': str(user['_id']), 'name': user.get('name', ''), 'role': user.get('role', 'resident'), 'societyId': str(user.get('societyId', ''))}, 
        app.config['SECRET_KEY'], algorithm='HS256'
    )
    return jsonify({"token": token, "user": format_doc(user)})

@app.route('/api/users/<u_id>', methods=['DELETE'])
@admin_required
def delete_user(u_id):
    users_col.delete_one({"_id": ObjectId(u_id)})
    return jsonify({"message": "User removed from society records"})

@app.route('/api/auth/admin-login', methods=['POST'])
def admin_login():
    data = request.json
    if data.get('pin') == "88786":
        token = jwt.encode({'role': 'admin', 'exp': datetime.utcnow().timestamp() + 86400}, app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({"token": token, "role": "admin"})
    return jsonify({"error": "Invalid PIN"}), 401

@app.route('/api/auth/seller-login', methods=['POST'])
def seller_login():
    data = request.json
    if data.get('pin') == "55555":
        # Global Vendor User
        payload = {
            'user_id': 'MODERATOR_VENDOR',
            'role': 'seller',
            'name': 'Verified Marketplace Vendor',
            'exp': datetime.utcnow().timestamp() + 86400
        }
        token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({"token": token, "role": "seller", "name": "Verified Marketplace Vendor"})
    return jsonify({"error": "Invalid PIN"}), 401

@app.route('/api/auth/guard-login', methods=['POST'])
def guard_login():
    data = request.json
    if data.get('pin') == "11111":
        token = jwt.encode({'role': 'guard', 'exp': datetime.utcnow().timestamp() + 86400}, app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({"token": token, "role": "guard"})
    return jsonify({"error": "Invalid PIN"}), 401

# -------------- ADMIN: SOCIETIES MODULE --------------
@app.route('/api/admin/societies', methods=['GET'])
@admin_required
def get_societies():
    societies = list(societies_col.find().sort("createdAt", -1))
    return jsonify([format_doc(s) for s in societies])

@app.route('/api/admin/societies', methods=['POST'])
@admin_required
def create_society():
    data = request.json
    name = data.get('name')
    if not name: return jsonify({"error": "Name required"}), 400
    
    code = f"SOC-{random.randint(1000,9999)}"
    society = {
        "name": name,
        "code": code,
        "address": data.get('address', ''),
        "createdAt": datetime.utcnow().isoformat()
    }
    societies_col.insert_one(society)
    return jsonify({"message": "Society created", "code": code}), 201

@app.route('/api/users/profile', methods=['PUT'])
@token_required
def update_profile():
    user_id = request.user_data.get('user_id')
    data = request.json
    
    # Ownership/Rent transfer logic: Update the resident to become a 'Transfer/Rent' flag or just update details
    update_data = {}
    if 'role' in data: update_data['role'] = data['role'] # 'resident' or 'tenant'
    if 'name' in data: update_data['name'] = data['name']
    
    users_col.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    return jsonify({"message": "Profile updated successfully"})

# -------------- USERS DIRECTORY MODULE --------------
@app.route('/api/users', methods=['GET'])
@token_required
def get_users():
    society_id = request.user_data.get('societyId')
    if request.user_data.get('role') == 'admin':
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
    else:
        query = {"societyId": society_id}
    
    users = list(users_col.find(query).sort("joinedAt", 1))
    return jsonify([format_doc(u) for u in users])

# -------------- USER/RESIDENT ENDPOINTS --------------
@app.route('/api/notices', methods=['GET'])
@token_required
def get_notices():
    society_id = request.user_data.get('societyId')
    query = {"societyId": society_id} if society_id else {} # Admin sees all if no societyId, but let's restrict to societyId
    if request.user_data.get('role') == 'admin' and not society_id:
        # Admin fetching all notices
        notices = list(notices_col.find().sort("date", -1))
    else:
        notices = list(notices_col.find(query).sort("date", -1))
    return jsonify([format_doc(n) for n in notices])

@app.route('/api/notices', methods=['POST'])
@admin_required
def add_notice():
    data = request.json
    society_id = data.get("societyId") # Admin must specify which society
    if not society_id: return jsonify({"error": "Society ID required"}), 400
    
    notice = {
        "societyId": society_id,
        "title": data.get("title"),
        "content": data.get("content"),
        "category": data.get("category", "General"),
        "date": datetime.utcnow().isoformat()
    }
    notices_col.insert_one(notice)
    return jsonify({"message": "Notice added"}), 201

@app.route('/api/notices/<n_id>', methods=['PUT'])
@admin_required
def update_notice(n_id):
    data = request.json
    notices_col.update_one({"_id": ObjectId(n_id)}, {"$set": {
        "title": data.get("title"),
        "content": data.get("content"),
        "category": data.get("category", "General")
    }})
    return jsonify({"message": "Notice updated"})

@app.route('/api/notices/<n_id>', methods=['DELETE'])
@admin_required
def delete_notice(n_id):
    notices_col.delete_one({"_id": ObjectId(n_id)})
    return jsonify({"message": "Notice deleted"})

@app.route('/api/complaints', methods=['GET'])
@token_required
def get_complaints():
    society_id = request.user_data.get('societyId')
    if request.user_data.get('role') == 'admin':
        # Admin gets all or filter by query param
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
        complaints = list(complaints_col.find(query).sort("date", -1))
    else:
        user_id = request.user_data.get('user_id')
        complaints = list(complaints_col.find({"societyId": society_id, "userId": user_id}).sort("date", -1))
    return jsonify([format_doc(c) for c in complaints])

@app.route('/api/complaints', methods=['POST'])
@token_required
def add_complaint():
    data = request.json
    society_id = request.user_data.get('societyId')
    user_id = request.user_data.get('user_id')
    user_name = request.user_data.get('name', 'Resident')
    if not society_id: return jsonify({"error": "User does not belong to a society"}), 400
    
    complaint = {
        "societyId": society_id,
        "userId": user_id,
        "userName": user_name,
        "category": data.get("category"),
        "description": data.get("description"),
        "status": "Pending",
        "date": datetime.utcnow().isoformat()
    }
    complaints_col.insert_one(complaint)
    return jsonify({"message": "Complaint raised"}), 201

@app.route('/api/complaints/<c_id>/status', methods=['PUT'])
@admin_required
def update_complaint_status(c_id):
    data = request.json
    complaints_col.update_one({"_id": ObjectId(c_id)}, {"$set": {"status": data.get("status")}})
    return jsonify({"message": "Status updated"})

@app.route('/api/dues', methods=['GET'])
@token_required
def get_dues():
    society_id = request.user_data.get('societyId')
    user_id = request.user_data.get('user_id')
    
    if request.user_data.get('role') == 'admin':
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
    else:
        query = {"userId": user_id, "societyId": society_id}
        
    dues = list(payments_col.find(query).sort("dueDate", 1))
    return jsonify([format_doc(d) for d in dues])

@app.route('/api/dues/bulk', methods=['POST'])
@admin_required
def add_bulk_dues():
    data = request.json
    society_id = data.get('societyId')
    total_amount = float(data.get('totalAmount', 0))
    due_date = data.get('dueDate')
    
    if not society_id or total_amount <= 0 or not due_date:
        return jsonify({"error": "Missing parameters"}), 400
        
    residents = list(users_col.find({"societyId": society_id, "role": "resident"}))
    if not residents:
        return jsonify({"error": "No residents found in this society to split among"}), 400
        
    split_amt = round(total_amount / len(residents), 2)
    due_records = []
    
    for r in residents:
        due_records.append({
            "societyId": society_id,
            "userId": str(r["_id"]),
            "userName": r.get("name", "Resident"),
            "amount": split_amt,
            "type": "Maintenance",
            "status": "Pending",
            "dueDate": due_date,
            "createdAt": datetime.utcnow().isoformat()
        })
        
    if due_records:
        payments_col.insert_many(due_records)
        
    return jsonify({"message": f"Successfully generated dues of ₹{split_amt} for {len(residents)} residents."}), 201

@app.route('/api/dues/<d_id>/pay', methods=['PUT'])
@token_required
def pay_due(d_id):
    payments_col.update_one({"_id": ObjectId(d_id)}, {"$set": {"status": "Paid"}})
    return jsonify({"message": "Payment successful"})

# -------------- SERVICES / HELPDESK MODULE --------------
@app.route('/api/services', methods=['GET'])
@token_required
def get_services():
    society_id = request.user_data.get('societyId')
    if request.user_data.get('role') == 'admin':
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
    else:
        query = {"societyId": society_id}
        
    services = list(services_col.find(query).sort("name", 1))
    return jsonify([format_doc(s) for s in services])

@app.route('/api/services', methods=['POST'])
@admin_required
def add_service():
    data = request.json
    society_id = data.get('societyId')
    if not society_id: return jsonify({"error": "Society ID required"}), 400
    
    service = {
        "societyId": society_id,
        "name": data.get("name"),
        "role": data.get("role"),
        "phone": data.get("phone"),
        "category": data.get("category", "Essential")
    }
    services_col.insert_one(service)
    return jsonify({"message": "Service added"})

# -------------- STAFF & ATTENDANCE MODULE --------------
@app.route('/api/staff/attendance', methods=['POST'])
def log_staff_attendance():
    data = request.json
    staff_id = data.get('staffId')
    action = data.get('action') # 'In' or 'Out'
    
    if not staff_id or action not in ['In', 'Out']:
        return jsonify({"error": "Staff ID and action (In/Out) required"}), 400
        
    log = {
        "staffId": staff_id,
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    }
    attendance_col.insert_one(log)
    
    # Update current status in services_col
    services_col.update_one({"_id": ObjectId(staff_id)}, {"$set": {"status": "Present" if action == 'In' else "Absent"}})
    
    return jsonify({"message": f"Staff marked {action} successfully"})

@app.route('/api/staff/<s_id>/history', methods=['GET'])
@token_required
def get_staff_history(s_id):
    history = list(attendance_col.find({"staffId": s_id}).sort("timestamp", -1))
    return jsonify([format_doc(h) for h in history])

@app.route('/api/staff/verify', methods=['POST'])
def verify_staff():
    # Similar to visitor verification for guards
    phone = request.json.get('phone')
    staff = services_col.find_one({"phone": phone})
    if not staff:
        return jsonify({"error": "Staff not registered"}), 404
        
    return jsonify({
        "staffId": str(staff["_id"]),
        "name": staff["name"],
        "role": staff["role"],
        "status": staff.get("status", "Absent")
    })

# -------------- VISITOR / SECURITY ENGINE --------------
@app.route('/api/visitors', methods=['GET'])
@token_required
def get_visitors():
    society_id = request.user_data.get('societyId')
    user_id = request.user_data.get('user_id')
    
    if request.user_data.get('role') == 'admin':
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
    else:
        query = {"userId": user_id, "societyId": society_id}
        
    visitors = list(visitors_col.find(query).sort("date", -1))
    return jsonify([format_doc(v) for v in visitors])

@app.route('/api/visitors', methods=['POST'])
@token_required
def add_visitor():
    data = request.json
    society_id = request.user_data.get('societyId')
    user_id = request.user_data.get('user_id')
    user_name = request.user_data.get('name', 'Resident')
    if not society_id: return jsonify({"error": "No Society scope"}), 400
    
    visitor = {
        "societyId": society_id,
        "userId": user_id,
        "userName": user_name,
        "visitorName": data.get("visitorName"),
        "purpose": data.get("purpose", "Guest"),
        "expectedDate": data.get("expectedDate"),
        "status": "Expected", 
        "passCode": f"{random.randint(100000, 999999)}",
        "date": datetime.utcnow().isoformat()
    }
    visitors_col.insert_one(visitor)
    return jsonify({"message": "Gate Pass Issued", "passCode": visitor["passCode"]}), 201
    
@app.route('/api/visitors/<v_id>/check-in', methods=['PUT'])
def check_in_visitor(v_id):
    # Publicly accessible endpoint for the Security Guard app to update Entry status
    res = visitors_col.update_one({"_id": ObjectId(v_id)}, {"$set": {"status": "Entered"}})
    if res.modified_count > 0:
        return jsonify({"message": "Visitor marked as ENTERED."})
    return jsonify({"error": "Failed to update visitor"}), 400

@app.route('/api/visitors/<v_id>/check-out', methods=['PUT'])
def check_out_visitor(v_id):
    res = visitors_col.update_one({"_id": ObjectId(v_id)}, {"$set": {"status": "Exited"}})
    if res.modified_count > 0:
        return jsonify({"message": "Visitor marked as EXITED."})
    return jsonify({"error": "Failed to update visitor"}), 400

@app.route('/api/security/verify-pass', methods=['POST'])
def verify_pass():
    # Allows a guard to scan/type a passcode and fetch visitor mapping
    pass_code = request.json.get('passCode')
    if not pass_code: return jsonify({"error": "Pass Code required"}), 400
    
    visitor = visitors_col.find_one({"passCode": pass_code, "status": {"$in": ["Expected", "Entered"]}})
    if not visitor:
        return jsonify({"error": "Invalid, Expired, or Already Exited Pass Code"}), 404
        
    society = societies_col.find_one({"_id": ObjectId(visitor["societyId"])})
    soc_name = society["name"] if society else "Unknown Society"
    
    return jsonify({
        "visitorId": str(visitor["_id"]),
        "visitorName": visitor["visitorName"],
        "purpose": visitor["purpose"],
        "residentName": visitor["userName"],
        "societyName": soc_name,
        "status": visitor["status"]
    })

@app.route('/api/bookings', methods=['GET', 'POST'])
@token_required
def manage_bookings():
    user_id = request.user_data.get('user_id')
    society_id = request.user_data.get('societyId')
    
    if request.method == 'POST':
        data = request.json
        if not data.get('facility') or not data.get('date'):
            return jsonify({"error": "Missing booking details"}), 400
            
        # Check for conflict to prevent double-booking the exact same slot
        conflict = bookings_col.find_one({
            "societyId": society_id, 
            "facility": data.get('facility'), 
            "date": data.get('date'), 
            "slot": data.get('slot'),
            "status": "Confirmed"
        })
        if conflict: return jsonify({"error": "Time slot already booked by another resident"}), 409
        
        booking = {
            "userId": user_id,
            "societyId": society_id,
            "userName": request.user_data.get('name'),
            "facility": data.get('facility'),
            "date": data.get('date'),
            "slot": data.get('slot'),
            "guests": data.get('guests', 1),
            "status": "Confirmed"
        }
        bookings_col.insert_one(booking)
        return jsonify({"message": "Booking Confirmed!"}), 201

    if request.user_data.get('role') == 'admin':
        soc_filter = request.args.get('societyId')
        query = {"societyId": soc_filter} if soc_filter else {}
    else:
        query = {"userId": user_id, "societyId": society_id}
        
    bookings = list(bookings_col.find(query).sort("date", -1))
    return jsonify([format_doc(b) for b in bookings])

@app.route('/api/bookings/<b_id>', methods=['DELETE'])
@token_required
def cancel_booking(b_id):
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    
    if role == 'admin':
        res = bookings_col.delete_one({"_id": ObjectId(b_id)})
    else:
        res = bookings_col.delete_one({"_id": ObjectId(b_id), "userId": user_id})
        
    if res.deleted_count > 0:
        return jsonify({"message": "Booking canceled successfully"})
    return jsonify({"error": "Failed to cancel booking (not found or unauthorized)"}), 400

@app.route('/api/analytics', methods=['GET'])
@token_required
def get_analytics():
    society_id = request.user_data.get('societyId')
    
    if request.user_data.get('role') == 'admin':
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
        u_query = {"societyId": society_filter} if society_filter else {}
        my_complaints_query = query
        my_dues_query = query
    else:
        query = {"societyId": society_id}
        u_query = {"societyId": society_id}
        my_complaints_query = {"userId": request.user_data.get('user_id'), "societyId": society_id}
        my_dues_query = {"userId": request.user_data.get('user_id'), "societyId": society_id}
        
    total_users = users_col.count_documents(u_query)
    total_complaints = complaints_col.count_documents(query)
    pending_complaints = complaints_col.count_documents({**query, "status": "Pending"})
    my_pending_complaints = complaints_col.count_documents({**my_complaints_query, "status": "Pending"})
    resolved_complaints = complaints_col.count_documents({**query, "status": "Resolved"})
    
    society_dues = list(payments_col.find(query))
    society_collected = sum([float(d.get('amount', 0)) for d in society_dues if d.get('status') == 'Paid'])
    society_pending = sum([float(d.get('amount', 0)) for d in society_dues if d.get('status') == 'Pending'])

    my_dues = list(payments_col.find(my_dues_query))
    my_pending = sum([float(d.get('amount', 0)) for d in my_dues if d.get('status') == 'Pending'])

    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    today_visitors = visitors_col.count_documents({**query, "date": {"$regex": "^" + today_str}})
    total_bookings = bookings_col.count_documents(query)

    # Marketplace Sales Detail
    orders = list(orders_col.find(query))
    total_sales = sum([o.get('price', 0) for o in orders if o.get('paymentStatus') == 'Paid'])
    
    # Simple Aggregate performance (Top Categories)
    cat_performance = {}
    for o in orders:
        if o.get('paymentStatus') == 'Paid':
            cat = o.get('category', 'General')
            cat_performance[cat] = cat_performance.get(cat, 0) + o.get('price', 0)
    
    return jsonify({
        "total_users": total_users,
        "total_complaints": total_complaints,
        "pending_complaints": pending_complaints,
        "my_pending_complaints": my_pending_complaints,
        "resolved_complaints": resolved_complaints,
        "dues_collected": society_collected,
        "dues_pending": society_pending,
        "my_dues_pending": my_pending,
        "today_visitors": today_visitors,
        "total_bookings": total_bookings,
        "market_revenue": total_sales,
        "category_stats": cat_performance
    })

# -------------- POLLS / SURVEYS MODULE --------------
@app.route('/api/polls', methods=['GET'])
@token_required
def get_polls():
    society_id = request.user_data.get('societyId')
    if request.user_data.get('role') == 'admin':
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
    else:
        query = {"societyId": society_id}
        
    polls = list(polls_col.find(query).sort("createdAt", -1))
    return jsonify([format_doc(p) for p in polls])

@app.route('/api/polls', methods=['POST'])
@admin_required
def create_poll():
    data = request.json
    society_id = data.get('societyId')
    if not society_id: return jsonify({"error": "Society ID required"}), 400
    
    poll = {
        "societyId": society_id,
        "question": data.get("question"),
        "options": [{"text": opt, "votes": 0} for opt in data.get("options", [])],
        "voters": [],
        "voters_v2": [], # [{uid, opt}, ...]
        "createdAt": datetime.utcnow().isoformat(),
        "expiresAt": data.get("expiresAt")
    }
    polls_col.insert_one(poll)
    return jsonify({"message": "Poll created"}), 201

@app.route('/api/polls/<p_id>', methods=['PUT', 'DELETE'])
@admin_required
def manage_poll(p_id):
    if request.method == 'DELETE':
        polls_col.delete_one({"_id": ObjectId(p_id)})
        return jsonify({"message": "Poll deleted"})
    
    data = request.json
    update_data = {"question": data.get("question")}
    if "options" in data:
        update_data["options"] = [{"text": opt, "votes": 0} for opt in data.get("options", [])]
    
    polls_col.update_one({"_id": ObjectId(p_id)}, {"$set": update_data})
    return jsonify({"message": "Poll updated"})

@app.route('/api/polls/<p_id>/vote', methods=['POST'])
@token_required
def vote_poll(p_id):
    user_id = request.user_data.get('user_id')
    option_index = request.json.get('optionIndex')
    
    poll = polls_col.find_one({"_id": ObjectId(p_id)})
    if not poll: return jsonify({"error": "Poll not found"}), 404
    
    # Check both old and new formats
    if user_id in poll.get('voters', []) or any(v.get('uid') == user_id for v in poll.get('voters_v2', [])):
        return jsonify({"error": "Already voted"}), 400
        
    polls_col.update_one(
        {"_id": ObjectId(p_id)},
        {
            "$inc": {f"options.{option_index}.votes": 1},
            "$push": {"voters_v2": {"uid": user_id, "opt": option_index}}
        }
    )
    return jsonify({"message": "Vote recorded"}), 200

@app.route('/api/polls/<p_id>/vote', methods=['DELETE'])
@token_required
def retract_vote(p_id):
    user_id = request.user_data.get('user_id')
    poll = polls_col.find_one({"_id": ObjectId(p_id)})
    if not poll: return jsonify({"error": "Poll not found"}), 404
    
    found_vote = next((v for v in poll.get('voters_v2', []) if v.get('uid') == user_id), None)
    if not found_vote:
        return jsonify({"error": "No vote found to retract"}), 400
        
    polls_col.update_one(
        {"_id": ObjectId(p_id)},
        {
            "$inc": {f"options.{found_vote['opt']}.votes": -1},
            "$pull": {"voters_v2": {"uid": user_id}}
        }
    )
    return jsonify({"message": "Vote retracted"})

# -------------- EMERGENCY / SOS MODULE --------------
@app.route('/api/sos', methods=['POST'])
@token_required
def trigger_sos():
    society_id = request.user_data.get('societyId')
    user_id = request.user_data.get('user_id')
    user_name = request.user_data.get('name')
    
    sos_alert = {
        "societyId": society_id,
        "userId": user_id,
        "userName": user_name,
        "location": request.json.get('location', 'Unknown'),
        "status": "Active",
        "createdAt": datetime.utcnow().isoformat()
    }
    sos_col.insert_one(sos_alert)
    return jsonify({"message": "SOS Alert Broadcasted! Help is on the way."}), 201

@app.route('/api/sos', methods=['GET'])
def get_sos_alerts():
    # Allow Guards (no societyId restriction for now or logic to handle it)
    alerts = list(sos_col.find({"status": "Active"}).sort("createdAt", -1))
    return jsonify([format_doc(a) for a in alerts])

@app.route('/api/sos/<s_id>/resolve', methods=['PUT'])
@admin_required
def resolve_sos(s_id):
    sos_col.update_one({"_id": ObjectId(s_id)}, {"$set": {"status": "Resolved"}})
    return jsonify({"message": "SOS Alert Resolved"})

# -------------- VEHICLE REGISTRY MODULE --------------
@app.route('/api/vehicles', methods=['GET'])
@token_required
def get_vehicles():
    society_id = request.user_data.get('societyId')
    user_id = request.user_data.get('user_id')
    
    if request.user_data.get('role') == 'admin':
        society_filter = request.args.get('societyId')
        query = {"societyId": society_filter} if society_filter else {}
    else:
        query = {"userId": user_id, "societyId": society_id}
        
    vehicles = list(vehicles_col.find(query).sort("createdAt", -1))
    return jsonify([format_doc(v) for v in vehicles])

@app.route('/api/vehicles', methods=['POST'])
@token_required
def add_vehicle():
    society_id = request.user_data.get('societyId')
    user_id = request.user_data.get('user_id')
    data = request.json
    
    vehicle = {
        "societyId": society_id,
        "userId": user_id,
        "userName": request.user_data.get('name'),
        "vehicleNumber": data.get("vehicleNumber"),
        "vehicleType": data.get("vehicleType"), # Car, Bike, etc.
        "model": data.get("model"),
        "parkingSlot": data.get("parkingSlot"),
        "createdAt": datetime.utcnow().isoformat()
    }
    vehicles_col.insert_one(vehicle)
    return jsonify({"message": "Vehicle registered"}), 201

@app.route('/api/vehicles/<v_id>', methods=['PUT', 'DELETE'])
@token_required
def manage_vehicle(v_id):
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    
    vehicle = vehicles_col.find_one({"_id": ObjectId(v_id)})
    if not vehicle: return jsonify({"error": "Vehicle not found"}), 404
    
    if role != 'admin' and str(vehicle.get('userId')) != user_id:
        return jsonify({"error": "Unauthorized to manage this vehicle"}), 403

    if request.method == 'DELETE':
        vehicles_col.delete_one({"_id": ObjectId(v_id)})
        return jsonify({"message": "Vehicle removed successfully"})
    
    data = request.json
    update_data = {
        "vehicleNumber": data.get("vehicleNumber"),
        "vehicleType": data.get("vehicleType"),
        "model": data.get("model"),
        "parkingSlot": data.get("parkingSlot")
    }
    vehicles_col.update_one({"_id": ObjectId(v_id)}, {"$set": update_data})
    return jsonify({"message": "Vehicle updated successfully"})

# -------------- MARKETPLACE MODULE --------------
@app.route('/api/marketplace/products', methods=['GET'])
@token_required
def get_products():
    society_id = request.user_data.get('societyId')
    # Fetch products that belong to this society, OR global products (societyId is None/missing)
    products = list(products_col.find({
        "status": "Active",
        "$or": [
            {"societyId": society_id},
            {"societyId": None},
            {"societyId": {"$exists": False}}
        ]
    }).sort("createdAt", -1))
    return jsonify([format_doc(p) for p in products])

@app.route('/api/marketplace/seller/products', methods=['GET'])
@token_required
def get_seller_products():
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    society_filter = request.args.get('societyId')
    
    if role == 'admin':
        query = {"status": {"$ne": "Deleted"}}
        if society_filter: query["societyId"] = society_filter
    else:
        query = {"userId": user_id}
        
    products = list(products_col.find(query).sort("createdAt", -1))
    return jsonify([format_doc(p) for p in products])

@app.route('/api/marketplace/products', methods=['POST'])
@token_required
def add_product():
    user_id = request.user_data.get('user_id')
    user_name = request.user_data.get('name')
    society_id = request.user_data.get('societyId')
    data = request.json
    product = {
        "userId": user_id,
        "sellerName": user_name,
        "societyId": society_id,
        "name": data.get("name"),
        "price": float(data.get("price", 0)),
        "description": data.get("description"),
        "category": data.get("category", "General"),
        "image": data.get("image", "https://img.icons8.com/color/96/box--v1.png"),
        "status": "Active",
        "createdAt": datetime.utcnow().isoformat()
    }
    products_col.insert_one(product)
    return jsonify({"message": "Product listed successfully"}), 201

@app.route('/api/marketplace/products/<p_id>', methods=['PUT'])
@token_required
def update_product(p_id):
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    data = request.json
    
    product = products_col.find_one({"_id": ObjectId(p_id)})
    if not product:
        return jsonify({"error": "Product not found"}), 404
        
    if role != 'admin' and product.get('userId') != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    update_fields = {
        "name": data.get("name"),
        "price": float(data.get("price", 0)) if data.get("price") else None,
        "description": data.get("description"),
        "category": data.get("category"),
        "image": data.get("image")
    }
    update_fields = {k: v for k, v in update_fields.items() if v is not None}
    products_col.update_one({"_id": ObjectId(p_id)}, {"$set": update_fields})
    return jsonify({"message": "Product updated successfully"})

@app.route('/api/marketplace/products/<p_id>', methods=['DELETE'])
@token_required
def delete_product(p_id):
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    
    product = products_col.find_one({"_id": ObjectId(p_id)})
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if role == 'admin':
        products_col.delete_one({"_id": ObjectId(p_id)})
        return jsonify({"message": "Product removed from marketplace by admin"})
    
    if product.get('userId') != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Soft delete for sellers
    products_col.update_one({"_id": ObjectId(p_id)}, {"$set": {"status": "Deleted"}})
    return jsonify({"message": "Product hidden by seller"})

@app.route('/api/marketplace/orders', methods=['POST'])
@token_required
def place_order():
    user_id = request.user_data.get('user_id')
    user_name = request.user_data.get('name')
    society_id = request.user_data.get('societyId')
    data = request.json
    
    # Get product to find the seller
    p_id = data.get("productId")
    product = products_col.find_one({"_id": ObjectId(p_id)})
    seller_id = product.get('userId') if product else None
    
    order = {
        "userId": user_id,
        "userName": user_name,
        "societyId": society_id,
        "sellerId": seller_id,
        "productId": p_id,
        "productName": data.get("productName"),
        "productImage": data.get("productImage", ""),
        "category": data.get("category", "General"),
        "price": data.get("price"),
        "status": "Placed",
        "paymentStatus": "Pending",
        "timeline": [{"status": "Placed", "time": datetime.utcnow().isoformat()}],
        "createdAt": datetime.utcnow().isoformat()
    }
    orders_col.insert_one(order)
    return jsonify({"message": "Order placed successfully"}), 201

@app.route('/api/marketplace/orders', methods=['GET'])
@token_required
def get_orders():
    user_id = request.user_data.get('user_id')
    orders = list(orders_col.find({"userId": user_id}).sort("createdAt", -1))
    return jsonify([format_doc(o) for o in orders])

@app.route('/api/marketplace/seller/orders', methods=['GET'])
@token_required
def get_seller_orders():
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    society_filter = request.args.get('societyId')

    if role == 'admin':
        query = {}
        if society_filter: query["societyId"] = society_filter
    else:
        query = {"sellerId": user_id}

    orders = list(orders_col.find(query).sort("createdAt", -1))
    return jsonify([format_doc(o) for o in orders])

@app.route('/api/marketplace/orders/<o_id>/status', methods=['PUT'])
@token_required
def update_order_status(o_id):
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    data = request.json
    new_status = data.get("status")
    
    order = orders_col.find_one({"_id": ObjectId(o_id)})
    if not order:
        return jsonify({"error": "Order not found"}), 404
        
    if role != 'admin' and order.get('sellerId') != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    update_fields = {"status": new_status}
    if new_status == "Delivered":
        update_fields["deliveredAt"] = datetime.utcnow().isoformat()
        
    orders_col.update_one(
        {"_id": ObjectId(o_id)},
        {
            "$set": update_fields,
            "$push": {"timeline": {"status": new_status, "time": datetime.utcnow().isoformat()}}
        }
    )
    return jsonify({"message": "Order status updated"})

@app.route('/api/marketplace/orders/<o_id>/pay', methods=['PUT'])
@token_required
def confirm_payment(o_id):
    user_id = request.user_data.get('user_id')
    role = request.user_data.get('role')
    
    order = orders_col.find_one({"_id": ObjectId(o_id)})
    if not order:
        return jsonify({"error": "Order not found"}), 404
        
    if role != 'admin' and order.get('sellerId') != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    orders_col.update_one(
        {"_id": ObjectId(o_id)},
        {
            "$set": {
                "paymentStatus": "Paid",
                "paidAt": datetime.utcnow().isoformat()
            },
            "$push": {"timeline": {"status": "Payment Confirmed", "time": datetime.utcnow().isoformat()}}
        }
    )
    return jsonify({"message": "Payment confirmed"})

# -------------- DIGITAL DOCUMENT VAULT --------------
@app.route('/api/vault/upload', methods=['POST'])
@token_required
def upload_document():
    user_id = request.user_data.get('user_id')
    user_name = request.user_data.get('name')
    society_id = request.user_data.get('societyId')
    data = request.json
    
    doc = {
        "userId": user_id,
        "userName": user_name,
        "societyId": society_id,
        "documentType": data.get("documentType"),
        "fileName": data.get("fileName"),
        "fileData": data.get("fileData"), # Base64
        "status": "Submitted",
        "createdAt": datetime.utcnow().isoformat()
    }
    documents_col.insert_one(doc)
    return jsonify({"message": "Document uploaded successfully"}), 201

@app.route('/api/vault/my-documents', methods=['GET'])
@token_required
def get_my_documents():
    user_id = request.user_data.get('user_id')
    docs = list(documents_col.find({"userId": user_id}).sort("createdAt", -1))
    return jsonify([format_doc(d) for d in docs])

@app.route('/api/admin/vault/all', methods=['GET'])
@admin_required
def get_all_documents():
    society_id = request.args.get('societyId')
    query = {}
    if society_id:
        query["societyId"] = society_id
    docs = list(documents_col.find(query).sort("createdAt", -1))
    return jsonify([format_doc(d) for d in docs])

# -------------- STAFF MANAGEMENT UPDATES --------------
@app.route('/api/services/<s_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_service(s_id):
    if request.method == 'DELETE':
        services_col.delete_one({"_id": ObjectId(s_id)})
        return jsonify({"message": "Staff removed"})
        
    data = request.json
    update_fields = {
        "name": data.get("name"),
        "role": data.get("role"),
        "phone": data.get("phone")
    }
    services_col.update_one({"_id": ObjectId(s_id)}, {"$set": update_fields})
    return jsonify({"message": "Staff details updated"})

@app.route('/api/marketplace/orders/<o_id>/invoice', methods=['GET'])
@token_required
def get_invoice(o_id):
    order = orders_col.find_one({"_id": ObjectId(o_id)})
    if not order:
        return jsonify({"error": "Order not found"}), 404
    invoice = {
        "invoiceId": f"INV-{str(order['_id'])[-6:].upper()}",
        "orderId": str(order['_id']),
        "productName": order.get("productName"),
        "price": order.get("price"),
        "buyerName": order.get("userName"),
        "status": order.get("status"),
        "paymentStatus": order.get("paymentStatus", "Pending"),
        "orderedOn": order.get("createdAt"),
        "deliveredOn": order.get("deliveredAt", ""),
        "paidOn": order.get("paidAt", "")
    }
    return jsonify(invoice)

# -------------- LIVE CHAT MODULE --------------
@app.route('/api/chat/messages', methods=['GET'])
@token_required
def get_messages():
    society_id = request.user_data.get('societyId')
    messages = list(messages_col.find({"societyId": society_id}).sort("createdAt", 1))
    return jsonify([format_doc(m) for m in messages])

@app.route('/api/chat/messages', methods=['POST'])
@token_required
def send_message():
    data = request.json
    message = {
        "societyId": request.user_data.get('societyId'),
        "userId": request.user_data.get('user_id'),
        "userName": request.user_data.get('name'),
        "text": data.get("text"),
        "createdAt": datetime.utcnow().isoformat()
    }
    messages_col.insert_one(message)
    return jsonify({"message": "Message sent"}), 201

if __name__ == '__main__':
    app.run(debug=True, port=5000)
