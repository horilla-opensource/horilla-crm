from django.db.models.signals import post_delete
from django.dispatch import receiver

from horilla_mail.models import HorillaMailAttachment

# Define your horilla_mail signals here


@receiver(post_delete, sender=HorillaMailAttachment)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """Deletes file from storage when HorillaMailAttachment is deleted."""
    if instance.file:
        storage, path = instance.file.storage, instance.file.path
        if storage.exists(path):
            storage.delete(path)
