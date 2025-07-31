from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from auth_utils import token_required, admin_required
from extensions import db
from models import User, UserRole, Reservation
from datetime import datetime, timedelta
import pytz
import re

ist_timezone = pytz.timezone('Asia/Kolkata')
profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

class ProfileValidator:
    @staticmethod
    def validate_email(email):
        if not email or not email.strip():
            return False, "Email is required"
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email.strip()):
            return False, "Invalid email format"
        return True, ""

    @staticmethod
    def validate_phone(phone):
        if phone and phone.strip():
            phone_clean = re.sub(r'\D', '', phone.strip())
            if len(phone_clean) != 10 or not phone_clean.startswith(('6', '7', '8', '9')):
                return False, "Phone must be 10 digits starting with 6-9"
        return True, ""

    @staticmethod
    def validate_full_name(name):
        if not name or len(name.strip()) < 2:
            return False, "Full name must be at least 2 characters"
        if len(name.strip()) > 100:
            return False, "Full name cannot exceed 100 characters"
        return True, ""

def get_inactive_days(user):
    if not hasattr(user, 'last_activity') or not user.last_activity:
        return 999
    now = datetime.now(ist_timezone).replace(tzinfo=None)
    delta = now - user.last_activity
    return delta.days

def is_user_currently_parked(user_id):
    active_reservation = Reservation.query.filter_by(
        user_id=user_id
    ).filter(Reservation.leaving_timestamp.is_(None)).first()
    return active_reservation is not None

def update_user_activity(user_id):
    try:
        user = User.query.get(user_id)
        if user and user.role == UserRole.user:
            user.last_activity = datetime.now(ist_timezone).replace(tzinfo=None)
            db.session.commit()
            print(f"Updated last_activity for user {user.username}")
    except Exception as e:
        print(f"Failed to update user activity: {e}")
        db.session.rollback()

@profile_bp.route('/me', methods=['GET'])
@token_required
def get_my_profile(current_user):
    try:
        profile_data = {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'full_name': current_user.full_name,
            'role': current_user.role.value,
            'mobile_number': current_user.mobile_number,
            'vehicle_type': current_user.vehicle_type,
            'vehicle_number': current_user.vehicle_number,
            'vehicle_brand': current_user.vehicle_brand,
            'home_address': current_user.home_address
        }

        # Calculate statistics based on role
        if current_user.role == UserRole.user:
            total_reservations = len(current_user.reservations)
            completed_reservations = [r for r in current_user.reservations if r.leaving_timestamp]
            total_spent = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
            
            profile_stats = {
                'total_reservations': total_reservations,
                'total_spent': round(total_spent, 2) if total_spent else 0.0,
                'member_since': 'Recently joined'
            }
        else:
            # Admin statistics
            total_users = User.query.filter_by(role=UserRole.user).count()
            total_reservations = Reservation.query.count()
            completed_reservations = Reservation.query.filter(
                Reservation.leaving_timestamp.isnot(None)
            ).all()
            total_revenue = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
            
            profile_stats = {
                'total_users': total_users,
                'total_reservations': total_reservations,
                'total_revenue': round(total_revenue, 2) if total_revenue else 0.0,
                'system_admin_since': 'System Administrator'
            }

        return jsonify({
            'profile': profile_data,
            'stats': profile_stats
        }), 200

    except Exception as e:
        return jsonify({'error': 'Failed to fetch profile'}), 500

@profile_bp.route('/me', methods=['PUT'])
@token_required
def update_my_profile(current_user):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required'}), 400

        errors = {}
        if 'email' in data:
            is_valid, error_msg = ProfileValidator.validate_email(data['email'])
            if not is_valid:
                errors['email'] = error_msg
            else:
                existing_user = User.query.filter(
                    User.email == data['email'].strip(),
                    User.id != current_user.id
                ).first()
                if existing_user:
                    errors['email'] = 'Email already in use by another user'

        if 'full_name' in data:
            is_valid, error_msg = ProfileValidator.validate_full_name(data['full_name'])
            if not is_valid:
                errors['full_name'] = error_msg

        if 'mobile_number' in data:
            is_valid, error_msg = ProfileValidator.validate_phone(data['mobile_number'])
            if not is_valid:
                errors['mobile_number'] = error_msg
            else:
                mobile_clean = re.sub(r'\D', '', data['mobile_number'].strip()) if data['mobile_number'] else ''
                if mobile_clean:
                    existing_user = User.query.filter(
                        User.mobile_number == mobile_clean,
                        User.id != current_user.id
                    ).first()
                    if existing_user:
                        errors['mobile_number'] = 'Mobile number already in use'

        if errors:
            return jsonify({'errors': errors}), 400

        if 'email' in data:
            current_user.email = data['email'].strip() 
        
        if 'full_name' in data:
            current_user.full_name = data['full_name'].strip()
        
        if 'mobile_number' in data:
            mobile_clean = re.sub(r'\D', '', data['mobile_number'].strip()) if data['mobile_number'].strip() else None
            current_user.mobile_number = mobile_clean
        
        if 'vehicle_type' in data:
            current_user.vehicle_type = data['vehicle_type'].strip() or None
            
        if 'vehicle_number' in data:
            current_user.vehicle_number = data['vehicle_number'].strip() or None
        
        if 'vehicle_brand' in data:
            current_user.vehicle_brand = data['vehicle_brand'].strip() or None
        
        if 'home_address' in data:
            current_user.home_address = data['home_address'].strip() or None

        if current_user.role == UserRole.user:
            current_user.last_activity = datetime.now(ist_timezone).replace(tzinfo=None)

        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'updated_fields': list(data.keys())
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500


@profile_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def get_users_for_management(current_user):
    try:
        search_query = request.args.get('q', '').strip()
        users_query = User.query.filter_by(role=UserRole.user)

        if search_query:
            users_query = users_query.filter(
                db.or_(
                    User.username.ilike(f'%{search_query}%'),
                    User.email.ilike(f'%{search_query}%'),
                    User.full_name.ilike(f'%{search_query}%')
                )
            )
        users = users_query.all()
        enhanced_users = []

        for user in users:
            now = datetime.now(ist_timezone).replace(tzinfo=None)
            recent_reservations = Reservation.query.filter_by(user_id=user.id).order_by(
                Reservation.leaving_timestamp.desc().nullsfirst(),
                Reservation.parking_timestamp.desc()
            ).limit(1).all()

            if recent_reservations:
                latest_reservation = recent_reservations[0]
                if latest_reservation.leaving_timestamp is None:
                    inactive_days = 0
                else:
                    latest_activity = latest_reservation.leaving_timestamp
                    if hasattr(user, 'last_activity') and user.last_activity:
                        latest_activity = max(latest_activity, user.last_activity)
                    inactive_days = (now - latest_activity).days
            else:
                if hasattr(user, 'last_activity') and user.last_activity:
                    inactive_days = (now - user.last_activity).days
                else:
                    inactive_days = 999

            is_currently_parked = is_user_currently_parked(user.id)
            current_parking = []
            if is_user_currently_parked(user.id):
                active_reservation = Reservation.query.filter_by(
                    user_id=user.id
                ).filter(Reservation.leaving_timestamp.is_(None)).first()
                
                if active_reservation:
                    now = datetime.now(ist_timezone).replace(tzinfo=None)
                    duration_hours = (now - active_reservation.parking_timestamp).total_seconds() / 3600
                    lot_price = active_reservation.spot.lot.price
                    current_cost = duration_hours * lot_price
                    
                    current_parking.append({
                        'spot_id': active_reservation.spot_id,
                        'lot_name': active_reservation.spot.lot.prime_location_name,
                        'lot_price': lot_price,
                        'duration_hours': round(duration_hours, 2),
                        'current_cost': round(current_cost, 2)
                    })

            completed_reservations = [r for r in user.reservations if r.leaving_timestamp]
            total_spent = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
            enhanced_users.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'mobile_number': user.mobile_number,
                'vehicle_type': user.vehicle_type,
                'vehicle_number': user.vehicle_number,
                'parking_stats': {
                    'total_reservations': len(user.reservations),
                    'total_amount_spent': round(total_spent, 2) if total_spent else 0.0
                },
                'is_currently_parked': is_currently_parked,
                'current_parking': current_parking,
                'last_activity_days': inactive_days,
                'can_delete': not is_currently_parked and inactive_days >= 30
            })
        return jsonify({
            'users': enhanced_users,
            'total_users': len(enhanced_users)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user management data'}), 500

@profile_bp.route('/users/<int:user_id>/details', methods=['GET'])
@token_required
@admin_required
def get_user_detailed_info(current_user, user_id):
    try:
        target_user = User.query.get(user_id)
        if not target_user or target_user.role != UserRole.user:
            return jsonify({'error': 'User not found'}), 404

        recent_reservations = Reservation.query.filter_by(
            user_id=user_id
        ).order_by(Reservation.parking_timestamp.desc()).limit(10).all()

        reservations_data = []
        for r in recent_reservations:
            duration_hours = None
            if r.leaving_timestamp and r.parking_timestamp:
                duration_seconds = (r.leaving_timestamp - r.parking_timestamp).total_seconds()
                duration_hours = round(duration_seconds / 3600, 2)
            reservations_data.append({
                'id': r.id,
                'lot_name': r.spot.lot.prime_location_name,
                'spot_id': r.spot_id,
                'start_time': r.parking_timestamp.isoformat() if r.parking_timestamp else None,
                'end_time': r.leaving_timestamp.isoformat() if r.leaving_timestamp else None,
                'duration_hours': duration_hours,
                'cost': r.parking_cost,
                'status': 'Active' if not r.leaving_timestamp else 'Completed'
            })

        completed_reservations = [r for r in target_user.reservations if r.leaving_timestamp]
        total_spent = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
        user_details = {
            'id': target_user.id,
            'username': target_user.username,
            'email': target_user.email,
            'full_name': target_user.full_name,
            'mobile_number': target_user.mobile_number,
            'vehicle_type': target_user.vehicle_type,
            'vehicle_number': target_user.vehicle_number,
            'vehicle_brand': target_user.vehicle_brand,
            'home_address': target_user.home_address,
            'stats': {
                'total_reservations': len(target_user.reservations),
                'total_spent': round(total_spent, 2) if total_spent else 0.0
            },
            'last_activity_days': get_inactive_days(target_user),
            'currently_parked': is_user_currently_parked(user_id),
            'recent_reservations': reservations_data
        }
        return jsonify({'user': user_details}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user details'}), 500

@profile_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user_account(current_user, user_id):
    try:
        target_user = User.query.get(user_id)
        if not target_user or target_user.role != UserRole.user:
            return jsonify({'error': 'User not found'}), 404

        if is_user_currently_parked(user_id):
            return jsonify({
                'error': 'Cannot delete user with active parking session'
            }), 400

        inactive_days = get_inactive_days(target_user)
        if inactive_days < 30:
            return jsonify({
                'error': 'Cannot delete recently active user',
                'reason': f'User was active {inactive_days} days ago. Must be inactive for 30+ days.'
            }), 400

        deleted_user_info = {
            'id': target_user.id,
            'username': target_user.username,
            'email': target_user.email
        }
        db.session.delete(target_user)
        db.session.commit()
        return jsonify({
            'message': 'User account deleted successfully',
            'deleted_user': deleted_user_info
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete user account'}), 500

    