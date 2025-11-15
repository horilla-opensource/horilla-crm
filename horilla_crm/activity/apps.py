"""App configuration for the activity module."""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class ActivityConfig(AppConfig):
    """
    Configuration class for the Activity app in Horilla CRM.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.activity"
    verbose_name = _("Activity")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/activity/",
                "view_or_include": "horilla_crm.activity.api.urls",
                "name": "horilla_crm_activity_api",
                "namespace": "horilla_crm_activity",
            }
        ]

    def ready(self):
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from horilla.urls import urlpatterns

            urlpatterns.append(
                path("activity/", include("horilla_crm.activity.urls")),
            )

            __import__("horilla_crm.activity.menu")  # noqa: F401
            __import__("horilla_crm.activity.signals")  # noqa:F401
        except Exception as e:
            import logging

            logging.warning("ActivityConfig.ready failed: %s", e)

        super().ready()
