from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import io
import os

job_bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@job_bp.route('/trigger-csv-export', methods=['POST'])
def trigger_csv_export():
    try:
        from flask import current_app
        data = request.get_json()
        user_id = data.get('user_id')
        export_type = data.get('export_type', 'user')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        celery = current_app.extensions['celery']
        task = celery.send_task('celery_tasks.generate_csv_export',
                               args=[user_id, export_type])
        
        return jsonify({
            'job_id': task.id,
            'status': 'processing',
            'message': f'CSV export started for {export_type} data',
            'check_status_url': f'/jobs/status/{task.id}'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_bp.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    try:
        from flask import current_app
        celery = current_app.extensions['celery']
        task = celery.AsyncResult(job_id)
        
        if task.state == 'PENDING':
            response = {
                'job_id': job_id,
                'state': task.state,
                'status': 'Job is waiting to be processed',
                'current': 0,
                'total': 100
            }
        elif task.state == 'SUCCESS':
            response = {
                'job_id': job_id,
                'state': task.state,
                'result': task.result,
                'status': 'Job completed successfully'
            }
        elif task.state == 'FAILURE':
            response = {
                'job_id': job_id,
                'state': task.state,
                'status': 'Job failed',
                'error': str(task.info)
            }
        else:
            response = {
                'job_id': job_id,
                'state': task.state,
                'status': str(task.info)
            }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_bp.route('/export/csv/download/<job_id>', methods=['GET'])
def download_csv_export(job_id):
    try:
        user_id = request.args.get('user_id')
        export_type = request.args.get('export_type', 'user')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        exports_dir = 'exports'
        if not os.path.exists(exports_dir):
            return jsonify({'error': 'No exports directory found'}), 404
        
        filename = None
        for file in os.listdir(exports_dir):
            if job_id in file and export_type in file and file.endswith('.csv'):
                filename = file
                break
        if not filename:
            return jsonify({'error': 'Export file not found'}), 404
        file_path = os.path.join(exports_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Export file not found'}), 404
        download_name = f"parking_export_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='text/csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_bp.route('/instant-csv-export', methods=['POST'])
def instant_csv_export():
    try:
        from models import User, Reservation
        from datetime import datetime
        import csv
        import io
        import os
        
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        reservations = Reservation.query.filter_by(
            user_id=user_id
        ).order_by(Reservation.parking_timestamp.desc()).all()
        
        if not reservations:
            return jsonify({'error': 'No parking history found'}), 404

        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer, quoting=csv.QUOTE_ALL)  # quote all fields for Excel compatibility

        headers = [
            'Reservation ID', 'Date', 'Parking Location', 'Spot ID', 
            'Start Time', 'End Time', 'Duration (Hours)', 'Cost (Rs)', 
            'Status', 'Lot Address', 'Generated On'
        ]
        csv_writer.writerow(headers)

        current_timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S IST') # for generated on field
        
        # Process reservations
        total_spent = 0
        total_hours = 0
        
        for reservation in reservations:
            try:
                parking_date = 'No Date'
                start_time = 'No Time'
                end_time = 'Still Active'
                duration = 'Active'
                status = 'Active'

                if reservation.parking_timestamp:
                    try:
                        parking_date = reservation.parking_timestamp.strftime('%d/%m/%y')
                        start_time = reservation.parking_timestamp.strftime('%H:%M:%S')
                    except (AttributeError, TypeError) as e:
                        print(f"Parking timestamp error for reservation {reservation.id}: {e}")
                        parking_date = 'Date Error'
                        start_time = 'Time Error'

                if reservation.leaving_timestamp:
                    try:
                        end_time = reservation.leaving_timestamp.strftime('%H:%M:%S')
                        status = 'Completed'

                        if reservation.parking_timestamp:
                            duration_seconds = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds()
                            duration_hours = round(duration_seconds / 3600, 2)
                            duration = str(duration_hours)
                            total_hours += duration_hours
                    except (AttributeError, TypeError) as e:
                        print(f"Leaving timestamp error for reservation {reservation.id}: {e}")
                        end_time = 'Time Error'
                        duration = 'Error'

                cost = reservation.parking_cost or 0
                if cost > 0:
                    total_spent += cost

                row = [
                    reservation.id,                                             
                    parking_date,                                               
                    reservation.spot.lot.prime_location_name or 'Unknown',      
                    reservation.spot_id,                                        
                    start_time,                                                 
                    end_time,                                                   
                    duration,                                                   
                    cost,                                                       
                    status,                                                     
                    reservation.spot.lot.address or 'Address not available',   
                    current_timestamp                                           
                ]
                csv_writer.writerow(row)
                
            except Exception as e:
                print(f"Error processing reservation {reservation.id}: {e}")
                error_row = [
                    reservation.id,
                    'Processing Error',
                    'Data Error',
                    reservation.spot_id if hasattr(reservation, 'spot') else 'N/A',
                    'Error',
                    'Error',
                    'Error',
                    reservation.parking_cost or 0,
                    'Error',
                    'Error',
                    current_timestamp
                ]
                csv_writer.writerow(error_row)
                continue
        
        csv_writer.writerow([]) 
        csv_writer.writerow(['SUMMARY REPORT', '', '', '', '', '', '', '', '', '', ''])
        csv_writer.writerow(['Total Reservations', len(reservations), '', '', '', '', '', '', '', '', ''])
        csv_writer.writerow(['Total Amount Spent', f'Rs. {total_spent:.2f}', '', '', '', '', '', '', '', '', ''])
        csv_writer.writerow(['Total Parking Hours', f'{total_hours:.2f}', '', '', '', '', '', '', '', '', ''])
        if total_hours > 0:
            avg_cost = total_spent / total_hours
            csv_writer.writerow(['Average Cost per Hour', f'Rs. {avg_cost:.2f}', '', '', '', '', '', '', '', '', ''])
        else:
            csv_writer.writerow(['Average Cost per Hour', 'Rs. 0.00', '', '', '', '', '', '', '', '', ''])
        
        csv_writer.writerow(['NOTE: If dates show as ####, double-click column border to auto-fit', '', '', '', '', '', '', '', '', '', ''])

        os.makedirs('exports', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_filename = f"parking_history_{user.username}_{timestamp}.csv"
        temp_path = os.path.join('exports', temp_filename)
        
        with open(temp_path, 'w', newline='', encoding='utf-8-sig') as f:
            f.write(csv_buffer.getvalue())
        
        download_filename = f"my_parking_history_{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        print(f"Export function error: {e}")
        return jsonify({'error': 'CSV export failed', 'details': str(e)}), 500


@job_bp.route('/test-daily-reminder', methods=['POST'])
def test_daily_reminder():
    try:
        from celery_tasks import send_daily_reminders
        task = send_daily_reminders.delay()
        return jsonify({
            'job_id': task.id,
            'message': 'Daily reminders job started',
            'status': 'processing',
            'check_status_url': f'/jobs/status/{task.id}'
        }), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_bp.route('/test-monthly-report', methods=['POST'])
def test_monthly_report():
    try:
        from celery_tasks import send_monthly_reports
        task = send_monthly_reports.delay()
        return jsonify({
            'job_id': task.id,
            'message': 'Monthly reports job started',
            'status': 'processing',
            'check_status_url': f'/jobs/status/{task.id}'
        }), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500