from flask import Blueprint, request, jsonify
import random, jwt, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from config import Config, users_col, otps_col, format_doc
from middleware import token_required

auth_bp = Blueprint('auth', __name__)

def send_otp_email(recipient_email, otp):
    msg = MIMEText(f"Your Society Hub verification OTP is: {otp}. Valid for 10 minutes.")
    msg['Subject'] = 'Login/Signup Verification OTP'
    msg['From'] = Config.EMAIL_HOST_USER
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(Config.EMAIL_HOST_USER, Config.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

@auth_bp.route('/auth/send-otp', methods=['POST'])
def send_otp():
    email = request.json.get('email')
    if not email: return jsonify({"error": "Email required"}), 400
    otp = str(random.randint(100000, 999999))
    otps_col.update_one({"email": email}, {"$set": {"otp": otp, "createdAt": datetime.utcnow()}}, upsert=True)
    if send_otp_email(email, otp):
        return jsonify({"message": "OTP sent to your email"})
    return jsonify({"error": "Failed to send OTP. Check SMTP settings."}), 500

@auth_bp.route('/auth/verify-otp', methods=['POST'])
def verify_otp():
    email = request.json.get('email')
    otp = request.json.get('otp')
    if not email or not otp: return jsonify({"error": "Fields missing"}), 400
    
    record = otps_col.find_one({"email": email, "otp": otp})
    if not record: return jsonify({"error": "Invalid or expired OTP"}), 401
    
    user = users_col.find_one({"email": email})
    if not user:
        new_user = {
            "email": email,
            "role": "resident",
            "joinedAt": datetime.utcnow().isoformat()
        }
        res = users_col.insert_one(new_user)
        user = users_col.find_one({"_id": res.inserted_id})

    otps_col.delete_one({"_id": record["_id"]})
    token = jwt.encode(
        {'user_id': str(user['_id']), 'name': user.get('name', ''), 'role': user.get('role', 'resident'), 'societyId': str(user.get('societyId', ''))}, 
        Config.SECRET_KEY, algorithm='HS256'
    )
    return jsonify({"token": token, "user": format_doc(user)})

@auth_bp.route('/auth/admin-login', methods=['POST'])
def admin_login():
    if request.json.get('pin') == "88786":
        token = jwt.encode({'role': 'admin', 'exp': datetime.utcnow().timestamp() + 86400}, Config.SECRET_KEY, algorithm='HS256')
        return jsonify({"token": token, "role": "admin"})
    return jsonify({"error": "Invalid PIN"}), 401

@auth_bp.route('/auth/seller-login', methods=['POST'])
def seller_login():
    if request.json.get('pin') == "55555":
        token = jwt.encode({'user_id': 'MODERATOR_VENDOR', 'role': 'seller', 'name': 'Verified Marketplace Vendor', 'exp': datetime.utcnow().timestamp() + 86400}, Config.SECRET_KEY, algorithm='HS256')
        return jsonify({"token": token, "role": "seller", "name": "Verified Marketplace Vendor"})
    return jsonify({"error": "Invalid PIN"}), 401

@auth_bp.route('/auth/guard-login', methods=['POST'])
def guard_login():
    if request.json.get('pin') == "11111":
        token = jwt.encode({'role': 'guard', 'exp': datetime.utcnow().timestamp() + 86400}, Config.SECRET_KEY, algorithm='HS256')
        return jsonify({"token": token, "role": "guard"})
    return jsonify({"error": "Invalid PIN"}), 401
