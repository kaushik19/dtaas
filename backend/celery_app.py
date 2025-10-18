from celery import Celery
from config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'dtaas',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['celery_tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 12,  # 12 hours max
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

if __name__ == '__main__':
    celery_app.start()

