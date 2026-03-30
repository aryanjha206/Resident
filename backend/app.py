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

def seller_or_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            if data.get('role') not in ['seller', 'admin']:
                return jsonify({'error': 'Seller or admin privileges required'}), 403
            request.user_data = data
        except Exception:
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
        token = jwt.encode({'role': 'seller', 'exp': datetime.utcnow().timestamp() + 86400, 'name': 'Verified Seller'}, app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({"token": token, "role": "seller", "name": "Verified Seller"})
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
    user_id = request.user_data.get('user_id')
    society_id = request.user_data.get('societyId')
    query = {"_id": ObjectId(d_id)}
    if request.user_data.get('role') != 'admin':
        query.update({"userId": user_id, "societyId": society_id})
    res = payments_col.update_one(query, {"$set": {"status": "Paid", "paidAt": datetime.utcnow().isoformat()}})
    if res.matched_count == 0:
        return jsonify({"error": "Due not found or unauthorized"}), 404
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

    return jsonify({
        "total_users": total_users,
        "total_complaints": total_complaints,
        "pending_complaints": pending_complaints,
        "my_pending_complaints": my_pending_complaints,
        "resolved_complaints": resolved_complaints,
        "dues_collected": society_collected,
        "dues_pending": society_pending,
        "my_dues_pending": my_pending
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
        "createdAt": datetime.utcnow().isoformat(),
        "expiresAt": data.get("expiresAt")
    }
    polls_col.insert_one(poll)
    return jsonify({"message": "Poll created"}), 201

@app.route('/api/polls/<p_id>/vote', methods=['POST'])
@token_required
def vote_poll(p_id):
    user_id = request.user_data.get('user_id')
    option_index = request.json.get('optionIndex')
    
    poll = polls_col.find_one({"_id": ObjectId(p_id)})
    if not poll: return jsonify({"error": "Poll not found"}), 404
    
    if user_id in poll.get('voters', []):
        return jsonify({"error": "Already voted"}), 400
        
    polls_col.update_one(
        {"_id": ObjectId(p_id)},
        {
            "$inc": {f"options.{option_index}.votes": 1},
            "$push": {"voters": user_id}
        }
    )
    return jsonify({"message": "Vote recorded"})

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
@token_required
def get_sos_alerts():
    if request.user_data.get('role') == 'admin':
        society_filter = request.args.get('societyId')
        query = {"status": "Active"}
        if society_filter:
            query["societyId"] = society_filter
    else:
        society_id = request.user_data.get('societyId')
        query = {"societyId": society_id, "status": "Active"}
    alerts = list(sos_col.find(query).sort("createdAt", -1))
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

# -------------- MARKETPLACE MODULE --------------
@app.route('/api/marketplace/products', methods=['GET'])
@token_required
def get_products():
    products = list(products_col.find({"status": "Active"}).sort("createdAt", -1))
    return jsonify([format_doc(p) for p in products])

@app.route('/api/marketplace/seller/products', methods=['GET'])
@seller_or_admin_required
def get_seller_products():
    products = list(products_col.find().sort("createdAt", -1))
    return jsonify([format_doc(p) for p in products])

@app.route('/api/marketplace/products', methods=['POST'])
@seller_or_admin_required
def add_product():
    data = request.json
    product = {
        "name": data.get("name"),
        "price": float(data.get("price", 0)),
        "description": data.get("description"),
        "image": data.get("image", "https://img.icons8.com/color/96/box--v1.png"),
        "status": "Active",
        "createdAt": datetime.utcnow().isoformat()
    }
    products_col.insert_one(product)
    return jsonify({"message": "Product listed successfully"}), 201

@app.route('/api/marketplace/products/<p_id>', methods=['PUT'])
@seller_or_admin_required
def update_product(p_id):
    data = request.json
    update_fields = {}
    if data.get("name"): update_fields["name"] = data["name"]
    if data.get("price"): update_fields["price"] = float(data["price"])
    if data.get("description") is not None: update_fields["description"] = data["description"]
    if data.get("image"): update_fields["image"] = data["image"]
    if data.get("status"): update_fields["status"] = data["status"]
    try:
        res = products_col.update_one({"_id": ObjectId(p_id)}, {"$set": update_fields})
    except Exception:
        return jsonify({"error": "Invalid product id"}), 400
    if res.matched_count == 0:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"message": "Product updated"})

@app.route('/api/marketplace/products/<p_id>', methods=['DELETE'])
@seller_or_admin_required
def delete_product(p_id):
    try:
        res = products_col.delete_one({"_id": ObjectId(p_id)})
    except Exception:
        return jsonify({"error": "Invalid product id"}), 400
    if res.deleted_count == 0:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"message": "Product deleted"})

@app.route('/api/marketplace/seller/analytics', methods=['GET'])
@seller_or_admin_required
def seller_analytics():
    total_products = products_col.count_documents({})
    active_products = products_col.count_documents({"status": "Active"})
    all_orders = list(orders_col.find())
    total_orders = len(all_orders)
    total_revenue = sum(float(o.get("price", 0)) for o in all_orders)
    paid_orders = [o for o in all_orders if o.get("paymentStatus") == "Paid"]
    paid_revenue = sum(float(o.get("price", 0)) for o in paid_orders)
    pending_revenue = total_revenue - paid_revenue
    return jsonify({
        "totalProducts": total_products,
        "activeProducts": active_products,
        "totalOrders": total_orders,
        "totalRevenue": total_revenue,
        "paidRevenue": paid_revenue,
        "pendingRevenue": pending_revenue,
        "paidOrders": len(paid_orders),
        "pendingOrders": total_orders - len(paid_orders)
    })

@app.route('/api/marketplace/orders', methods=['POST'])
@token_required
def place_order():
    user_id = request.user_data.get('user_id')
    user_name = request.user_data.get('name')
    society_id = request.user_data.get('societyId')
    data = request.json
    product = None
    product_id = data.get("productId")
    if product_id:
        try:
            product = products_col.find_one({"_id": ObjectId(product_id)})
        except Exception:
            product = None
    
    order = {
        "userId": user_id,
        "userName": user_name,
        "societyId": society_id,
        "productId": product_id,
        "productName": data.get("productName") or (product or {}).get("name", ""),
        "productImage": data.get("productImage") or (product or {}).get("image", "https://img.icons8.com/color/96/box--v1.png"),
        "price": data.get("price") if data.get("price") is not None else float((product or {}).get("price", 0)),
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
@seller_or_admin_required
def get_seller_orders():
    orders = list(orders_col.find().sort("createdAt", -1))
    return jsonify([format_doc(o) for o in orders])

@app.route('/api/marketplace/orders/<o_id>/status', methods=['PUT'])
@seller_or_admin_required
def update_order_status(o_id):
    data = request.json
    new_status = data.get("status")
    update_fields = {"status": new_status}
    timeline_entries = [{"status": new_status, "time": datetime.utcnow().isoformat()}]
    if new_status == "Delivered":
        update_fields["deliveredAt"] = datetime.utcnow().isoformat()
        update_fields["paymentStatus"] = "Paid"
        update_fields["paidAt"] = datetime.utcnow().isoformat()
        timeline_entries.append({"status": "Payment Confirmed", "time": datetime.utcnow().isoformat()})
    res = orders_col.update_one(
        {"_id": ObjectId(o_id)},
        {
            "$set": update_fields,
            "$push": {"timeline": {"$each": timeline_entries}}
        }
    )
    if res.matched_count == 0:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({"message": "Order status updated"})

@app.route('/api/marketplace/orders/<o_id>/pay', methods=['PUT'])
@seller_or_admin_required
def confirm_payment(o_id):
    order = orders_col.find_one({"_id": ObjectId(o_id)})
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.get("paymentStatus") == "Paid":
        return jsonify({"message": "Payment already confirmed"})
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

@app.route('/api/marketplace/orders/<o_id>/invoice', methods=['GET'])
@token_required
def get_invoice(o_id):
    query = {"_id": ObjectId(o_id)}
    if request.user_data.get('role') != 'admin':
        query["userId"] = request.user_data.get('user_id')
    order = orders_col.find_one(query)
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
