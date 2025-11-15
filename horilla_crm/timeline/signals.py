from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from horilla_core.models import HorillaUser
from horilla_keys.models import ShortcutKey


# Define your timeline signals here
@receiver(post_save, sender=HorillaUser)
def create_calendar_shortcuts(sender, instance, created, **kwargs):
    predefined = [
        {"page": "/timeline/calendar-view/", "key": "I", "command": "alt"},
    ]

    for item in predefined:
        if not ShortcutKey.objects.filter(user=instance, page=item["page"]).exists():
            ShortcutKey.objects.create(
                user=instance,
                page=item["page"],
                key=item["key"],
                command=item["command"],
                company=instance.company,
            )
