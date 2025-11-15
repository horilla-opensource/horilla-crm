"""
App configuration for the Reports module in Horilla CRM.
Handles app metadata and auto-registering URLs.
"""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class ReportsConfig(AppConfig):
    """
    Configuration class for the Reports app in Horilla CRM.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.reports"
    verbose_name = _("Reports")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/reports/",
                "view_or_include": "horilla_crm.reports.api.urls",
                "name": "horilla_crm_reports_api",
                "namespace": "horilla_crm_reports",
            }
        ]

    def ready(self):
        """Auto-register URLs and import the app menu."""
        from django.urls import include, path

        from horilla.urls import urlpatterns

        try:
            urlpatterns.append(
                path("reports/", include("horilla_crm.reports.urls")),
            )

            __import__("horilla_crm.reports.menu")  # noqa: F401
            __import__("horilla_crm.reports.signals")
        except Exception as e:
            import logging

            logging.warning("ReportsConfig.ready failed: %s", e)

        super().ready()
