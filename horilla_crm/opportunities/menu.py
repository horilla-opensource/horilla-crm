"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Opportunities app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import (
    floating_menu,
    my_settings_menu,
    settings_menu,
    sub_section_menu,
)
from horilla_crm.opportunities.models import (
    Opportunity,
    OpportunitySettings,
    OpportunityStage,
)


@sub_section_menu.register
class OpportunitiesSubSection:
    """
    Registers the opportunities menu to sub section in the main sidebar.
    """

    section = "sales"
    verbose_name = _("Opportunities")
    icon = "assets/icons/opportunities.svg"
    url = reverse_lazy("opportunities:opportunities_view")
    app_label = "opportunities"
    perm = [
        "opportunities.view_opportunity",
        "opportunities.view_own_opportunity",
    ]
    position = 3
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }


@floating_menu.register
class OpportunitiesFloating:
    """Floating menu configuration for the Opportunity model."""

    title = Opportunity()._meta.verbose_name
    url = reverse_lazy("opportunities:opportunity_create")
    icon = "/assets/icons/opportunities.svg"
    items = {
        "hx-target": "#modalBox",
        "hx-swap": "innerHTML",
        "onclick": "openModal()",
        "perm": ["opportunities.add_opportunity"],
    }


@my_settings_menu.register
class OpportunityTeamSettings:
    """'My Settings' menu entry for Opportunity Teams."""

    title = _("Opportunity Team")
    url = reverse_lazy("opportunities:opportunity_team_view")
    active_urls = [
        "opportunities:opportunity_team_view",
        "opportunities:opportunity_team_detail_view",
    ]
    order = 5
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#opportunity-team-view",
        "hx-select-oob": "#my-settings-sidebar",
    }
    condition = staticmethod(OpportunitySettings.is_team_selling_enabled)


@settings_menu.register
class OpportunitiesSettings:
    """Settings menu entries for the Opportunities module."""

    title = _("Opportunity")
    icon = "/assets/icons/oppor.svg"
    order = 5
    items = [
        {
            "label": OpportunityStage()._meta.verbose_name,
            "url": reverse_lazy("opportunities:opportunity_stage_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#opportunity-stage-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "opportunities.view_opportunitystage",
        },
        {
            "label": _("Opportunity Team Settings"),
            "url": reverse_lazy("opportunities:team_selling_setup"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#opportunity-team-settings",
            "hx-select-oob": "#settings-sidebar",
            "perm": "opportunities.view_opportunitysettings",
        },
        {
            "label": _("Opportunity Split Settings"),
            "url": reverse_lazy("opportunities:opportunity_split_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#opportunity-split-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "opportunities.view_opportunitysplittype",
            "condition": staticmethod(OpportunitySettings.is_team_selling_enabled),
        },
    ]
