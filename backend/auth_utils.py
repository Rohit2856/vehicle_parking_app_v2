import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from models import User, UserRole

class TokenManager:
    @staticmethod
    def generate_access_token(user):
        # Generate JWT access token for authenticated user
        payload = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role.value,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        }
        return jwt.encode(
            payload, 
            current_app.config['JWT_SECRET_KEY'], 
            algorithm=current_app.config['JWT_ALGORITHM']
        )
    
    @staticmethod
    def decode_token(token):
        # Decode and validate JWT token
        try:
            payload = jwt.decode(
                token, 
                current_app.config['JWT_SECRET_KEY'], 
                algorithms=[current_app.config['JWT_ALGORITHM']]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

def token_required(f):
    # Decorator to require valid JWT token
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Authentication token required'}), 401
        
        payload = TokenManager.decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        current_user = User.query.get(payload['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated_function

def admin_required(f):
    # Decorator to require admin role
    @wraps(f)
    def decorated_function(current_user, *args, **kwargs):
        if current_user.role != UserRole.admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(current_user, *args, **kwargs)
    
    return decorated_function

def user_required(f):
    #Decorator to require user role
    @wraps(f)
    def decorated_function(current_user, *args, **kwargs):
        if current_user.role != UserRole.user:
            return jsonify({'error': 'User access only'}), 403
        return f(current_user, *args, **kwargs)
    
    return decorated_function
