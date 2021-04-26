import os
from celery import Celery

BROKER_URI = 'pyamqp://rabbitmq'
BACKEND_URI = 'redis://redis'

app = Celery(
    'celery_tasks',
    broker=BACKEND_URI,
    backend=BACKEND_URI,
    broker_heartbeat=0,
    include=['celery_tasks.tasks']
)
