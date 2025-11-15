from datetime import timedelta

from celery.schedules import crontab

HORILLA_BEAT_SCHEDULE = {
    "process-scheduled-mails-every-minute": {
        "task": "horilla_mail.tasks.process_scheduled_mails",
        "schedule": timedelta(seconds=10),
    },
}
