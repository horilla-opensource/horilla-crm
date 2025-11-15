from celery.schedules import crontab

HORILLA_CRM_BEAT_SCHEDULE = {
    "fetch-emails-every-minute": {
        "task": "horilla_crm.leads.tasks.fetch_emails_to_leads",  # Fixed path
        "schedule": crontab(minute="*"),  # Every minute
    },
}
