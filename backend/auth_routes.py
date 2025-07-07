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
def register_user():
    # Register new user (admin registration blocked)
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate input
        is_valid_username, username_error = AuthValidator.validate_username(username)
        if not is_valid_username:
            return jsonify({'error': username_error}), 400
        
        is_valid_password, password_error = AuthValidator.validate_password(password)
        if not is_valid_password:
            return jsonify({'error': password_error}), 400
        
        # Block admin registration
        if username.lower() == 'admin':
            return jsonify({'error': 'Admin registration not permitted'}), 403
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'error': 'Username already taken'}), 409
        
        # Create new user
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=UserRole.user
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'User registration successful',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'role': new_user.role.value
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed due to server error'}), 500

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
