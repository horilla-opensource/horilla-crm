"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Timeline app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import main_section_menu, sub_section_menu


@main_section_menu.register
class AnalyticsSection:
    """
    Registers the Schedule section in the main sidebar.
    """

    section = "schedule"
    name = _("Schedule")
    icon = "/assets/icons/schedule.svg"
    position = 4


@sub_section_menu.register
class CalendarSubSection:
    """
    Registers the timeline menu to sub section in the main sidebar.
    """

    section = "schedule"
    verbose_name = _("Calendar")
    icon = "assets/icons/calendar.svg"
    url = reverse_lazy("timeline:calendar_view")
    app_label = "timeline"
    position = 1
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
