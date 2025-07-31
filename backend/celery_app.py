from app import create_app
from celery_worker import make_celery

flask_app = create_app()   # Create Flask app instance

celery = make_celery(flask_app)    # Create Celery instance

if __name__ == '__main__':
    celery.start()