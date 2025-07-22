from celery import Celery

def make_celery(app):
    # Set up Celery to use Flask app config and Redis as broker
    celery = Celery(
        app.import_name,
        broker=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    )
    
    # Update celery config from Flask app config
    celery.conf.update(app.config)
    
    # ISt timezone
    celery.conf.timezone = 'Asia/Kolkata'
    
    # Configure task route
    celery.conf.task_routes = {
        'celery_tasks.send_daily_reminders': {'queue': 'notifications'},
        'celery_tasks.send_monthly_reports': {'queue': 'reports'},
        'celery_tasks.generate_csv_export': {'queue': 'exports'},
    }
    
    # Configure task serialization
    celery.conf.task_serializer = 'json'
    celery.conf.accept_content = ['json']
    celery.conf.result_serializer = 'json'
    
    # Task execution with Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

