import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'society-hub-2026-secret')
    MONGODB_URI = os.environ.get('MONGODB_URI')
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

client = MongoClient(Config.MONGODB_URI)
db = client['society_hub']

# Collections global
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

def format_doc(doc):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    if doc and 'societyId' in doc and type(doc['societyId']) == str:
        pass # already str
    from bson.objectid import ObjectId
    if doc and 'societyId' in doc and isinstance(doc['societyId'], ObjectId):
        doc['societyId'] = str(doc['societyId'])
    return doc
