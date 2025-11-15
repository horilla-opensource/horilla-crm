""" "Configuration for the timeline app in Horilla CRM."""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class TimelineConfig(AppConfig):
    """Configuration class for the Timeline app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.timeline"
    verbose_name = _("Timeline")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/timeline/",
                "view_or_include": "horilla_crm.timeline.api.urls",
                "name": "horilla_crm_timeline_api",
                "namespace": "horilla_crm_timeline",
            }
        ]

    def ready(self):
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("timeline/", include("horilla_crm.timeline.urls")),
            )

            __import__("horilla_crm.timeline.menu")  # noqa: F401
            __import__("horilla_crm.timeline.signals")  # noqa:F401
        except ImportError:
            # Handle errors silently to prevent app load failure
            pass

        super().ready()
