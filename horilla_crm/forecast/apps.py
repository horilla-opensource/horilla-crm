"""App configuration for the forecast module."""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class ForecastConfig(AppConfig):
    """Configuration class for the Forecast app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.forecast"
    verbose_name = _("Forecast")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/forecast/",
                "view_or_include": "horilla_crm.forecast.api.urls",
                "name": "horilla_crm_forecast_api",
                "namespace": "horilla_crm_forecast",
            }
        ]

    demo_data_files = [
        (7, "load_data/forecast_type.json"),
    ]

    def ready(self):
        try:
            from django.urls import include, path

            from horilla.urls import urlpatterns

            urlpatterns.append(
                path("forecast/", include("horilla_crm.forecast.urls")),
            )

            __import__("horilla_crm.forecast.menu")
            __import__("horilla_crm.forecast.signals")

        except Exception as e:
            import logging

            logging.warning("ForecastsConfig.ready failed: %s", e)

        super().ready()
