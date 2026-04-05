from flask import Blueprint

def register_routes(app):
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.marketplace import marketplace_bp
    from routes.visitors import visitors_bp
    from routes.community import community_bp
    from routes.property import property_bp
    from routes.vault import vault_bp
    from routes.analytics import analytics_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(marketplace_bp, url_prefix='/api')
    app.register_blueprint(visitors_bp, url_prefix='/api')
    app.register_blueprint(community_bp, url_prefix='/api')
    app.register_blueprint(property_bp, url_prefix='/api')
    app.register_blueprint(vault_bp, url_prefix='/api')
    app.register_blueprint(analytics_bp, url_prefix='/api')
