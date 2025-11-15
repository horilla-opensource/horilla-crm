from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from horilla_core.models import ListColumnVisibility

# Define your horilla_generics signals here


@receiver(post_delete, sender=ListColumnVisibility)
def clear_cache_on_delete(sender, instance, **kwargs):
    """
    Clear the cache for the corresponding ListColumnVisibility object when it is deleted.
    """
    cache_key = f"visible_columns_{instance.user.id}_{instance.app_label}_{instance.model_name}_{instance.context}_{instance.url_name}"
    cache.delete(cache_key)
