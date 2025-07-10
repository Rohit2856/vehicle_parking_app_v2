from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from models import db, User, UserRole
from auth_routes import auth_bp
from dashboard_routes import dashboard_bp
from admin_lot_routes import admin_lot_bp  
from werkzeug.security import generate_password_hash

def create_app():
    # Create and configure Flask application
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for frontend integration
    CORS(app, resources={
        r"/auth/*": {"origins": "*"},
        r"/admin/*": {"origins": "*"},
        r"/user/*": {"origins": "*"}
    })
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_lot_bp)  # Register admin lot management blueprint
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Vehicle Parking App - Authentication System',
            'version': '2.0',
            'status': 'operational',
            'available_endpoints': {
                'authentication': ['/auth/register', '/auth/login', '/auth/verify'],
                'dashboards': ['/admin/dashboard', '/user/dashboard'],
                'profile': ['/profile'],
                'admin_management': ['/admin/lots', '/admin/spots', '/admin/users', '/admin/dashboard/summary']  # Added admin management endpoints
            }
        })
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'authentication': 'enabled',
            'admin_management': 'enabled'  # Added admin management status
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return jsonify({'error': 'Method not allowed'}), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

def setup_database(app):
    #Initialize database and create predefined admin user
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        # Create predefined admin 
        admin_user = User.query.filter_by(username='admin').first()
        
        if not admin_user:
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role=UserRole.admin
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Predefined admin user created successfully")
            print("Username: admin")
            print("Password: admin123")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    app = create_app()
    setup_database(app)
    print("Starting Vehicle Parking App...")
    app.run(debug=True, host='0.0.0.0', port=5000)

