"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the horilla_keys app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import my_settings_menu

# Define your menu registration logic here


@my_settings_menu.register
class ShortKeySettings:
    """'My Settings' menu entry for Short Keys."""

    title = _("Short Keys")
    url = reverse_lazy("horilla_keys:short_key_view")
    active_urls = [
        "horilla_keys:short_key_view",
    ]
    hx_select_id = "#short-key-view"
    order = 6
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#short-key-view",
        "hx-select-oob": "#my-settings-sidebar",
    }
