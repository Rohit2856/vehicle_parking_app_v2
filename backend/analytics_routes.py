from flask import Blueprint, jsonify
from auth_utils import token_required, admin_required, user_required
from models import db, ParkingLot, ParkingSpot, Reservation, User, UserRole, ParkingSpotStatus
from cache_manager import cache_response
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import pytz

ist_timezone = pytz.timezone('Asia/Kolkata')
analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

def get_current_ist_naive():
    # current IST time as naive datetime
    return datetime.now(ist_timezone).replace(tzinfo=None)

def calculate_duration_safe(start_time, end_time=None):
    # safely calculate duration between IST timestamps
    if end_time is None:
        end_time = get_current_ist_naive()
    return (end_time - start_time).total_seconds() / 3600

@analytics_bp.route('/admin/parking-stats', methods=['GET'])
@token_required
@admin_required
@cache_response('analytics_admin_parking_stats', ttl=600)
def get_admin_parking_stats(current_user):
    try:
        # Last 7 days activity
        daily_data = []
        for i in range(7):
            date = get_current_ist_naive() - timedelta(days=6-i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            count = Reservation.query.filter(
                and_(
                    Reservation.parking_timestamp >= start_of_day,
                    Reservation.parking_timestamp < end_of_day
                )
            ).count()
            
            daily_data.append({
                'date': date.strftime('%a'),  
                'reservations': count,
                'revenue': round(count * 50, 2)  # Estimated revenue
            })

        # Live parking lot status
        lot_data = []
        for lot in ParkingLot.query.all():
            total = len(lot.spots)
            occupied = sum(1 for s in lot.spots if s.status == ParkingSpotStatus.occupied)
            available = total - occupied
            
            lot_data.append({
                'name': lot.prime_location_name[:15],  
                'occupied': occupied,
                'available': available,
                'occupancy': round((occupied/total*100) if total > 0 else 0, 1)
            })

        # Revenue by time periods
        periods = ['Today', 'This Week', 'This Month', 'Last Month']
        revenue_data = []
        for period in periods:
            if period == 'Today':
                start = get_current_ist_naive().replace(hour=0, minute=0, second=0)
            elif period == 'This Week':
                start = get_current_ist_naive() - timedelta(days=7)
            elif period == 'This Month':
                start = get_current_ist_naive().replace(day=1, hour=0, minute=0, second=0)
            else:  # Last Month
                current = get_current_ist_naive()
                start = (current.replace(day=1) - timedelta(days=1)).replace(day=1)
            revenue = db.session.query(func.sum(Reservation.parking_cost)).filter(
                and_(
                    Reservation.leaving_timestamp >= start,
                    Reservation.parking_cost.isnot(None)
                )
            ).scalar() or 0
            revenue_data.append({
                'period': period,
                'amount': round(revenue, 2)
            })

        # user behavior patterns
        behavior_data = []
        for hour in [6, 10, 14, 18, 22]:  
            count = Reservation.query.filter(
                func.extract('hour', Reservation.parking_timestamp) == hour
            ).count()
            behavior_data.append({
                'hour': f"{hour}:00",
                'bookings': count
            })
        return jsonify({
            'daily_activity': daily_data,
            'lot_status': lot_data,
            'revenue_trends': revenue_data,
            'peak_hours': behavior_data,
            'summary': {
                'total_lots': len(lot_data),
                'total_spots': sum(l['occupied'] + l['available'] for l in lot_data),
                'active_users': User.query.filter_by(role=UserRole.user).count(),
                'today_revenue': revenue_data[0]['amount'] if revenue_data else 0
            },
            'generated_at': get_current_ist_naive().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            'daily_activity': [{'date': 'Today', 'reservations': 0, 'revenue': 0}],
            'lot_status': [{'name': 'No Data', 'occupied': 0, 'available': 1, 'occupancy': 0}],
            'revenue_trends': [{'period': 'Today', 'amount': 0}],
            'peak_hours': [{'hour': '12:00', 'bookings': 0}],
            'summary': {'total_lots': 0, 'total_spots': 0, 'active_users': 0, 'today_revenue': 0},
            'generated_at': get_current_ist_naive().isoformat(),
            'error': str(e)
        }), 200

@analytics_bp.route('/user/parking-stats', methods=['GET'])
@token_required
@user_required
@cache_response('analytics_user_parking_stats', ttl=300, user_specific=True)
def get_user_parking_stats(current_user):
    # Streamlined user analytics
    try:
        user_reservations = Reservation.query.filter_by(user_id=current_user.id).all()
        monthly_spending = []
        for i in range(6):
            month_start = get_current_ist_naive().replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=32)
            
            spent = sum(r.parking_cost or 0 for r in user_reservations 
                       if r.leaving_timestamp and month_start <= r.leaving_timestamp < month_end)
            
            monthly_spending.append({
                'month': month_start.strftime('%b'),
                'amount': round(spent, 2)
            })
        monthly_spending.reverse()

        lot_usage = {}    # Favorite parking lots
        for reservation in user_reservations:
            lot_name = reservation.spot.lot.prime_location_name
            lot_usage[lot_name] = lot_usage.get(lot_name, 0) + 1
        
        favorite_lots = [{'name': k[:12], 'visits': v} for k, v in 
                        sorted(lot_usage.items(), key=lambda x: x[1], reverse=True)[:5]]

        duration_prefs = []    # Parking duration preferences
        completed = [r for r in user_reservations if r.leaving_timestamp]
        
        for label, min_h, max_h in [('Quick (0-2h)', 0, 2), ('Medium (2-5h)', 2, 5), 
                                   ('Long (5h+)', 5, 24)]:
            count = sum(1 for r in completed 
                       if min_h <= calculate_duration_safe(r.parking_timestamp, r.leaving_timestamp) < max_h)
            duration_prefs.append({'label': label, 'count': count})
            
        weekly_pattern = []
        for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
            day_num = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].index(day)
            count = sum(1 for r in user_reservations 
                       if r.parking_timestamp.weekday() == day_num)
            weekly_pattern.append({'day': day, 'bookings': count})

        return jsonify({
            'spending_trend': monthly_spending,
            'favorite_locations': favorite_lots or [{'name': 'No data', 'visits': 0}],
            'duration_preferences': duration_prefs,
            'weekly_activity': weekly_pattern,
            'personal_stats': {
                'total_bookings': len(user_reservations),
                'total_spent': round(sum(r.parking_cost or 0 for r in user_reservations), 2),
                'avg_duration': round(sum(calculate_duration_safe(r.parking_timestamp, r.leaving_timestamp) 
                                        for r in completed) / len(completed) if completed else 0, 1),
                'favorite_lot': max(lot_usage.items(), key=lambda x: x[1])[0] if lot_usage else 'None'
            },
            'generated_at': get_current_ist_naive().isoformat()
        }), 200
    except Exception as e:
        # Fallback data
        return jsonify({
            'spending_trend': [{'month': 'Jan', 'amount': 0}],
            'favorite_locations': [{'name': 'No data', 'visits': 0}],
            'duration_preferences': [{'label': 'No data', 'count': 0}],
            'weekly_activity': [{'day': 'Mon', 'bookings': 0}],
            'personal_stats': {'total_bookings': 0, 'total_spent': 0, 'avg_duration': 0, 'favorite_lot': 'None'},
            'generated_at': get_current_ist_naive().isoformat()
        }), 200



