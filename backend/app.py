from flask import Flask, jsonify, request, send_from_directory
from flask_mail import Mail
from config import Config
from models import db, User, UserRole
from auth_routes import auth_bp
from dashboard_routes import dashboard_bp
from admin_lot_routes import admin_lot_bp
from user_routes import user_bp
from analytics_routes import analytics_bp
from job_routes import job_bp
from werkzeug.security import generate_password_hash
from datetime import datetime
import subprocess
import sys
import os

def create_app():
    # Configure Flask to serve frontend files
    app = Flask(__name__, 
                static_folder='../frontend',  
                static_url_path='')           
    
    app.config.from_object(Config)
    # Initialize extensions
    db.init_app(app)
    mail = Mail(app)
    
    # Initialize Celery
    from celery_worker import make_celery
    celery = make_celery(app)
    
    app.extensions['celery'] = celery
    app.extensions['mail'] = mail
    
    # Test Redis connection
    try:
        from cache_manager import redis_client
        redis_client.ping()
        print("Redis connection successful")
    except Exception as e:
        print(f"Redis connection failed: {e}")
    
    # Setup Celery tasks within app context
    with app.app_context():
        from celery_tasks import setup_periodic_tasks, register_tasks
        setup_periodic_tasks(celery)
        app.celery_tasks = register_tasks(celery)
    
    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_lot_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(job_bp)
    
    # API Status endpoint
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'message': 'Vehicle Parking App - Complete System',
            'version': '2.1',
            'status': 'operational',
            'features': {
                'authentication': 'enabled',
                'role_based_access': 'enabled',
                'parking_management': 'enabled',
                'analytics': 'enabled',
                'redis_caching': 'enabled',
                'background_jobs': 'enabled',
                'multi_channel_notifications': 'enabled'
            },
            'available_endpoints': {
                'authentication': ['/auth/register', '/auth/login', '/auth/verify'],
                'dashboards': ['/admin/dashboard', '/user/dashboard'],
                'admin_management': ['/admin/lots', '/admin/spots', '/admin/users', '/admin/dashboard/summary'],
                'user_parking': ['/user/lots', '/user/reserve', '/user/history', '/user/current-reservation'],
                'analytics': ['/analytics/admin/parking-stats', '/analytics/admin/revenue-summary', '/analytics/user/parking-stats'],
                'background_jobs': ['/jobs/trigger-csv-export', '/jobs/status/<job_id>', '/jobs/test-daily-reminder', '/jobs/test-monthly-report'],
                'exports': ['/export/csv/download/<job_id>'],
                'testing': ['/jobs/test/gchat', '/jobs/test/email'],
                'cache_management': ['/admin/cache/clear', '/analytics/cache/clear']
            },
            'notification_channels': ['email', 'google_chat'],
            'scheduled_jobs': ['daily_reminders', 'monthly_reports']
        })
    
    @app.route('/health')
    def health_check():
        redis_status = 'connected'
        try:
            from cache_manager import redis_client
            redis_client.ping()
        except:
            redis_status = 'disconnected'
        
        celery_status = 'connected'
        try:
            celery.control.ping(timeout=1)
        except:
            celery_status = 'disconnected'
        
        mail_configured = bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'))
        gchat_configured = bool(app.config.get('GCHAT_WEBHOOK_URL'))
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'system_status': {
                'database': 'connected',
                'redis_cache': redis_status,
                'celery_worker': celery_status,
                'authentication': 'enabled',
                'admin_management': 'enabled',
                'user_parking': 'enabled',
                'analytics': 'enabled'
            },
            'notification_status': {
                'email_configured': mail_configured,
                'gchat_configured': gchat_configured
            },
            'background_jobs': 'enabled'
        })
    
    # Frontend serving routes
    @app.route('/')
    def serve_index():
        """Serve the main login page"""
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def serve_frontend(path):
        # Define API prefixes to avoid conflicts
        api_prefixes = ['auth', 'admin', 'user', 'analytics', 'jobs', 'export', 'test', 'health', 'api']
        
        if any(path.startswith(prefix + '/') or path == prefix for prefix in api_prefixes):
            return None  # will trigger Flask's normal routing
        
        # For frontend files
        frontend_file_path = os.path.join(app.static_folder, path)

        # To check if the requested file exists in the static folder
        if os.path.exists(frontend_file_path) and os.path.isfile(frontend_file_path):
            return send_from_directory(app.static_folder, path)

        # For Single Page Application routing
        # serving index.html for unknown routes
        return send_from_directory(app.static_folder, 'index.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        # For API requests, return JSON error
        if request.path.startswith('/auth/') or request.path.startswith('/admin/') or \
           request.path.startswith('/user/') or request.path.startswith('/analytics/') or \
           request.path.startswith('/jobs/') or request.path.startswith('/export/') or \
           request.path.startswith('/test/'):
            return jsonify({'error': 'API endpoint not found'}), 404
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return jsonify({'error': 'Method not allowed'}), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    return app

def setup_database(app):
    with app.app_context():
        db.create_all()
        admin_user = User.query.filter_by(username='admin').first()
        
        if not admin_user:
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role=UserRole.admin,
                email='admin@vehicleparkingapp.com',
                full_name='System Administrator',
                mobile_number='9999999999',
                vehicle_type='Admin',
                vehicle_number='ADMIN001',
                vehicle_brand='System Vehicle',
                home_address='System Address'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Predefined admin user created successfully")
            print("   Username: admin")
            print("   Password: admin123")
        else:
            print("Admin user already exists")

def start_celery_components():
    # to sttart Celery worker and beat as background processes
    try:
        # to start Celery worker
        worker_process = subprocess.Popen([
            sys.executable, '-m', 'celery', 
            '-A', 'celery_app:celery', 'worker', 
            '--loglevel=info', '--pool=solo'
        ], cwd=os.getcwd())
        # to start Celery beat
        beat_process = subprocess.Popen([
            sys.executable, '-m', 'celery', 
            '-A', 'celery_app:celery', 'beat', 
            '--loglevel=info'
        ], cwd=os.getcwd())
        print("Celery Worker and Beat started in background")
        return worker_process, beat_process
        
    except Exception as e:
        print(f"Could not start Celery components: {e}")
        return None, None

if __name__ == '__main__':
    app = create_app()
    setup_database(app)
    worker_proc, beat_proc = start_celery_components() # to start Celery components automatically

    print("\n" + "="*60)
    print("VEHICLE PARKING APP - COMPLETE SYSTEM")
    print("="*60)
    print("Authentication & Role-based Access System Ready")
    print("Admin Dashboard & Lot Management System Ready")  
    print("User Dashboard & Reservation System Ready")
    print("Analytics & Charts System Ready")
    print("Redis Caching System Ready")
    print("Celery Background Jobs System Ready")
    print("Multi-Channel Notifications Ready (Email + Google Chat)")
    print("CSV Export System Ready")
    print("Scheduled Daily & Monthly Reports Ready")
    print("="*60)
    print("Notification Channels: Email, Google Chat")
    print("Scheduled Jobs: Daily Reminders (8 AM), Monthly Reports (1st @ 9 AM)")
    print("Background Jobs: CSV Export, Email Reports, GChat Notifications")
    print("="*60)
    print("FRONTEND + BACKEND UNIFIED SERVER")
    print("Access your complete app at: http://127.0.0.1:5000")
    print("API Documentation at: http://127.0.0.1:5000/api/status")
    print("Health Check at: http://127.0.0.1:5000/health")
    print("="*60 + "\n")
    print("Access entire application at: http://127.0.0.1:5000")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nShutting down...")
        if worker_proc:
            worker_proc.terminate()
        if beat_proc:
            beat_proc.terminate()


