"""Leads app configuration."""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class LeadsConfig(AppConfig):
    """Leads App Configuration"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.leads"
    verbose_name = _("Leads")

    demo_data = {
        "files": [
            (4, "load_data/lead_stage.json"),
            (5, "load_data/leads.json"),
        ],
        "order": 2,
    }

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/leads/",
                "view_or_include": "horilla_crm.leads.api.urls",
                "name": "horilla_crm_leads_api",
                "namespace": "horilla_crm_leads",
            }
        ]

    def ready(self):
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from horilla.urls import urlpatterns

            __import__("horilla_crm.leads.signals")  # noqa: F401
            __import__("horilla_crm.leads.menu")  # noqa: F401

            urlpatterns.append(
                path("leads/", include("horilla_crm.leads.urls", namespace="leads")),
            )

            from django.conf import settings

            from .celery_schedules import HORILLA_CRM_BEAT_SCHEDULE

            if not hasattr(settings, "CELERY_BEAT_SCHEDULE"):
                settings.CELERY_BEAT_SCHEDULE = {}

            settings.CELERY_BEAT_SCHEDULE.update(HORILLA_CRM_BEAT_SCHEDULE)

        except Exception as e:
            import logging

            logging.warning("LeadsConfig.ready failed: %s", e)
        super().ready()
