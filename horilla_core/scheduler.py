# myapp/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
from django.utils import timezone

from horilla_core.models import RecycleBin, RecycleBinPolicy


def fiscal_year_update():
    call_command("update_fiscal_year")


def clear_expired_recyclebin():
    now = timezone.now()
    total_deleted = 0
    for policy in RecycleBinPolicy.objects.select_related("company"):
        cutoff = now - timezone.timedelta(days=policy.retention_days)
        deleted_count, _ = RecycleBin.objects.filter(
            company=policy.company, deleted_at__date__lte=cutoff.date()
        ).delete()
        total_deleted += deleted_count


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fiscal_year_update, "interval", hours=12, id="fiscal_year_update_job"
    )
    scheduler.add_job(
        clear_expired_recyclebin,
        "interval",
        hours=4,
        id="clear_expired_recyclebin_job",
        replace_existing=True,
    )
    scheduler.start()
