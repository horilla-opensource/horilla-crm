from datetime import timedelta

from celery.schedules import crontab

HORILLA_BEAT_SCHEDULE = {
    "process-scheduled-exports": {
        "task": "horilla_core.tasks.process_scheduled_exports",
        "schedule": timedelta(seconds=10),
    },
}
