"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Forecast app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import settings_menu, sub_section_menu
from horilla_crm.forecast.models import ForecastTarget, ForecastType


@sub_section_menu.register
class ForecastsSubSection:
    """
    Registers the forecast menu to sub section in the main sidebar.
    """

    section = "sales"
    verbose_name = _("Forecast")
    icon = "assets/icons/forecast.svg"
    url = reverse_lazy("forecast:forecast_view")
    app_label = "forecast"
    perm = [
        "opportunities.view_opportunity",
        "opportunities.view_own_opportunity",
    ]
    position = 4
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }


@settings_menu.register
class ForecastSettings:
    """Settings menu entries for the Forecast module."""

    title = _("Forecast")
    icon = "/assets/icons/growth.svg"
    order = 6
    items = [
        {
            "label": ForecastType()._meta.verbose_name,
            "url": reverse_lazy("forecast:forecast_type_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#forecast-type-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "forecast.view_forecasttype",
        },
        {
            "label": ForecastTarget()._meta.verbose_name,
            "url": reverse_lazy("forecast:forecast_target_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#forecast-target-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "forecast.view_forecasttarget",
        },
    ]
