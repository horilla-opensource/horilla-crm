from horilla.menu import settings_menu
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _


@settings_menu.register
class CustomFieldsSettings:
    """Settings menu entry for Custom Fields."""

    title = _("Custom Field")
    icon = "/assets/icons/custom-field.svg"
    order = 10
    items = [
        {
            "label": _("Custom Fields"),
            "url": reverse_lazy("custom_fields:view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#custom-fields-view",
            "hx-select-oob": "#settings-sidebar",
        },
    ]
