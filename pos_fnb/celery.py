import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_fnb.settings')

app = Celery('pos_fnb')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
