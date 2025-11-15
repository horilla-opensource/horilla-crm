"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Leads app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import (
    floating_menu,
    main_section_menu,
    settings_menu,
    sub_section_menu,
)
from horilla_crm.leads.models import Lead, LeadStatus


@floating_menu.register
class LeadFloating:
    """Floating menu for Lead model"""

    title = Lead()._meta.verbose_name
    url = reverse_lazy("leads:leads_create")
    icon = "/assets/icons/leads.svg"
    items = {
        "hx-target": "#modalBox",
        "hx-swap": "innerHTML",
        "onclick": "openModal()",
        "perm": ["leads.add_lead"],
    }


@settings_menu.register
class LeadsSettings:
    """Settings menu for Lead module"""

    title = _("Lead")
    icon = "/assets/icons/lead1.svg"
    order = 4
    items = [
        {
            "label": LeadStatus()._meta.verbose_name,
            "url": reverse_lazy("leads:lead_stage_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#leads-status-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "leads.view_leadstatus",
        },
        {
            "label": "Mail to Lead",
            "url": reverse_lazy("leads:mail_to_lead_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#mail-to-lead-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "leads.view_emailtoleadconfig",
        },
    ]


@main_section_menu.register
class SalesSection:
    """
    Registers the Sales section in the main sidebar.
    """

    section = "sales"
    name = _("Sales")
    icon = "/assets/icons/sales.svg"
    position = 1


@sub_section_menu.register
class LeadSubSection:
    """
    Registers the lead menu to sub section in the main sidebar.
    """

    section = "sales"
    verbose_name = _("Leads")
    icon = "assets/icons/leads.svg"
    url = reverse_lazy("leads:leads_view")
    app_label = "leads"
    perm = ["leads.view_lead", "leads.view_own_lead"]
    position = 1
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
