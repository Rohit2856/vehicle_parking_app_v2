# celery_app.py
from app import create_app
from celery_worker import make_celery

# Create Flask app instance
flask_app = create_app()

# Create Celery instance
celery = make_celery(flask_app)

# Setup tasks
with flask_app.app_context():
    from celery_tasks import setup_periodic_tasks, register_tasks
    setup_periodic_tasks(celery)
    register_tasks(celery)

if __name__ == '__main__':
    celery.start()
