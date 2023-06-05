import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'News.settings')

app = Celery('News')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send_email_every_week': {
        'task': 'news_portal.tasks.send_email_every_week',
        'schedule': crontab(minute=56, hour=6, day_of_week='thu')
    }
}
