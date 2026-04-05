from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from routes import register_routes

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    
    # Register all modular routes
    register_routes(app)
    
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({"status": "CORE_ACTIVE", "version": "2.0.0-PROD"})

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
