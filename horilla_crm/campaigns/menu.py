"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Campaigns app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import floating_menu, sub_section_menu
from horilla_crm.campaigns.models import Campaign


@floating_menu.register
class CampaignFloating:
    """
    Campaign Floating Menu
    """

    title = Campaign()._meta.verbose_name
    url = reverse_lazy("campaigns:campaign_create")
    icon = "/assets/icons/campaign.svg"
    items = {
        "hx-target": "#modalBox",
        "hx-swap": "innerHTML",
        "onclick": "openModal()",
        "perm": ["campaigns.add_campaign"],
    }


@sub_section_menu.register
class CampaignSubSection:
    """
    Registers the campaigns menu to sub section in the main sidebar.
    """

    section = "sales"
    verbose_name = _("Campaigns")
    icon = "assets/icons/campaign.svg"
    url = reverse_lazy("campaigns:campaign_view")
    app_label = "campaigns"
    perm = ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    position = 2
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
