import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")

app = Celery("sales_crm")

# Read config from Django settings, CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all INSTALLED_APPS
app.autodiscover_tasks()
