"""App configuration for the opportunities module."""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class OpportunitiesConfig(AppConfig):
    """Configuration class for the Opportunities app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.opportunities"
    verbose_name = _("Opportunities")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/opportunities/",
                "view_or_include": "horilla_crm.opportunities.api.urls",
                "name": "horilla_crm_opportunities_api",
                "namespace": "horilla_crm_opportunities",
            }
        ]

    demo_data_files = [
        (8, "load_data/opportunity_stage.json"),
        (9, "load_data/opportunity.json"),
    ]

    demo_data_config = {
        "key": "opportunities_count",
        "display_name": _("Opportunities"),
        "order": 3,
    }

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        try:
            urlpatterns.append(
                path("opportunities/", include("horilla_crm.opportunities.urls")),
            )

            __import__("horilla_crm.opportunities.menu")
            __import__("horilla_crm.opportunities.signals")

        except Exception as e:
            import logging

            logging.warning("OpportunitiesConfig.ready failed: %s", e)

        super().ready()
