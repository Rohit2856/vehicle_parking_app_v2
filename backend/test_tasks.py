from flask import Flask
from celery_tasks import celery, generate_csv_export, send_daily_reminders
from email_templates import EmailTemplates
import time
import signal
import sys

def signal_handler(sig, frame):
    print('Test interrupted by user')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def test_email_system():
    print("Testing email system...")
    result = EmailTemplates.send_email(
        to_email="rohitrai2856@gmail.com",
        subject="Test Email - Vehicle Parking App",
        body="This is a test email to verify the email system is working correctly."
    )
    print(f"Email test result: {result}")
    return result

def test_csv_export(user_id=2):
    print(f"Testing CSV export for user {user_id}...")
    
    from app import create_app
    from models import User
    
    app = create_app()
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"User {user_id} not found")
            return {'status': 'FAILED', 'error': 'User not found'}
        else:
            print(f"User found: {user.username} - {user.email}")
 
    test_email = "23f1000362@ds.study.iitm.ac.in"  
    task = generate_csv_export.delay(user_id, 'user', test_email)  
    print(f"Task ID: {task.id}")
    print(f"CSV will be sent to: {test_email} (for testing)")
    print("Waiting for task completion..")
    
    timeout_counter = 0  # timeout for CSV export
    max_timeout = 30  # 30 seconds max

    while timeout_counter < max_timeout:
        try:
            task_state = task.state
            print(f"Task state: {task_state}")
            
            if task_state == 'SUCCESS':
                result = task.result
                print(f"Export result: {result}")
                return result
            
            elif task_state == 'FAILURE':
                print(f"Task failed")
                try:
                    error_info = task.info
                    print(f"Task error: {error_info}")
                    return {'status': 'FAILED', 'error': str(error_info)}
                except Exception as e:
                    print(f"Could not retrieve error info: {e}")
                    return {'status': 'FAILED', 'error': 'Task failed with unknown error'}

            try:
                if hasattr(task, 'info') and task.info:
                    print(f"Task info: {task.info}")
            except Exception:
                pass  
            time.sleep(2)
            timeout_counter += 1
            
        except Exception as e:
            print(f"Error checking task status: {e}")
            time.sleep(2)
            timeout_counter += 1
            continue
    print("Task timeout - stopping test")
    return {'status': 'TIMEOUT', 'task_id': task.id}

def test_daily_reminders():
    print("Testing daily reminders...")
    task = send_daily_reminders.delay()
    print(f"Task ID: {task.id}")
    print("Waiting for task completion...")
    
    timeout_counter = 0
    max_timeout = 60  
    
    while timeout_counter < max_timeout:
        try:
            task_state = task.state
            print(f"Task state: {task_state}")
            
            if task_state == 'SUCCESS':
                result = task.result
                print(f"Reminder result: {result}")
                return result
            elif task_state == 'FAILURE':
                try:
                    error_info = task.info
                    print(f"Task failed: {error_info}")
                    return {'status': 'FAILED', 'error': str(error_info)}
                except Exception:
                    return {'status': 'FAILED', 'error': 'Task failed with unknown error'}
            elif task_state == 'PROCESSING':
                try:
                    if hasattr(task, 'info') and task.info:
                        print(f"Task progress: {task.info}")
                except Exception:
                    pass
            time.sleep(3)  
            timeout_counter += 1
            
        except KeyboardInterrupt:
            print("Test interrupted by user")
            return {'status': 'INTERRUPTED', 'task_id': task.id}
        except Exception as e:
            print(f"Error checking task: {e}")
            time.sleep(3)
            timeout_counter += 1
    
    print("Daily reminders timeout - stopping test")
    return {'status': 'TIMEOUT', 'task_id': task.id}

def test_celery_connection():
    print("Testing Celery connection...")
    try:
        inspect = celery.control.inspect()
        stats = inspect.stats()
        if stats:
            print("Celery workers are active:")
            for worker, stat in stats.items():
                print(f"  Worker: {worker}")
        else:
            print("No active Celery workers found")
        return True
    except Exception as e:
        print(f"Celery connection failed: {e}")
        return False

def run_all_tests():
    print("=" * 50)
    print("VEHICLE PARKING APP - TASK SYSTEM TESTS")
    print("=" * 50)
    try:
        if not test_celery_connection():
            print("Celery connection failed. Please start Celery worker first.")
            return
        
        email_result = test_email_system()
        if email_result['status'] == 'SUCCESS':
            print("Email system working properly")
        else:
            print(f"Email system failed: {email_result}")
            return
       
        export_result = test_csv_export()
        if export_result and export_result.get('status') == 'SUCCESS':
            print("CSV export system working properly")
        else:
            print(f"CSV export failed: {export_result}")
        
        # Test daily reminders
        reminder_result = test_daily_reminders()
        if reminder_result and reminder_result.get('status') == 'SUCCESS':
            print("Daily reminder system working properly")
        else:
            print(f"Daily reminders result: {reminder_result}")
        
    except KeyboardInterrupt:
        print("Tests interrupted by user")
        return
    except Exception as e:
        print(f"Test suite error: {e}")
        return
    
    print("=" * 50)
    print("ALL TESTS COMPLETED")
    print("=" * 50)

if __name__ == "__main__":
    print("Starting task system tests...")
    print("Make sure Celery worker is running:")
    print("celery -A celery_tasks worker --loglevel=info --pool=solo")
    print()
    
    try:
        choice = input("Press Enter to continue or 'q' to quit: ")
        if choice.lower() != 'q':
            run_all_tests()
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)

