"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Reports app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import main_section_menu, sub_section_menu


@main_section_menu.register
class AnalyticsSection:
    """
    Registers the Analytics section in the main sidebar.
    """

    section = "analytics"
    name = _("Analytics")
    icon = "/assets/icons/data-analytics.svg"
    position = 3


@sub_section_menu.register
class ReportsSubSection:
    """
    Registers the reports menu to sub section in the main sidebar.
    """

    section = "analytics"
    verbose_name = _("Reports")
    icon = "assets/icons/reports.svg"
    url = reverse_lazy("reports:reports_list_view")
    app_label = "reports"
    perm = ["reports.view_report", "reports.view_own_report"]
    position = 1
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
