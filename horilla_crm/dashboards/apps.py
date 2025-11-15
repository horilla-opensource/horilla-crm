"""App configuration for dashboards app."""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class DashboardsConfig(AppConfig):
    """
    Dashboards App Configuration
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.dashboards"
    verbose_name = _("Dashboards")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/dashboards/",
                "view_or_include": "horilla_crm.dashboards.api.urls",
                "name": "horilla_crm_dashboards_api",
                "namespace": "horilla_crm_dashboards",
            }
        ]

    def ready(self):
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("dashboards/", include("horilla_crm.dashboards.urls")),
            )

            __import__("horilla_crm.dashboards.menu")  # noqa: F401
            __import__("horilla_crm.dashboards.signals")  # noqa:F401
        except Exception as e:
            import logging

            logging.warning("DashboardsConfig.ready failed: %s", e)
        super().ready()
