from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, UserRole
from auth_utils import TokenManager
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

class AuthValidator:
    @staticmethod
    def validate_username(username):
        # Validate username format and rules
        if not username or len(username.strip()) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 50:
            return False, "Username cannot exceed 50 characters"
        
        if not re.match("^[a-zA-Z0-9_]+$", username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        return True, ""
    
    @staticmethod
    def validate_password(password):
        # Validate password strength
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long"
        
        if len(password) > 128:
            return False, "Password cannot exceed 128 characters"
        
        return True, ""

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'password', 'email', 'full_name', 'mobile_number', 'vehicle_type', 'vehicle_number']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
        
        # Email validation
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Mobile validation 
        mobile_pattern = r'^[6-9]\d{9}$'
        if not re.match(mobile_pattern, data['mobile_number']):
            return jsonify({'error': 'Invalid mobile number. Use 10-digit Indian mobile number'}), 400
        
        # Vehicle number validation
        vehicle_pattern = r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$'
        if not re.match(vehicle_pattern, data['vehicle_number'].upper()):
            return jsonify({'error': 'Invalid vehicle number format. Use format like DL01AB1234'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        if User.query.filter_by(mobile_number=data['mobile_number']).first():
            return jsonify({'error': 'Mobile number already registered'}), 400
        
        if User.query.filter_by(vehicle_number=data['vehicle_number'].upper()).first():
            return jsonify({'error': 'Vehicle number already registered'}), 400
        
        # Create new user
        new_user = User(
            username=data['username'],
            password_hash=generate_password_hash(data['password']),
            email=data['email'],
            full_name=data['full_name'],
            mobile_number=data['mobile_number'],
            vehicle_type=data['vehicle_type'],
            vehicle_number=data['vehicle_number'].upper(),
            vehicle_brand=data.get('vehicle_brand'),
            home_address=data.get('home_address'),
            role=UserRole.user
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'full_name': new_user.full_name,
                'vehicle_type': new_user.vehicle_type,
                'vehicle_number': new_user.vehicle_number
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    # Authenticate user and return JWT token
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Find user by username
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate access token
        access_token = TokenManager.generate_access_token(user)
        
        # Determine dashboard redirect URL
        dashboard_url = '/admin/dashboard' if user.role == UserRole.admin else '/user/dashboard'
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'token_type': 'Bearer',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role.value
            },
            'dashboard_url': dashboard_url
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Login failed due to server error'}), 500

@auth_bp.route('/verify', methods=['GET'])
def verify_token():
    # Verify token validity without requiring decorator
    try:
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'valid': False, 'error': 'No authorization header'}), 401
        
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return jsonify({'valid': False, 'error': 'Invalid token format'}), 401
        
        payload = TokenManager.decode_token(token)
        if not payload:
            return jsonify({'valid': False, 'error': 'Invalid or expired token'}), 401
        
        user = User.query.get(payload['user_id'])
        if not user:
            return jsonify({'valid': False, 'error': 'User not found'}), 401
        
        return jsonify({
            'valid': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role.value
            }
        }), 200
        
    except Exception as e:
        return jsonify({'valid': False, 'error': 'Token verification failed'}), 500
