"""Extension of INSTALLED_APPS with Horilla modules."""

from horilla.settings.base import INSTALLED_APPS

INSTALLED_APPS.extend(
    [
        "horilla_crm.accounts",
        "horilla_crm.contacts",
        "horilla_crm.leads",
        "horilla_crm.scoring_rules",
        "horilla_crm.campaigns",
        "horilla_crm.opportunities",
        "horilla_crm.forecast",
        "booking",
        "calls",
        "custom_fields",
    ]
)
