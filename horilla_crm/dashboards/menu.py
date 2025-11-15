"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Dashboards app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import main_section_menu, sub_section_menu


@main_section_menu.register
class HomeSection:
    """
    Registers the Home section in the main sidebar.
    """

    section = "home"
    name = _("Home")
    icon = "/assets/icons/home.svg"
    position = 0


@sub_section_menu.register
class DashboardsSubSection:
    """
    Registers the lead dashboards to sub section in the main sidebar.
    """

    section = "analytics"
    verbose_name = _("Dashboards")
    icon = "assets/icons/dashboards.svg"
    url = reverse_lazy("dashboards:dashboard_list_view")
    app_label = "dashboards"
    perm = ["dashboards.view_dashboard", "dashboards.view_own_dashboard"]
    position = 2
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
