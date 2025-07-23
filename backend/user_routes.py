from flask import Blueprint, request, jsonify
from auth_utils import token_required, user_required
from models import db, ParkingLot, ParkingSpot, ParkingSpotStatus, Reservation
from datetime import datetime
import pytz
from pytz import timezone
ist_timezone = pytz.timezone('Asia/Kolkata')

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/lots', methods=['GET'])
@token_required
@user_required
def get_available_parking_lots(current_user):
    # Get all parking lots with available spots
    try:
        lots = ParkingLot.query.all()
        lots_data = []
        
        for lot in lots:
            total_spots = len(lot.spots)
            occupied_spots = len([s for s in lot.spots if s.status == ParkingSpotStatus.occupied])
            available_spots = total_spots - occupied_spots
            
            if available_spots > 0:
                lots_data.append({
                    'id': lot.id,
                    'prime_location_name': lot.prime_location_name,
                    'price': lot.price,
                    'address': lot.address,
                    'pin_code': lot.pin_code,
                    'number_of_spots': lot.number_of_spots,
                    'available_spots': available_spots,
                    'occupancy_rate': round((occupied_spots / total_spots * 100), 2) if total_spots > 0 else 0
                })
        
        return jsonify({
            'available_lots': lots_data,
            'total_available_lots': len(lots_data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch available parking lots'}), 500

@user_bp.route('/reserve', methods=['POST'])
@token_required
@user_required
def reserve_parking_spot(current_user):
    # Auto-allocate and reserve the first available spot in a chosen lot
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        lot_id = data.get('lot_id')
        if not lot_id:
            return jsonify({'error': 'lot_id is required'}), 400

        # Check if user already has an active reservation
        active_reservation = Reservation.query.filter_by(
            user_id=current_user.id
        ).filter(Reservation.leaving_timestamp.is_(None)).first()
        
        if active_reservation:
            return jsonify({'error': 'You already have an active reservation'}), 400

        lot = ParkingLot.query.get(lot_id)
        if not lot:
            return jsonify({'error': 'Parking lot not found'}), 404

        # Find first available spot in the lot
        available_spot = ParkingSpot.query.filter_by(
            lot_id=lot_id, 
            status=ParkingSpotStatus.available
        ).first()
        
        if not available_spot:
            return jsonify({'error': 'No available spots in this lot'}), 400

        # Create reservation
        now = datetime.now(ist_timezone)
        reservation = Reservation(
            spot_id=available_spot.id,
            user_id=current_user.id,
            parking_timestamp=now,
            leaving_timestamp=None,
            parking_cost=None
        )
        db.session.add(reservation)

        # Update spot status to occupied
        available_spot.status = ParkingSpotStatus.occupied

        db.session.commit()

        return jsonify({
            'message': 'Spot reserved successfully',
            'reservation': {
                'reservation_id': reservation.id,
                'spot_id': available_spot.id,
                'lot_id': lot_id,
                'lot_name': lot.prime_location_name,
                'parking_timestamp': reservation.parking_timestamp.isoformat(),
                'hourly_rate': lot.price
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to reserve parking spot'}), 500

@user_bp.route('/occupy/<int:reservation_id>', methods=['POST'])
@token_required
@user_required
def occupy_spot(current_user, reservation_id):
    # Mark a reserved spot as occupied (update status and timestamp)
    try:
        reservation = Reservation.query.get(reservation_id)
        
        if not reservation or reservation.user_id != current_user.id:
            return jsonify({'error': 'Reservation not found or access denied'}), 404

        if reservation.leaving_timestamp is not None:
            return jsonify({'error': 'Reservation already completed'}), 400

        spot = ParkingSpot.query.get(reservation.spot_id)
        if not spot:
            return jsonify({'error': 'Parking spot not found'}), 404

        # Update spot status to occupied (should already be occupied from reservation)
        spot.status = ParkingSpotStatus.occupied

        # Update parking timestamp to current time
        reservation.parking_timestamp = datetime.now(ist_timezone)

        db.session.commit()

        return jsonify({
            'message': 'Spot marked as occupied',
            'parking_timestamp': reservation.parking_timestamp.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to occupy spot'}), 500

@user_bp.route('/release/<int:reservation_id>', methods=['POST'])
@token_required
@user_required
def release_spot(current_user, reservation_id):
    # Release a spot (update status and leaving timestamp)
    try:
        reservation = Reservation.query.get(reservation_id)
        
        if not reservation or reservation.user_id != current_user.id:
            return jsonify({'error': 'Reservation not found or access denied'}), 404

        spot = ParkingSpot.query.get(reservation.spot_id)
        if not spot:
            return jsonify({'error': 'Parking spot not found'}), 404

        if reservation.leaving_timestamp is not None:
            return jsonify({'error': 'Spot already released'}), 400

        # Update spot status to available
        spot.status = ParkingSpotStatus.available

        # Set leaving timestamp
        reservation.leaving_timestamp = datetime.now(ist_timezone)

        # Calculate parking cost based on duration
        duration_seconds = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds()
        duration_hours = duration_seconds / 3600
        cost = duration_hours * reservation.spot.lot.price
        reservation.parking_cost = round(cost, 2)

        db.session.commit()

        return jsonify({
            'message': 'Spot released successfully',
            'parking_cost': reservation.parking_cost,
            'duration_hours': round(duration_hours, 2),
            'leaving_timestamp': reservation.leaving_timestamp.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to release spot'}), 500

@user_bp.route('/history', methods=['GET'])
@token_required
@user_required
def get_parking_history(current_user):
    # Get parking reservation history for the current user
    try:
        reservations = Reservation.query.filter_by(
            user_id=current_user.id
        ).order_by(Reservation.parking_timestamp.desc()).all()
        
        history = []
        total_spent = 0
        
        for r in reservations:
            duration_hours = None
            if r.leaving_timestamp and r.parking_timestamp:
                duration_seconds = (r.leaving_timestamp - r.parking_timestamp).total_seconds()
                duration_hours = round(duration_seconds / 3600, 2)
            
            if r.parking_cost:
                total_spent += r.parking_cost
            
            history.append({
                'reservation_id': r.id,
                'spot_id': r.spot_id,
                'lot_id': r.spot.lot_id,
                'lot_name': r.spot.lot.prime_location_name,
                'lot_address': r.spot.lot.address,
                'parking_timestamp': r.parking_timestamp.isoformat() if r.parking_timestamp else None,
                'leaving_timestamp': r.leaving_timestamp.isoformat() if r.leaving_timestamp else None,
                'duration_hours': duration_hours,
                'parking_cost': r.parking_cost,
                'status': 'Active' if not r.leaving_timestamp else 'Completed'
            })
        
        return jsonify({
            'history': history,
            'total_reservations': len(history),
            'total_amount_spent': round(total_spent, 2),
            'active_reservations': len([h for h in history if h['status'] == 'Active'])
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch parking history'}), 500

@user_bp.route('/current-reservation', methods=['GET'])
@token_required
@user_required
def get_current_reservation(current_user):
    # Get user's current active reservation
    try:
        active_reservation = Reservation.query.filter_by(
            user_id=current_user.id
        ).filter(Reservation.leaving_timestamp.is_(None)).first()
        
        if not active_reservation:
            return jsonify({'active_reservation': None}), 200
        
        # calculate current duration
        current_time = datetime.now(ist_timezone)
        duration_seconds = (current_time - active_reservation.parking_timestamp).total_seconds()
        duration_hours = round(duration_seconds / 3600, 2)
        estimated_cost = round(duration_hours * active_reservation.spot.lot.price, 2)
        
        reservation_data = {
            'reservation_id': active_reservation.id,
            'spot_id': active_reservation.spot_id,
            'lot_id': active_reservation.spot.lot_id,
            'lot_name': active_reservation.spot.lot.prime_location_name,
            'lot_address': active_reservation.spot.lot.address,
            'parking_timestamp': active_reservation.parking_timestamp.isoformat(),
            'current_duration_hours': duration_hours,
            'estimated_cost': estimated_cost,
            'hourly_rate': active_reservation.spot.lot.price
        }
        
        return jsonify({'active_reservation': reservation_data}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch current reservation'}), 500
