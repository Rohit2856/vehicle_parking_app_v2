import os
from datetime import datetime, timedelta
import pytz

# IST Timezone Configuration
TIMEZONE = 'Asia/Kolkata'
IST_TZ = pytz.timezone('Asia/Kolkata')

def get_ist_now():  # helper function for ist time
    return datetime.now(pytz.timezone('Asia/Kolkata'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vp-mad2-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///vehicle_parking_app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-for-vehicle-parking'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_ALGORITHM = 'HS256'

    # Redis Configuration
    REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    REDIS_DB = int(os.environ.get('REDIS_DB') or 0)
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')

    # Cache Configuration
    CACHE_DEFAULT_TTL = 300  # 5 minutes
    CACHE_LOTS_TTL = 600  # 10 minutes for parking lots
    CACHE_SPOTS_TTL = 60  # 1 minute for spot availability
    CACHE_ANALYTICS_TTL = 900  # 15 minutes for analytics data

    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = '23f1000362@ds.study.iitm.ac.in'
    MAIL_PASSWORD = 'pbss jvmv obmo dmik'
    MAIL_DEFAULT_SENDER = '23f1000362@ds.study.iitm.ac.in'

    # Google Chat Configuration
    GCHAT_WEBHOOK_URL = 'https://chat.googleapis.com/v1/spaces/AAQAOmFxSN8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=bB8u5rlM_ubqV4EhWTRFjTsnKUECSWAnarWuK4SX_bc'
    GCHAT_NOTIFICATIONS_ENABLED = True

    # Celery Configuration 
    broker_url = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    result_backend = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    timezone = TIMEZONE
    enable_utc = True

    # Task routing
    task_routes = {
        'celery_tasks.generate_csv_export': {'queue': 'export'},
        'celery_tasks.send_daily_reminders': {'queue': 'notifications'},
        'celery_tasks.generate_monthly_report': {'queue': 'reports'}
    }

# Scheduled task
from celery.schedules import crontab
beat_schedule = {
    'send-daily-reminders': {
        'task': 'celery_tasks.send_daily_reminders',
        'schedule': crontab(hour=18, minute=0),  # 6pm
    },
    'generate-monthly-reports': {
        'task': 'celery_tasks.send_monthly_reports',
        'schedule': crontab(hour=9, minute=0, day_of_month=1),  # 1st day 9am
    }
}

