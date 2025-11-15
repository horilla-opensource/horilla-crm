"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla Core app.
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import settings_menu


@settings_menu.register
class MailSettings:
    """Settings menu entries for the Forecast module."""

    title = _("Mail")
    icon = "/assets/icons/email-orange.svg"
    order = 3
    items = [
        {
            "label": _("Outgoing Mail Server"),
            "url": reverse_lazy("horilla_mail:mail_server_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#mail-server-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_mail.view_horillamailconfiguration",
        },
        {
            "label": _("Incoming Mail Server"),
            "url": reverse_lazy("horilla_mail:incoming_mail_server_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#mail-server-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_mail.view_horillamailconfiguration",
        },
        {
            "label": _("Mail Template"),
            "url": reverse_lazy("horilla_mail:mail_template_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#mail-template-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_mail.view_horillamailtemplate",
        },
    ]
