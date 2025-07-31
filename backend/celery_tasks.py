from celery import Celery
from datetime import datetime, timedelta
import csv
import io
import os
import pytz
from sqlalchemy import func, and_
import uuid

ist_timezone = pytz.timezone('Asia/Kolkata')  # IST timezone setup

def get_current_ist():
    """Get current IST time as naive datetime"""
    return datetime.now(ist_timezone).replace(tzinfo=None)

celery = Celery('celery_tasks')   # Create Celery instance

celery.conf.update(     # Configure Celery
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=True,
    imports=['celery_tasks'],  # Important tthis ensures task are discovered
)

# flask app context helper 
def get_flask_app():
    # get Flask app instance with proper import handling
    try:
        try:   # Direct import
            from app import create_app
            return create_app()
        except ImportError:   # Fallback for relative import issues
            import sys
            import os
            
            # Add current directory to Python path
            current_dir = os.path.dirname(os.path.abspath(__file__)) 
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from app import create_app
            return create_app()
    except ImportError as e:
        print(f"Error importing Flask app: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path}")
        raise

@celery.task(bind=True, name='celery_tasks.generate_csv_export')
def generate_csv_export(self, user_id, export_type='user', test_email=None):

    print(f"[DEBUG] CSV Export task started - User ID: {user_id}, Type: {export_type}, Test Email: {test_email}")
    try:
        self.update_state(state='PROCESSING', meta={'status': 'Initializing...'})
        print(f"[DEBUG] Task state updated to PROCESSING")

        print(f"[DEBUG] Creating Flask app context...")
        app = get_flask_app()
        print(f"[DEBUG] Flask app created successfully")
        
        with app.app_context():
            print(f"[DEBUG] Inside Flask app context")
            
            # Import models inside the app context for proper access
            from models import db, User, Reservation, ParkingLot, ParkingSpot
            from email_templates import EmailTemplates
        
            print(f"[DEBUG] Models imported successfully")
            self.update_state(state='PROCESSING', meta={'status': 'Fetching user data...'})
            user = User.query.get(user_id)
            if not user:
                print(f"[ERROR] User {user_id} not found")
                return {'status': 'FAILED', 'error': f'User {user_id} not found'}
            print(f"[DEBUG] User found: {user.username}")
            self.update_state(state='PROCESSING', meta={'status': 'Getting reservations...'})

            reservations = Reservation.query.filter_by(user_id=user_id).order_by(
                Reservation.parking_timestamp.desc()).all()
            
            print(f"[DEBUG] Found {len(reservations)} reservations")
            self.update_state(state='PROCESSING', meta={'status': 'Generating CSV...'})
            csv_buffer = io.StringIO()
            csv_writer = csv.writer(csv_buffer, quoting=csv.QUOTE_ALL)

            headers = [
                'Reservation ID', 'Date', 'Parking Location', 'Spot ID',
                'Start Time', 'End Time', 'Duration (Hours)', 'Cost (Rs)',
                'Status', 'Lot Address', 'Generated On'
            ]
            csv_writer.writerow(headers)
            current_timestamp = get_current_ist().strftime('%d-%m-%Y %H:%M:%S IST')

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
                        parking_date = reservation.parking_timestamp.strftime('%d/%m/%y')
                        start_time = reservation.parking_timestamp.strftime('%H:%M:%S')
                    if reservation.leaving_timestamp:
                        end_time = reservation.leaving_timestamp.strftime('%H:%M:%S')
                        status = 'Completed'
                        if reservation.parking_timestamp:
                            duration_seconds = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds()
                            duration_hours = round(duration_seconds / 3600, 2)
                            duration = str(duration_hours)
                            total_hours += duration_hours
                    cost = reservation.parking_cost or 0
                    if cost > 0:
                        total_spent += cost
                   
                    row = [
                        reservation.id,
                        parking_date,
                        reservation.spot.lot.prime_location_name if reservation.spot and reservation.spot.lot else 'Unknown',
                        reservation.spot_id,
                        start_time,
                        end_time,
                        duration,
                        cost,
                        status,
                        reservation.spot.lot.address if reservation.spot and reservation.spot.lot else 'Address not available',
                        current_timestamp
                    ]
                    csv_writer.writerow(row)  # Write reservation data to CSV
                except Exception as e:
                    print(f"[ERROR] Error processing reservation {reservation.id}: {e}")
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
            
            self.update_state(state='PROCESSING', meta={'status': 'Saving CSV file...'})

            # save CSV file with username 
            os.makedirs('exports', exist_ok=True)  
            export_id = str(uuid.uuid4())
            timestamp = get_current_ist().strftime('%Y%m%d_%H%M%S')
            filename = f"parking_export_{export_type}_{user.username}_{timestamp}.csv"
            file_path = os.path.join('exports', filename)

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                f.write(csv_buffer.getvalue())
            
            print(f"[DEBUG] CSV saved to: {file_path}")
            
            self.update_state(state='PROCESSING', meta={'status': 'Sending email with attachment...'})
            
            # send email with csv attachment
            email_subject = f"Your Parking Data Export is Ready - {len(reservations)} Records"
            
            # use the export template from email_templates
            export_data = {
                'records_count': len(reservations),
                'export_type': export_type,
                'filename': filename
            }
            
            email_body = EmailTemplates.get_export_ready_template(user.username, export_data)

            recipient_email = test_email if test_email else user.email
            print(f"[DEBUG] Sending CSV to: {recipient_email}")

            email_result = EmailTemplates.send_email(
                to_email=recipient_email,
                subject=email_subject,
                body=email_body,
                html=False,
                attachment_path=file_path  # this attaches the CSV file
            )
            print(f"[DEBUG] Email sent with attachment: {email_result}")

            final_result = {
                'status': 'SUCCESS',
                'file_path': file_path,
                'filename': filename,
                'records_count': len(reservations),
                'export_id': export_id,
                'total_spent': total_spent,
                'total_hours': total_hours,
                'email_sent': email_result.get('status') == 'SUCCESS',
                'sent_to_email': recipient_email  
            }
            
            print(f"[DEBUG] Task completed successfully: {final_result}")
            return final_result
            
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Task failed: {error_msg}")
        import traceback
        traceback.print_exc()

        self.update_state(
            state='FAILURE',
            meta={
                'error': error_msg,
                'exc_type': type(e).__name__,
                'exc_message': error_msg
            }
        )
        
        return {'status': 'FAILED', 'error': error_msg}

@celery.task(bind=True, name='celery_tasks.send_daily_reminders')
def send_daily_reminders(self):
    # send daily reminders to inactive users
    print("[DEBUG] Daily reminders task started")
    
    try:
        self.update_state(state='PROCESSING', meta={'status': 'Initializing reminders...'})
        app = get_flask_app()
        with app.app_context():
            from models import User, db
            from email_templates import EmailTemplates
            users = User.query.limit(3).all()
            print(f"[DEBUG] Found {len(users)} users to send reminders")
            
            self.update_state(state='PROCESSING', meta={'status': f'Sending reminders to {len(users)} users...'})
            sent_count = 0
            failed_count = 0
            
            for i, user in enumerate(users, 1):
                try:
                    print(f"[DEBUG] Sending reminder {i}/{len(users)} to {user.email}")
                    reminder_data = {
                        'last_activity': user.last_activity.strftime('%Y-%m-%d') if hasattr(user, 'last_activity') and user.last_activity else 'Never',
                        'username': user.username
                    }

                    email_body = EmailTemplates.get_daily_reminder_template(user.username, reminder_data)
                    result = EmailTemplates.send_email(
                        to_email=user.email,
                        subject="Don't Forget to Book Your Parking Spot!",
                        body=email_body
                    )
                    if result.get('status') == 'SUCCESS':
                        sent_count += 1
                        print(f"[DEBUG] Reminder sent successfully to {user.email}")
                    else:
                        failed_count += 1
                        print(f"[ERROR] Failed to send reminder to {user.email}: {result}")
                except Exception as e:
                    failed_count += 1
                    print(f"[ERROR] Error sending reminder to user {user.id}: {e}")
                    continue

                progress = (i / len(users)) * 100
                self.update_state(state='PROCESSING', meta={'status': f'Progress: {progress:.0f}% ({i}/{len(users)})'})
                try:
                    db.session.remove()   # Clean up session after each user
                except:
                    pass
            try:
                db.session.remove()  # Clean up session
                db.session.close()
            except:
                pass
            print(f"[DEBUG] Daily reminders completed. Sent: {sent_count}, Failed: {failed_count}")
            return {
                'status': 'SUCCESS', 
                'reminders_sent': sent_count,
                'failed_count': failed_count,
                'total_users': len(users)
            }
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Daily reminders failed: {error_msg}")
        import traceback
        traceback.print_exc()
        try:
            from models import db
            db.session.rollback()
            db.session.close()
        except:
            pass
        self.update_state(
            state='FAILURE',
            meta={
                'error': error_msg,
                'exc_type': type(e).__name__,
                'exc_message': error_msg
            }
        )
        return {'status': 'FAILED', 'error': error_msg}

__all__ = ['generate_csv_export', 'send_daily_reminders']   # Export tasks for Celery

