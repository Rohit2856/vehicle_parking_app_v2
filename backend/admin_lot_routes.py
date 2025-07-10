from flask import Blueprint, request, jsonify
from auth_utils import token_required, admin_required
from models import db, ParkingLot, ParkingSpot, ParkingSpotStatus, User, UserRole, Reservation
from datetime import datetime

admin_lot_bp = Blueprint('admin_lot', __name__, url_prefix='/admin')

class ParkingLotManager:
    @staticmethod
    def validate_lot_data(data):
        """Validate parking lot creation/update data"""
        errors = []
        
        if not data.get('prime_location_name', '').strip():
            errors.append("Location name is required")
        
        if not data.get('price') or data.get('price') <= 0:
            errors.append("Valid price is required")
        
        if not data.get('number_of_spots') or data.get('number_of_spots') <= 0:
            errors.append("Number of spots must be greater than 0")
        
        if data.get('number_of_spots', 0) > 1000:
            errors.append("Number of spots cannot exceed 1000")
        
        return errors
    
    @staticmethod
    def create_parking_spots(lot_id, num_spots):
        """Automatically create parking spots for a lot"""
        spots_created = []
        for i in range(num_spots):
            spot = ParkingSpot(
                lot_id=lot_id,
                status=ParkingSpotStatus.available
            )
            db.session.add(spot)
            spots_created.append(spot)
        
        db.session.commit()
        return spots_created

@admin_lot_bp.route('/lots', methods=['POST'])
@token_required
@admin_required
def create_parking_lot(current_user):
    # Create a new parking lot with automatic spot generation
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        # Validate input data
        validation_errors = ParkingLotManager.validate_lot_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Create parking lot
        new_lot = ParkingLot(
            prime_location_name=data['prime_location_name'].strip(),
            price=float(data['price']),
            address=data.get('address', '').strip() or None,
            pin_code=data.get('pin_code', '').strip() or None,
            number_of_spots=int(data['number_of_spots'])
        )
        
        db.session.add(new_lot)
        db.session.flush()  # Get the lot ID before creating spots
        
        # Automatically create parking spots
        spots_created = ParkingLotManager.create_parking_spots(
            new_lot.id, 
            new_lot.number_of_spots
        )
        
        return jsonify({
            'message': 'Parking lot created successfully',
            'lot': {
                'id': new_lot.id,
                'prime_location_name': new_lot.prime_location_name,
                'price': new_lot.price,
                'address': new_lot.address,
                'pin_code': new_lot.pin_code,
                'number_of_spots': new_lot.number_of_spots,
                'spots_created': len(spots_created)
            }
        }), 201
        
    except ValueError as e:
        return jsonify({'error': 'Invalid numeric values provided'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create parking lot'}), 500

@admin_lot_bp.route('/lots', methods=['GET'])
@token_required
@admin_required
def get_all_parking_lots(current_user):
    # Get all parking lots with summary information
    try:
        lots = ParkingLot.query.all()
        lots_data = []
        
        for lot in lots:
            # Calculate spot statistics
            total_spots = len(lot.spots)
            occupied_spots = len([s for s in lot.spots if s.status == ParkingSpotStatus.occupied])
            available_spots = total_spots - occupied_spots
            occupancy_rate = (occupied_spots / total_spots * 100) if total_spots > 0 else 0
            
            lots_data.append({
                'id': lot.id,
                'prime_location_name': lot.prime_location_name,
                'price': lot.price,
                'address': lot.address,
                'pin_code': lot.pin_code,
                'number_of_spots': lot.number_of_spots,
                'spot_summary': {
                    'total_spots': total_spots,
                    'occupied_spots': occupied_spots,
                    'available_spots': available_spots,
                    'occupancy_rate': round(occupancy_rate, 2)
                }
            })
        
        return jsonify({
            'lots': lots_data,
            'total_lots': len(lots_data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch parking lots'}), 500

@admin_lot_bp.route('/lots/<int:lot_id>', methods=['GET'])
@token_required
@admin_required
def get_parking_lot_details(current_user, lot_id):
    # Get detailed information about a specific parking lot
    try:
        lot = ParkingLot.query.get(lot_id)
        
        if not lot:
            return jsonify({'error': 'Parking lot not found'}), 404
        
        # Get spot details with current reservations
        spots_data = []
        for spot in lot.spots:
            active_reservation = None
            for reservation in spot.reservations:
                if reservation.leaving_timestamp is None:
                    active_reservation = {
                        'id': reservation.id,
                        'user_id': reservation.user_id,
                        'username': reservation.user.username,
                        'parking_timestamp': reservation.parking_timestamp.isoformat(),
                        'parking_cost': reservation.parking_cost
                    }
                    break
            
            spots_data.append({
                'id': spot.id,
                'status': spot.status.value,
                'active_reservation': active_reservation
            })
        
        lot_details = {
            'id': lot.id,
            'prime_location_name': lot.prime_location_name,
            'price': lot.price,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'number_of_spots': lot.number_of_spots,
            'spots': spots_data,
            'summary': {
                'total_spots': len(spots_data),
                'occupied_spots': len([s for s in spots_data if s['status'] == 'O']),
                'available_spots': len([s for s in spots_data if s['status'] == 'A'])
            }
        }
        
        return jsonify({'lot_details': lot_details}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch lot details'}), 500

@admin_lot_bp.route('/lots/<int:lot_id>', methods=['PUT'])
@token_required
@admin_required
def update_parking_lot(current_user, lot_id):
    # Update parking lot information and handle spot changes
    try:
        lot = ParkingLot.query.get(lot_id)
        
        if not lot:
            return jsonify({'error': 'Parking lot not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        # Validate input data
        validation_errors = ParkingLotManager.validate_lot_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Update lot information
        lot.prime_location_name = data['prime_location_name'].strip()
        lot.price = float(data['price'])
        lot.address = data.get('address', '').strip() or None
        lot.pin_code = data.get('pin_code', '').strip() or None
        
        # Handle spot number changes
        new_spot_count = int(data['number_of_spots'])
        current_spot_count = len(lot.spots)
        
        if new_spot_count > current_spot_count:
            # Add more spots
            additional_spots = new_spot_count - current_spot_count
            ParkingLotManager.create_parking_spots(lot.id, additional_spots)
        elif new_spot_count < current_spot_count:
            # Remove excess spots (only if they're available)
            spots_to_remove = current_spot_count - new_spot_count
            available_spots = [s for s in lot.spots if s.status == ParkingSpotStatus.available]
            
            if len(available_spots) < spots_to_remove:
                return jsonify({
                    'error': f'Cannot reduce spots. Only {len(available_spots)} spots are available for removal'
                }), 400
            
            # Remove available spots
            for i in range(spots_to_remove):
                db.session.delete(available_spots[i])
        
        lot.number_of_spots = new_spot_count
        db.session.commit()
        
        return jsonify({
            'message': 'Parking lot updated successfully',
            'lot': {
                'id': lot.id,
                'prime_location_name': lot.prime_location_name,
                'price': lot.price,
                'address': lot.address,
                'pin_code': lot.pin_code,
                'number_of_spots': lot.number_of_spots
            }
        }), 200
        
    except ValueError as e:
        return jsonify({'error': 'Invalid numeric values provided'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update parking lot'}), 500

@admin_lot_bp.route('/lots/<int:lot_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_parking_lot(current_user, lot_id):
    # Delete parking lot (only if all spots are empty)
    try:
        lot = ParkingLot.query.get(lot_id)
        
        if not lot:
            return jsonify({'error': 'Parking lot not found'}), 404
        
        # Check if any spots are occupied
        occupied_spots = [s for s in lot.spots if s.status == ParkingSpotStatus.occupied]
        if occupied_spots:
            return jsonify({
                'error': f'Cannot delete lot. {len(occupied_spots)} spots are currently occupied'
            }), 400
        
        # Delete the lot (cascade will handle spots)
        db.session.delete(lot)
        db.session.commit()
        
        return jsonify({'message': 'Parking lot deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete parking lot'}), 500

@admin_lot_bp.route('/spots', methods=['GET'])
@token_required
@admin_required
def get_all_parking_spots(current_user):
    # Get all parking spots with detailed information
    try:
        spots = ParkingSpot.query.join(ParkingLot).all()
        spots_data = []
        
        for spot in spots:
            # Get active reservation if any
            active_reservation = None
            for reservation in spot.reservations:
                if reservation.leaving_timestamp is None:
                    active_reservation = {
                        'id': reservation.id,
                        'user_id': reservation.user_id,
                        'username': reservation.user.username,
                        'parking_timestamp': reservation.parking_timestamp.isoformat(),
                        'duration_hours': (datetime.utcnow() - reservation.parking_timestamp).total_seconds() / 3600
                    }
                    break
            
            spots_data.append({
                'id': spot.id,
                'lot_id': spot.lot_id,
                'lot_name': spot.lot.prime_location_name,
                'lot_price': spot.lot.price,
                'status': spot.status.value,
                'status_display': 'Occupied' if spot.status == ParkingSpotStatus.occupied else 'Available',
                'active_reservation': active_reservation
            })
        
        return jsonify({
            'spots': spots_data,
            'total_spots': len(spots_data),
            'occupied_spots': len([s for s in spots_data if s['status'] == 'O']),
            'available_spots': len([s for s in spots_data if s['status'] == 'A'])
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch parking spots'}), 500

@admin_lot_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def get_all_users_with_parking_info(current_user):
    # Get all users with their parking usage details
    try:
        users = User.query.filter_by(role=UserRole.user).all()
        users_data = []
        
        for user in users:
            # Get user's parking statistics
            total_reservations = len(user.reservations)
            active_reservations = [r for r in user.reservations if r.leaving_timestamp is None]
            completed_reservations = [r for r in user.reservations if r.leaving_timestamp is not None]
            
            # Calculate total spending
            total_spent = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
            
            # Get current parking spot info
            current_spots = []
            for reservation in active_reservations:
                current_spots.append({
                    'spot_id': reservation.spot_id,
                    'lot_name': reservation.spot.lot.prime_location_name,
                    'parking_since': reservation.parking_timestamp.isoformat(),
                    'duration_hours': round((datetime.utcnow() - reservation.parking_timestamp).total_seconds() / 3600, 2)
                })
            
            users_data.append({
                'id': user.id,
                'username': user.username,
                'parking_stats': {
                    'total_reservations': total_reservations,
                    'active_reservations': len(active_reservations),
                    'completed_reservations': len(completed_reservations),
                    'total_amount_spent': round(total_spent, 2) if total_spent else 0.0
                },
                'current_parking': current_spots,
                'is_currently_parked': len(active_reservations) > 0
            })
        
        return jsonify({
            'users': users_data,
            'total_users': len(users_data),
            'users_currently_parked': len([u for u in users_data if u['is_currently_parked']])
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch users information'}), 500

@admin_lot_bp.route('/dashboard/summary', methods=['GET'])
@token_required
@admin_required
def get_admin_dashboard_summary(current_user):
    # Get comprehensive dashboard summary for admin
    try:
        # System statistics
        total_users = User.query.filter_by(role=UserRole.user).count()
        total_lots = ParkingLot.query.count()
        total_spots = ParkingSpot.query.count()
        occupied_spots = ParkingSpot.query.filter_by(status=ParkingSpotStatus.occupied).count()
        available_spots = total_spots - occupied_spots
        
        # Revenue statistics
        completed_reservations = Reservation.query.filter(Reservation.leaving_timestamp.isnot(None)).all()
        total_revenue = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
        
        # Active reservations
        active_reservations = Reservation.query.filter(Reservation.leaving_timestamp.is_(None)).count()
        
        # Recent activity
        recent_reservations = Reservation.query.order_by(Reservation.id.desc()).limit(10).all()
        recent_activity = []
        for reservation in recent_reservations:
            recent_activity.append({
                'id': reservation.id,
                'username': reservation.user.username,
                'lot_name': reservation.spot.lot.prime_location_name,
                'spot_id': reservation.spot_id,
                'parking_timestamp': reservation.parking_timestamp.isoformat(),
                'status': 'Active' if not reservation.leaving_timestamp else 'Completed',
                'cost': reservation.parking_cost
            })
        
        dashboard_summary = {
            'system_overview': {
                'total_registered_users': total_users,
                'total_parking_lots': total_lots,
                'total_parking_spots': total_spots,
                'occupied_spots': occupied_spots,
                'available_spots': available_spots,
                'occupancy_rate': round((occupied_spots / total_spots * 100), 2) if total_spots > 0 else 0,
                'active_reservations': active_reservations
            },
            'revenue_overview': {
                'total_revenue': round(total_revenue, 2) if total_revenue else 0.0,
                'completed_reservations': len(completed_reservations),
                'average_revenue_per_reservation': round(total_revenue / len(completed_reservations), 2) if completed_reservations else 0.0
            },
            'recent_activity': recent_activity
        }
        
        return jsonify(dashboard_summary), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch dashboard summary'}), 500
