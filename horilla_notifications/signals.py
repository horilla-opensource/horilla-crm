from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Notification


@receiver(post_save, sender=Notification)
def send_notification(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{instance.user.id}",  # User-specific group
            {
                "type": "notification_message",
                "message": instance.message,
                "created_at": instance.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "sender": instance.sender.username if instance.sender else "System",
                "id": instance.id,
                "open_url": reverse(
                    "horilla_notifications:open_notification", args=[instance.id]
                ),
            },
        )
