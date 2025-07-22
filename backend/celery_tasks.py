from celery.schedules import crontab
from datetime import datetime
from models import db, User, UserRole, Reservation, ParkingLot
from notifications import NotificationService
from email_templates import EmailTemplates
import pytz

celery_app = None

def setup_periodic_tasks(celery):
    global celery_app
    celery_app = celery
    
    @celery.on_after_configure.connect
    def configure_periodic_tasks(sender, **kwargs):
        # Daily reminder at 8:00 IST
        sender.add_periodic_task(
            crontab(hour=8, minute=0, timezone='Asia/Kolkata'),
            send_daily_reminders.s(),
            name='Send daily parking reminders to all users'
        )
        
        # Monthly report on 1st of each month at 9:00 IST
        sender.add_periodic_task(
            crontab(hour=9, minute=0, day_of_month=1, timezone='Asia/Kolkata'),
            send_monthly_reports.s(),
            name='Send monthly activity reports to all users'
        )

def register_tasks(celery):
    global celery_app
    celery_app = celery
    
    # Register periodic tasks 
    return {
        'send_daily_reminders': send_daily_reminders,
        'send_monthly_reports': send_monthly_reports,
        'send_multi_channel_notification': send_multi_channel_notification,
    }

@celery_app.task(bind=True) if celery_app else lambda f: f  
def send_daily_reminders(self=None):
    # Send daily reminders via email and Google Chat 
    try:
        users = User.query.filter_by(role=UserRole.user).all()
        
        if not users:
            return "No users found"
        
        for user in users:
            ist_tz = pytz.timezone('Asia/Kolkata')
            month_start = datetime.now(ist_tz).replace(day=1, hour=0, minute=0, second=0)
            
            active_reservations = Reservation.query.filter_by(user_id=user.id).filter(
                Reservation.leaving_timestamp.is_(None)
            ).count()
            
            monthly_spending = db.session.query(db.func.sum(Reservation.parking_cost)).filter(
                Reservation.user_id == user.id,
                Reservation.leaving_timestamp >= month_start,
                Reservation.parking_cost.isnot(None)
            ).scalar() or 0
            
            available_lots = ParkingLot.query.count()
            
            reminder_data = {
                'active_reservations': active_reservations,
                'monthly_spending': float(monthly_spending),
                'available_lots': available_lots
            }
            
            user_data = {
                'name': user.full_name or user.username,
                'email': user.email or f"{user.username}@example.com",
                'reminder_data': reminder_data,
                'enable_gchat': True
            }
            send_multi_channel_notification.delay(user_data, "daily_reminder")
        print(f"Daily reminders sent to {len(users)} users")
        return f"Reminders sent to {len(users)} users"
        
    except Exception as e:
        print(f"Error in daily reminders: {e}")
        return f"Error: {e}"

@celery_app.task(bind=True) if celery_app else lambda f: f
def send_monthly_reports(self=None):
    # Send monthly reports to all users
    try:
        users = User.query.filter_by(role=UserRole.user).all()
        
        if not users:
            return "No users found"
        
        for user in users:
            ist_tz = pytz.timezone('Asia/Kolkata')
            month_start = datetime.now(ist_tz).replace(day=1, hour=0, minute=0, second=0)
            
            user_reservations = Reservation.query.filter(
                Reservation.user_id == user.id,
                Reservation.parking_timestamp >= month_start
            ).all()
            
            total_reservations = len(user_reservations)
            total_spent = sum([r.parking_cost for r in user_reservations if r.parking_cost]) or 0
            
            # Calculate average duration
            completed_reservations = [r for r in user_reservations if r.leaving_timestamp]
            avg_duration = 0
            if completed_reservations:
                total_duration = sum([
                    (r.leaving_timestamp - r.parking_timestamp).total_seconds() / 3600 
                    for r in completed_reservations
                ])
                avg_duration = round(total_duration / len(completed_reservations), 2)
            
            # Recent reservations for email
            recent_reservations = []
            for r in user_reservations[-10:]:
                duration = 0
                if r.leaving_timestamp and r.parking_timestamp:
                    duration = round((r.leaving_timestamp - r.parking_timestamp).total_seconds() / 3600, 2)
                
                recent_reservations.append({
                    'date': r.parking_timestamp.strftime('%Y-%m-%d') if r.parking_timestamp else 'N/A',
                    'lot_name': r.spot.lot.prime_location_name,
                    'duration': duration,
                    'cost': r.parking_cost or 0
                })
            
            report_data = {
                'period': f"{month_start.strftime('%B %Y')}",
                'total_reservations': total_reservations,
                'total_spent': float(total_spent),
                'avg_duration': avg_duration,
                'favorite_lot': 'N/A',
                'recent_reservations': recent_reservations
            }
            
            user_data = {
                'name': user.full_name or user.username,
                'email': user.email or f"{user.username}@example.com",
                'report_data': report_data
            }
            send_multi_channel_notification.delay(user_data, "monthly_report")
            
        print(f"Monthly reports sent to {len(users)} users")
        return f"Monthly reports sent to {len(users)} users"
        
    except Exception as e:
        print(f"Error in monthly reports: {e}")
        return f"Error: {e}"

@celery_app.task(bind=True) if celery_app else lambda f: f
def send_multi_channel_notification(self=None, user_data=None, notification_type="daily_reminder"):
    # Send notifications across multiple channels
    try:
        if not user_data:
            return "No user data provided"
            
        results = []
        
        # Email notification
        if user_data.get('email'):
            if notification_type == "daily_reminder":
                from flask_mail import Message
                from flask import current_app
                
                msg = Message(
                    subject="Daily Parking Reminder - Vehicle Parking App",
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[user_data['email']]
                )
                
                reminder_data = user_data.get('reminder_data', {})
                msg.body = f"""
Hello {user_data['name']},

Daily Parking Summary:
- Active Reservations: {reminder_data.get('active_reservations', 0)}
- Total Spent This Month: ₹{reminder_data.get('monthly_spending', 0.0)}
- Available Parking Lots: {reminder_data.get('available_lots', 0)}

Don't forget to check your parking status!

Best regards,
Vehicle Parking App Team
                """
                
                msg.html = EmailTemplates.get_daily_reminder_template(user_data['name'], reminder_data)
                current_app.extensions['mail'].send(msg)
                results.append("Email sent")
                
            elif notification_type == "monthly_report":
                from flask_mail import Message
                from flask import current_app
                
                report_data = user_data.get('report_data', {})
                html_content = EmailTemplates.get_monthly_report_template(user_data['name'], report_data)
                
                msg = Message(
                    subject=f"Monthly Parking Report - {report_data.get('period', 'Current Month')}",
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[user_data['email']]
                )
                
                msg.html = html_content
                current_app.extensions['mail'].send(msg)
                results.append("Monthly report email sent")
        
        # Google Chat notification
        if user_data.get('enable_gchat', True):
            if notification_type == "daily_reminder":
                reminder_data = user_data.get('reminder_data', {})
                message = f"Daily Parking Summary for {user_data['name']}: Active: {reminder_data.get('active_reservations', 0)}, Spent: ₹{reminder_data.get('monthly_spending', 0.0)}, Available: {reminder_data.get('available_lots', 0)}"
                
                success = NotificationService.send_gchat_webhook_notification(message, title="Daily Parking Reminder")
                if success:
                    results.append("Google Chat sent")
        
        return f"Multi-channel notifications: {', '.join(results)}"
        
    except Exception as e:
        print(f"Error in multi-channel notification: {e}")
        return f"Error: {e}"
