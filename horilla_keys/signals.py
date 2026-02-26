"""
Signals for the horilla_keys app
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse_lazy

from horilla.auth.models import User
from horilla_keys.models import ShortcutKey


@receiver(post_save, sender=User)
def create_all_default_shortcuts(sender, instance, created, **kwargs):
    """
    Create all default shortcut keys for a newly created user
    using a single bulk insert.
    """

    if not created:
        return

    predefined = [
        {"page": "/", "key": "H", "command": "alt"},
        {"page": "/my-profile-view/", "key": "P", "command": "alt"},
        {"page": "/regional-formating-view/", "key": "G", "command": "alt"},
        {"page": "/user-login-history-view/", "key": "L", "command": "alt"},
        {"page": "/user-holiday-view/", "key": "V", "command": "alt"},
        {"page": "/shortkeys/short-key-view/", "key": "K", "command": "alt"},
        {"page": "/user-view/", "key": "U", "command": "alt"},
        {"page": "/branches-view/", "key": "B", "command": "alt"},
    ]

    shortcuts = [
        ShortcutKey(
            user=instance,
            page=item["page"],
            key=item["key"],
            command=item["command"],
            company=instance.company,
        )
        for item in predefined
    ]

    ShortcutKey.objects.bulk_create(shortcuts, ignore_conflicts=True)
