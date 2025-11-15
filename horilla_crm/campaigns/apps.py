"""App configuration for the Campaign module."""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class CampaignsConfig(AppConfig):
    """Configuration class for the Campaigns app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.campaigns"
    verbose_name = _("Campaigns")
    demo_data_files = [
        (6, "load_data/campaign.json"),
    ]

    demo_data_config = {
        "key": "campaigns_count",
        "display_name": _("Campaigns"),
        "order": 4,
    }

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/campaigns/",
                "view_or_include": "horilla_crm.campaigns.api.urls",
                "name": "horilla_crm_campaigns_api",
                "namespace": "horilla_crm_campaigns",
            }
        ]

    def ready(self):
        try:
            from django.urls import include, path

            from horilla.urls import urlpatterns

            urlpatterns.append(
                path("campaigns/", include("horilla_crm.campaigns.urls")),
            )

            __import__("horilla_crm.campaigns.menu")  # noqa: F401
            __import__("horilla_crm.campaigns.signals")  # noqa:F401

        except Exception as e:
            import logging

            logging.warning("CampaignsConfig.ready failed: %s", e)
        super().ready()
