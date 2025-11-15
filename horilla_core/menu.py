"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla Core app.
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import my_settings_menu, settings_menu
from horilla_core.models import (
    CustomerRole,
    Department,
    PartnerRole,
    Role,
    ScoringRule,
    TeamRole,
)


@my_settings_menu.register
class MyProfileSettings:
    """My Settings Menu entry for My profile."""

    title = _("Profile")
    url = reverse_lazy("horilla_core:my_profile_view")
    hx_select_id = "#my-profile-view"
    active_urls = "horilla_core:my_profile_view"
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#my-profile-view",
        "hx-select-oob": "#my-settings-sidebar",
        "style": "display:none",
    }


@my_settings_menu.register
class RegionalFormattingSettings:
    """My Settings Menu entry for Regional & Formatting settings."""

    title = _("Regional & Formatting")
    url = reverse_lazy("horilla_core:regional_formating_view")
    active_urls = "horilla_core:regional_formating_view"
    order = 1
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#regional-formating-view",
        "hx-select-oob": "#my-settings-sidebar",
    }


@my_settings_menu.register
class ChangePasswordSettings:
    """My Settings Menu entry for Change password."""

    title = _("Change Password")
    url = reverse_lazy("horilla_core:change_password_view")
    active_urls = "horilla_core:change_password_view"
    order = 2
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#change-password-view",
        "hx-select-oob": "#my-settings-sidebar",
    }


@my_settings_menu.register
class LoginHistorySettings:
    """My Settings Menu entry for User Login History settings."""

    title = _("Login History")
    url = reverse_lazy("horilla_core:user_login_history_view")
    active_urls = "horilla_core:user_login_history_view"
    order = 3
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#user-login-history-view",
        "hx-select-oob": "#my-settings-sidebar",
    }


@my_settings_menu.register
class HolidaySettings:
    """My Settings Menu entry for Holiday configuration."""

    title = _("Holiday")
    url = reverse_lazy("horilla_core:user_holiday_view")
    active_urls = "horilla_core:user_holiday_view"
    order = 4
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#user-holiday-view",
        "hx-select-oob": "#my-settings-sidebar",
    }


@settings_menu.register
class GeneralSettings:
    """Settings menu entries for the general."""

    title = _("General")
    icon = "/assets/icons/general.svg"
    order = 1
    items = [
        {
            "label": _("Company Information"),
            "url": reverse_lazy("horilla_core:company_information"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#company-information",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_company",
            "order": 1,
        },
        {
            "label": _("Users"),
            "url": reverse_lazy("horilla_core:user_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#users-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_horillauser",
            "order": 2,
        },
        {
            "label": _("Groups and Permissions"),
            "url": reverse_lazy("horilla_core:group_permission_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#permission-view",
            "hx-select-oob": "#settings-sidebar",
            "order": 3,
        },
    ]


@settings_menu.register
class BaseSettings:
    """Settings menu entries for the base."""

    title = _("Base")
    icon = "/assets/icons/base.svg"
    order = 2
    items = [
        {
            "label": Department()._meta.verbose_name,
            "url": reverse_lazy("horilla_core:department_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#department-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_department",
        },
        {
            "label": _("Branches"),
            "url": reverse_lazy("horilla_core:branches_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#branches-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_company",
        },
        {
            "label": ScoringRule()._meta.verbose_name,
            "url": reverse_lazy("horilla_core:scoring_rule_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#scoring-rule-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_scoringrule",
        },
        {
            "label": Role()._meta.verbose_name,
            "url": reverse_lazy("horilla_core:roles_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#role-container",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_role",
        },
        {
            "label": TeamRole()._meta.verbose_name,
            "url": reverse_lazy("horilla_core:team_role_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#team-role-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_teamrole",
        },
        {
            "label": CustomerRole()._meta.verbose_name,
            "url": reverse_lazy("horilla_core:customer_role_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#customer-role-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_customerrole",
        },
        {
            "label": PartnerRole()._meta.verbose_name,
            "url": reverse_lazy("horilla_core:partner_role_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#partner-role-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_partnerrole",
        },
    ]


@settings_menu.register
class DataManagementSettings:
    """Settings menu entries for the data management."""

    title = _("Data Mangement")
    icon = "/assets/icons/data.svg"
    order = 7
    items = [
        {
            "label": _("Import Data"),
            "url": reverse_lazy("horilla_core:import_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#import-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.can_view_horilla_import",
        },
        {
            "label": _("Export Data"),
            "url": reverse_lazy("horilla_core:export_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#export-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.can_view_horilla_export",
        },
        {
            "label": _("Recycle Bin"),
            "url": reverse_lazy("horilla_core:recycle_bin_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#recycle-bin-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "horilla_core.view_recyclebin",
        },
    ]
