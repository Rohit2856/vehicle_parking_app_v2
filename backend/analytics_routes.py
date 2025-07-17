from flask import Blueprint, jsonify
from auth_utils import token_required, admin_required, user_required
from models import db, ParkingLot, ParkingSpot, Reservation, User, UserRole, ParkingSpotStatus
from datetime import datetime, timedelta
from sqlalchemy import func, and_

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/admin/parking-stats', methods=['GET'])
@token_required
@admin_required
def get_admin_parking_stats(current_user):
    # Get parking statistics for admin dashboard charts
    try:
        # Daily parking statistics for the last 7 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        daily_stats = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            next_date = date + timedelta(days=1)
            
            reservations_count = Reservation.query.filter(
                and_(
                    Reservation.parking_timestamp >= date,
                    Reservation.parking_timestamp < next_date
                )
            ).count()
            
            daily_stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'reservations': reservations_count
            })
        
        # Lot occupancy statistics
        lot_stats = []
        lots = ParkingLot.query.all()
        for lot in lots:
            total_spots = len(lot.spots)
            occupied_spots = len([s for s in lot.spots if s.status == ParkingSpotStatus.occupied])
            occupancy_rate = (occupied_spots / total_spots * 100) if total_spots > 0 else 0
            
            lot_stats.append({
                'lot_name': lot.prime_location_name,
                'total_spots': total_spots,
                'occupied_spots': occupied_spots,
                'occupancy_rate': round(occupancy_rate, 2)
            })
        
        # Monthly revenue statistics
        monthly_revenue = []
        for i in range(6):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            
            revenue = db.session.query(func.sum(Reservation.parking_cost)).filter(
                and_(
                    Reservation.leaving_timestamp >= month_start,
                    Reservation.leaving_timestamp < month_end,
                    Reservation.parking_cost.isnot(None)
                )
            ).scalar()
            
            monthly_revenue.append({
                'month': month_start.strftime('%Y-%m'),
                'revenue': round(revenue, 2) if revenue else 0
            })
        
        # Parking duration distribution
        duration_stats = []
        completed_reservations = Reservation.query.filter(
            Reservation.leaving_timestamp.isnot(None)
        ).all()
        
        duration_ranges = [
            {'label': '0-1 hours', 'min': 0, 'max': 1, 'count': 0},
            {'label': '1-3 hours', 'min': 1, 'max': 3, 'count': 0},
            {'label': '3-6 hours', 'min': 3, 'max': 6, 'count': 0},
            {'label': '6+ hours', 'min': 6, 'max': float('inf'), 'count': 0}
        ]
        
        for reservation in completed_reservations:
            if reservation.parking_timestamp and reservation.leaving_timestamp:
                duration = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds() / 3600
                for range_item in duration_ranges:
                    if range_item['min'] <= duration < range_item['max']:
                        range_item['count'] += 1
                        break
        
        return jsonify({
            'daily_reservations': daily_stats,
            'lot_occupancy': lot_stats,
            'monthly_revenue': monthly_revenue,
            'duration_distribution': duration_ranges
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch admin parking statistics'}), 500

@analytics_bp.route('/admin/revenue-summary', methods=['GET'])
@token_required
@admin_required
def get_admin_revenue_summary(current_user):
    # Get revenue summary for admin dashboard
    try:
        # Total revenue
        total_revenue = db.session.query(func.sum(Reservation.parking_cost)).filter(
            Reservation.parking_cost.isnot(None)
        ).scalar()
        
        # Today's revenue
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        today_revenue = db.session.query(func.sum(Reservation.parking_cost)).filter(
            and_(
                Reservation.leaving_timestamp >= today_start,
                Reservation.leaving_timestamp < today_end,
                Reservation.parking_cost.isnot(None)
            )
        ).scalar()
        
        # This month's revenue
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_revenue = db.session.query(func.sum(Reservation.parking_cost)).filter(
            and_(
                Reservation.leaving_timestamp >= month_start,
                Reservation.parking_cost.isnot(None)
            )
        ).scalar()
        
        # Average revenue per reservation
        avg_revenue = db.session.query(func.avg(Reservation.parking_cost)).filter(
            Reservation.parking_cost.isnot(None)
        ).scalar()
        
        # Revenue by parking lot
        lot_revenue = []
        lots = ParkingLot.query.all()
        for lot in lots:
            revenue = db.session.query(func.sum(Reservation.parking_cost)).join(
                ParkingSpot, Reservation.spot_id == ParkingSpot.id
            ).filter(
                and_(
                    ParkingSpot.lot_id == lot.id,
                    Reservation.parking_cost.isnot(None)
                )
            ).scalar()
            
            lot_revenue.append({
                'lot_name': lot.prime_location_name,
                'revenue': round(revenue, 2) if revenue else 0
            })
        
        return jsonify({
            'total_revenue': round(total_revenue, 2) if total_revenue else 0,
            'today_revenue': round(today_revenue, 2) if today_revenue else 0,
            'month_revenue': round(month_revenue, 2) if month_revenue else 0,
            'average_revenue': round(avg_revenue, 2) if avg_revenue else 0,
            'lot_revenue': lot_revenue
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch revenue summary'}), 500

@analytics_bp.route('/user/parking-stats', methods=['GET'])
@token_required
@user_required
def get_user_parking_stats(current_user):
    # Get parking statistics for user dashboard charts
    try:
        # User's monthly parking activity
        monthly_activity = []
        for i in range(6):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            
            reservations_count = Reservation.query.filter(
                and_(
                    Reservation.user_id == current_user.id,
                    Reservation.parking_timestamp >= month_start,
                    Reservation.parking_timestamp < month_end
                )
            ).count()
            
            monthly_activity.append({
                'month': month_start.strftime('%Y-%m'),
                'reservations': reservations_count
            })
        
        # Reverse to show chronological order (oldest to newest)
        monthly_activity.reverse()
        
        # User's spending over time
        monthly_spending = []
        for i in range(6):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            
            spending = db.session.query(func.sum(Reservation.parking_cost)).filter(
                and_(
                    Reservation.user_id == current_user.id,
                    Reservation.leaving_timestamp >= month_start,
                    Reservation.leaving_timestamp < month_end,
                    Reservation.parking_cost.isnot(None)
                )
            ).scalar()
            
            monthly_spending.append({
                'month': month_start.strftime('%Y-%m'),
                'spending': round(spending, 2) if spending else 0.0
            })
        
        # Reverse to show chronological order
        monthly_spending.reverse()
        
        # User's parking duration preferences
        user_reservations = Reservation.query.filter(
            and_(
                Reservation.user_id == current_user.id,
                Reservation.leaving_timestamp.isnot(None)
            )
        ).all()
        
        duration_preferences = [
            {'label': '0-1 hours', 'min': 0, 'max': 1, 'count': 0},
            {'label': '1-3 hours', 'min': 1, 'max': 3, 'count': 0},
            {'label': '3-6 hours', 'min': 3, 'max': 6, 'count': 0},
            {'label': '6+ hours', 'min': 6, 'max': float('inf'), 'count': 0}
        ]
        
        for reservation in user_reservations:
            if reservation.parking_timestamp and reservation.leaving_timestamp:
                duration = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds() / 3600
                for range_item in duration_preferences:
                    if range_item['min'] <= duration < range_item['max']:
                        range_item['count'] += 1
                        break
        
        # User's favorite parking lots
        lot_usage = []
        lots = ParkingLot.query.all()
        for lot in lots:
            usage_count = Reservation.query.join(
                ParkingSpot, Reservation.spot_id == ParkingSpot.id
            ).filter(
                and_(
                    Reservation.user_id == current_user.id,
                    ParkingSpot.lot_id == lot.id
                )
            ).count()
            
            if usage_count > 0:
                lot_usage.append({
                    'lot_name': lot.prime_location_name,
                    'usage_count': usage_count
                })
        
        # Sort lot usage by count (descending) to show most used first
        lot_usage.sort(key=lambda x: x['usage_count'], reverse=True)
        
        # Ensure minimum data for charts (add dummy data if no real data exists)
        if not monthly_activity or all(item['reservations'] == 0 for item in monthly_activity):
            # Add at least one data point to prevent blank charts
            current_month = datetime.utcnow().strftime('%Y-%m')
            monthly_activity = [
                {'month': current_month, 'reservations': 0}
            ]
        
        if not monthly_spending or all(item['spending'] == 0 for item in monthly_spending):
            current_month = datetime.utcnow().strftime('%Y-%m')
            monthly_spending = [
                {'month': current_month, 'spending': 0.0}
            ]
        
        if not any(item['count'] > 0 for item in duration_preferences):
            # Add at least one count to prevent blank pie chart
            duration_preferences[0]['count'] = 1
        
        if not lot_usage:
            # Add dummy data if no parking lots used
            lot_usage = [
                {'lot_name': 'No parking history', 'usage_count': 0}
            ]
        
        return jsonify({
            'monthly_activity': monthly_activity,
            'monthly_spending': monthly_spending,
            'duration_preferences': duration_preferences,
            'lot_usage': lot_usage
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user parking statistics'}), 500

