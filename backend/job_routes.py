from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import io

job_bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@job_bp.route('/trigger-csv-export', methods=['POST'])
def trigger_csv_export():
    try:
        from flask import current_app
        
        data = request.get_json()
        user_id = data.get('user_id')
        export_type = data.get('export_type', 'user')
        date_range = data.get('date_range')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        # celery instance from current_app
        celery = current_app.extensions['celery']
        
        # Getting register task by name
        task = celery.send_task('celery_tasks.generate_csv_export', 
                               args=[user_id, export_type, date_range])
        
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
    # Check job status
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

@job_bp.route('/test-daily-reminder', methods=['POST'])
def test_daily_reminder():
    try:
        from celery_tasks import send_daily_reminders
        send_daily_reminders.delay()
        return jsonify({
            'message': 'Daily reminders job started',
            'status': 'processing'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_bp.route('/test-monthly-report', methods=['POST'])
def test_monthly_report():
    try:
        from celery_tasks import send_monthly_reports
        send_monthly_reports.delay()
        return jsonify({
            'message': 'Monthly reports job started',
            'status': 'processing'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_bp.route('/export/csv/download/<job_id>', methods=['GET'])
def download_csv_export(job_id):
    # Download completed CSV export
    try:
        from flask import current_app
        
        user_id = request.args.get('user_id')
        export_type = request.args.get('export_type', 'user')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        # Get CSV from Redis
        celery = current_app.extensions['celery']
        redis_key = f"csv_export_{export_type}_{user_id}_{job_id}"
        csv_content = celery.backend.client.get(redis_key)
        
        if not csv_content:
            return jsonify({
                'error': 'CSV not ready or expired',
                'message': 'Please check job status first'
            }), 404
        
        # Return CSV file
        csv_buffer = io.BytesIO(csv_content.encode('utf-8'))
        filename = f"parking_export_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            csv_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_bp.route('/test/gchat', methods=['POST'])
def test_gchat():
    try:
        from notifications import NotificationService
        
        data = request.get_json()
        message = data.get('message', 'Test notification from Vehicle Parking App')
        title = data.get('title', 'Test Notification')
        
        success = NotificationService.send_gchat_webhook_notification(message, title)
        
        if success:
            return jsonify({
                'message': 'Google Chat notification sent successfully',
                'status': 'success'
            }), 200
        else:
            return jsonify({
                'error': 'Google Chat notification failed',
                'status': 'failed'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_bp.route('/test/email', methods=['POST'])
def test_email():
    try:
        from flask import current_app
        from flask_mail import Message
        
        data = request.get_json()
        email = data.get('email')
        subject = data.get('subject', 'Test Email from Vehicle Parking App')
        message = data.get('message', 'This is a test email from your Vehicle Parking App!')
        
        if not email:
            return jsonify({'error': 'email is required'}), 400
        
        msg = Message(
            subject=subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email]
        )
        msg.body = message
        msg.html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: #007bff; color: white; padding: 20px; text-align: center;">
                <h2>{subject}</h2>
            </div>
            <div style="padding: 20px;">
                <p>{message}</p>
                <p><strong>This is a test email from your Vehicle Parking App system.</strong></p>
            </div>
        </body>
        </html>
        """
        
        current_app.extensions['mail'].send(msg)
        
        return jsonify({
            'message': 'Test email sent successfully',
            'email': email,
            'status': 'success'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Email sending failed: {str(e)}',
            'status': 'failed'
        }), 500
