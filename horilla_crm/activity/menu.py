"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Activities app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import sub_section_menu


@sub_section_menu.register
class ActivitySubSection:
    """
    Registers the activity menu to sub section in the main sidebar.
    """

    section = "schedule"
    verbose_name = _("Activities")
    icon = "assets/icons/activity.svg"
    url = reverse_lazy("activity:activity_view")
    app_label = "activity"
    position = 2
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
