from flask import Blueprint, jsonify
from auth_utils import token_required, admin_required, user_required
from models import db, User, ParkingLot, ParkingSpot, Reservation, UserRole
import pytz
from pytz import timezone
ist_timezone = pytz.timezone('Asia/Kolkata')
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/admin/dashboard', methods=['GET'])
@token_required
@admin_required
def admin_dashboard(current_user):
    # Admin dashboard with system overview
    try:
        # System statistics
        total_users = User.query.filter_by(role=UserRole.user).count()
        total_lots = ParkingLot.query.count()
        total_spots = ParkingSpot.query.count()
        occupied_spots = ParkingSpot.query.filter_by(status='O').count()
        available_spots = total_spots - occupied_spots
        
        # Recent activity
        recent_reservations = Reservation.query.order_by(
            Reservation.id.desc()
        ).limit(5).all()
        
        dashboard_data = {
            'welcome_message': f'Welcome to Admin Dashboard, {current_user.username}',
            'user_info': {
                'id': current_user.id,
                'username': current_user.username,
                'role': current_user.role.value
            },
            'system_stats': {
                'total_registered_users': total_users,
                'total_parking_lots': total_lots,
                'total_parking_spots': total_spots,
                'occupied_spots': occupied_spots,
                'available_spots': available_spots,
                'occupancy_rate': round((occupied_spots / total_spots * 100), 2) if total_spots > 0 else 0
            },
            'recent_activity': {
                'recent_reservations_count': len(recent_reservations)
            }
        }
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to load admin dashboard'}), 500

@dashboard_bp.route('/user/dashboard', methods=['GET'])
@token_required
@user_required
def user_dashboard(current_user):
    # User dashboard with personal parking information
    try:
        # User's reservation statistics
        user_reservations = Reservation.query.filter_by(user_id=current_user.id).all()
        active_reservations = [r for r in user_reservations if r.leaving_timestamp is None]
        completed_reservations = [r for r in user_reservations if r.leaving_timestamp is not None]
        
        # Available parking lots
        available_lots = ParkingLot.query.count()
        
        # Calculate total spending
        total_spent = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
        
        # Current reservation details
        current_reservation = None
        if active_reservations:
            reservation = active_reservations[0]
            from datetime import datetime
            current_time = datetime.now(ist_timezone)
            duration_seconds = (current_time - reservation.parking_timestamp).total_seconds()
            duration_hours = round(duration_seconds / 3600, 2)
            estimated_cost = round(duration_hours * reservation.spot.lot.price, 2)
            
            current_reservation = {
                'reservation_id': reservation.id,
                'spot_id': reservation.spot_id,
                'lot_name': reservation.spot.lot.prime_location_name,
                'current_duration_hours': duration_hours,
                'estimated_cost': estimated_cost
            }
        
        dashboard_data = {
            'welcome_message': f'Welcome to User Dashboard, {current_user.username}',
            'user_info': {
                'id': current_user.id,
                'username': current_user.username,
                'role': current_user.role.value
            },
            'parking_stats': {
                'total_reservations': len(user_reservations),
                'active_reservations': len(active_reservations),
                'completed_reservations': len(completed_reservations),
                'total_amount_spent': round(total_spent, 2) if total_spent else 0.0,
                'available_parking_lots': available_lots
            },
            'current_status': {
                'has_active_parking': len(active_reservations) > 0,
                'current_reservation': current_reservation
            }
        }
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to load user dashboard'}), 500

@dashboard_bp.route('/profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    # Get current user profile information
    try:
        profile_data = {
            'id': current_user.id,
            'username': current_user.username,
            'role': current_user.role.value,
            'account_type': 'Administrator' if current_user.role == UserRole.admin else 'Regular User'
        }
        
        return jsonify({'profile': profile_data}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch profile'}), 500
