from flask import Blueprint, request, jsonify
from auth_utils import token_required, admin_required
from models import db, ParkingLot, ParkingSpot, ParkingSpotStatus, User, UserRole, Reservation
from cache_manager import cache_response, invalidate_cache
import pytz
from datetime import datetime
ist_timezone = pytz.timezone('Asia/Kolkata')

admin_lot_bp = Blueprint('admin_lot', __name__, url_prefix='/admin')

class ParkingLotManager:
    @staticmethod
    def validate_lot_data(data):
        # validate parking lot data
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
        spots_created = []     # creates parking spots for lot
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
@invalidate_cache(['lots_*', 'spots_*', 'analytics_*'])
def create_parking_lot(current_user):
    try:  
        data = request.get_json()    
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        validation_errors = ParkingLotManager.validate_lot_data(data)  # Validate input data
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400  

        new_lot = ParkingLot(   # Create new parking lot instance
            prime_location_name=data['prime_location_name'].strip(),
            price=float(data['price']),
            address=data.get('address', '').strip() or None,
            pin_code=data.get('pin_code', '').strip() or None,
            number_of_spots=int(data['number_of_spots'])
        )
        
        db.session.add(new_lot)
        db.session.flush()  # Flush to get the new lot ID
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
        return jsonify({'error': 'Invalid value provided'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create parking lot'}), 500

@admin_lot_bp.route('/lots', methods=['GET'])
@token_required
@admin_required
@cache_response('lots_admin_all', ttl=600)
def get_all_parking_lots(current_user):
    #all parking lots with info 
    try:
        query = request.args.get('q', '').strip()
        pincode = request.args.get('pincode', '').strip()
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        lots_query = ParkingLot.query
        if query:
            lots_query = lots_query.filter(
                db.or_(
                    ParkingLot.prime_location_name.ilike(f'%{query}%'),
                    ParkingLot.address.ilike(f'%{query}%')
                )
            )
        if pincode:
            lots_query = lots_query.filter(ParkingLot.pin_code.ilike(f'%{pincode}%'))
        if min_price:
            lots_query = lots_query.filter(ParkingLot.price >= float(min_price))
        if max_price:
            lots_query = lots_query.filter(ParkingLot.price <= float(max_price))
        lots = lots_query.all()        

        lots_data = []
        for lot in lots:
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
            'total_lots': len(lots_data),
            'cache_info': {
                'cached_at': datetime.now(ist_timezone).isoformat(),
                'ttl': 600  #
            }
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch parking lots'}), 500

@admin_lot_bp.route('/lots/<int:lot_id>', methods=['GET'])
@token_required
@admin_required
@cache_response('lots_admin_detail', ttl=300)
def get_parking_lot_details(current_user, lot_id):
    # Get detailed information about a specific parking lot (cached)
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
            },
            'cache_info': {
                'cached_at': datetime.now(ist_timezone).isoformat(),
                'ttl': 300
            }
        }
        
        return jsonify({'lot_details': lot_details}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch lot details'}), 500

@admin_lot_bp.route('/lots/<int:lot_id>', methods=['PUT'])
@token_required
@admin_required
@invalidate_cache(['lots_*', 'spots_*', 'analytics_*'])
def update_parking_lot(current_user, lot_id):
    # update parking lot information & spot 
    try:
        lot = ParkingLot.query.get(lot_id)
        
        if not lot:
            return jsonify({'error': 'Parking lot not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        validation_errors = ParkingLotManager.validate_lot_data(data)
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400

        lot.prime_location_name = data['prime_location_name'].strip()
        lot.price = float(data['price'])
        lot.address = data.get('address', '').strip() or None
        lot.pin_code = data.get('pin_code', '').strip() or None

        new_spot_count = int(data['number_of_spots'])
        current_spot_count = len(lot.spots)
        
        if new_spot_count > current_spot_count:
            additional_spots = new_spot_count - current_spot_count
            ParkingLotManager.create_parking_spots(lot.id, additional_spots)
        elif new_spot_count < current_spot_count:
            spots_to_remove = current_spot_count - new_spot_count
            available_spots = [s for s in lot.spots if s.status == ParkingSpotStatus.available]
            
            if len(available_spots) < spots_to_remove:
                return jsonify({
                    'error': f'Cannot reduce spots. Only {len(available_spots)} spots are available for removal'
                }), 400
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
@invalidate_cache(['lots_*', 'spots_*', 'analytics_*'])
def delete_parking_lot(current_user, lot_id):
    # Delete lot if all spots empty
    try:
        lot = ParkingLot.query.get(lot_id)
        if not lot:
            return jsonify({'error': 'Parking lot not found'}), 404
        
        # check if any spot is occupied
        occupied_spots = [s for s in lot.spots if s.status == ParkingSpotStatus.occupied]
        if occupied_spots:
            return jsonify({
                'error': f'Cannot delete lot. {len(occupied_spots)} spots are currently occupied'
            }), 400
        db.session.delete(lot)
        db.session.commit()
        
        return jsonify({'message': 'Parking lot deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete parking lot'}), 500

@admin_lot_bp.route('/spots', methods=['GET'])
@token_required
@admin_required
@cache_response('spots_admin_all', ttl=60)
def get_all_parking_spots(current_user):
    # all parking spots info 
    try:
        # Get search parameters
        query = request.args.get('q', '').strip()
        status = request.args.get('status', '').strip()
        lot_id = request.args.get('lot_id')
        
        spots_query = ParkingSpot.query.join(ParkingLot)
        
        # Apply filters if provided
        if query:
            spots_query = spots_query.filter(
                db.or_(
                    ParkingSpot.id == int(query) if query.isdigit() else False,
                    ParkingLot.prime_location_name.ilike(f'%{query}%')
                )
            )
        if status and status in ['A', 'O']:
            status_enum = ParkingSpotStatus.available if status == 'A' else ParkingSpotStatus.occupied
            spots_query = spots_query.filter(ParkingSpot.status == status_enum)
        if lot_id:
            spots_query = spots_query.filter(ParkingSpot.lot_id == int(lot_id))
        
        spots = spots_query.all()
        spots_data = []

        for spot in spots:
            active_reservation = None
            vehicle_number = None
            can_delete = False
            for reservation in spot.reservations:
                if reservation.leaving_timestamp is None:
                    user = reservation.user
                    active_reservation = {
                        'id': reservation.id,
                        'user_id': reservation.user_id,
                        'username': user.username,
                        'parking_timestamp': reservation.parking_timestamp.isoformat(),
                        'duration_hours': (datetime.now(ist_timezone) - reservation.parking_timestamp).total_seconds() / 3600
                    }
                    vehicle_number = user.vehicle_number if user.vehicle_number else 'Not provided'
                    break

            if spot.status == ParkingSpotStatus.available and active_reservation is None:
                can_delete = True
            spots_data.append({
                'id': spot.id,
                'lot_id': spot.lot_id,
                'lot_name': spot.lot.prime_location_name,
                'lot_price': spot.lot.price,
                'status': spot.status.value,
                'status_display': 'Occupied' if spot.status == ParkingSpotStatus.occupied else 'Available',
                'active_reservation': active_reservation,
                'vehicle_number': vehicle_number if vehicle_number else '-',
                'can_delete': can_delete
            })
        return jsonify({
            'spots': spots_data,
            'total_spots': len(spots_data),
            'occupied_spots': len([s for s in spots_data if s['status'] == 'O']),
            'available_spots': len([s for s in spots_data if s['status'] == 'A']),
            'cache_info': {
                'cached_at': datetime.now(ist_timezone).isoformat(),
                'ttl': 60
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch parking spots'}), 500

@admin_lot_bp.route('/spots/<int:spot_id>/remove', methods=['DELETE'])
@token_required
@admin_required
@invalidate_cache(['spots_*', 'lots_*', 'analytics_*'])
def remove_individual_spot(current_user, spot_id):
    # Remove a specific parking spot if it's available
    try:
        target_spot = ParkingSpot.query.get(spot_id)
        if not target_spot:
            return jsonify({'error': 'Parking spot not found'}), 404
        if target_spot.status == ParkingSpotStatus.occupied:
            return jsonify({'error': 'Cannot delete occupied spot'}), 400
        pending_reservations = [r for r in target_spot.reservations if r.leaving_timestamp is None]
        if pending_reservations:
            return jsonify({'error': 'Spot has active reservations'}), 400
        parent_lot = target_spot.lot
        db.session.delete(target_spot)
        parent_lot.number_of_spots = parent_lot.number_of_spots - 1  #update spot count
        db.session.commit()
        return jsonify({
            'message': 'Parking spot removed successfully',
            'updated_lot_count': parent_lot.number_of_spots
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to remove parking spot'}), 500

@admin_lot_bp.route('/users', methods=['GET'])
@token_required
@admin_required
@cache_response('users_admin_all', ttl=300)
def get_all_users_with_parking_info(current_user):
    #users with their usage details 
    try:
        # Get search parameters
        query = request.args.get('q', '').strip()
        email = request.args.get('email', '').strip()
        vehicle_type = request.args.get('vehicle_type', '').strip()
        
        users_query = User.query.filter_by(role=UserRole.user)
        
        # Apply filters if provided
        if query:
            users_query = users_query.filter(
                db.or_(
                    User.username.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%'),
                    User.full_name.ilike(f'%{query}%'),
                    User.vehicle_number.ilike(f'%{query}%')
                )
            )
        if email:
            users_query = users_query.filter(User.email.ilike(f'%{email}%'))
        if vehicle_type:
            users_query = users_query.filter(User.vehicle_type.ilike(f'%{vehicle_type}%'))
        
        users = users_query.all()
        users_data = []
        for user in users:
            total_reservations = len(user.reservations)
            active_reservations = [r for r in user.reservations if r.leaving_timestamp is None]
            completed_reservations = [r for r in user.reservations if r.leaving_timestamp is not None]
            total_spent = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
            current_spots = []
            for reservation in active_reservations:
                current_spots.append({
                    'spot_id': reservation.spot_id,
                    'lot_name': reservation.spot.lot.prime_location_name,
                    'parking_since': reservation.parking_timestamp.isoformat(),
                    'duration_hours': round((datetime.now(ist_timezone) - reservation.parking_timestamp).total_seconds() / 3600, 2)
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
            'users_currently_parked': len([u for u in users_data if u['is_currently_parked']]),
            'cache_info': {
                'cached_at': datetime.now(ist_timezone).isoformat(),
                'ttl': 300
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch users information'}), 500

@admin_lot_bp.route('/dashboard/summary', methods=['GET'])
@token_required
@admin_required
@cache_response('dashboard_admin_summary', ttl=120)
def get_admin_dashboard_summary(current_user):
    # comprehensive dashboard summary for admin 
    try:
        total_users = User.query.filter_by(role=UserRole.user).count()
        total_lots = ParkingLot.query.count()
        total_spots = ParkingSpot.query.count()
        occupied_spots = ParkingSpot.query.filter_by(status=ParkingSpotStatus.occupied).count()
        available_spots = total_spots - occupied_spots
        completed_reservations = Reservation.query.filter(Reservation.leaving_timestamp.isnot(None)).all()
        total_revenue = sum([r.parking_cost for r in completed_reservations if r.parking_cost])
        active_reservations = Reservation.query.filter(Reservation.leaving_timestamp.is_(None)).count()

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
            'recent_activity': recent_activity,
            'cache_info': {
                'cached_at': datetime.now(ist_timezone).isoformat(),
                'ttl': 120
            }
        }
        return jsonify(dashboard_summary), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch dashboard summary'}), 500

@admin_lot_bp.route('/cache/clear', methods=['POST'])
@token_required
@admin_required
def clear_cache(current_user):
    try:
        from cache_manager import cache_manager
        cache_manager.flush_cache()
        return jsonify({'message': 'Cache cleared successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to clear cache'}), 500
    