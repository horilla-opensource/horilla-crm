"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Accounts app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import floating_menu, main_section_menu, sub_section_menu
from horilla_crm.accounts.models import Account


@floating_menu.register
class AccountFloating:
    """
    Configuration for the Account floating menu.

    Defines the title, URL, icon, HTMX behavior, and permissions
    for creating a new Account via the floating menu.
    """

    title = Account()._meta.verbose_name
    url = reverse_lazy("accounts:account_create_form_view")
    icon = "/assets/icons/account.svg"
    items = {
        "hx-target": "#modalBox",
        "hx-swap": "innerHTML",
        "onclick": "openModal()",
        "perm": ["accounts.add_account"],
    }


@main_section_menu.register
class PeopleSection:
    """
    Registers the People section in the main sidebar.
    """

    section = "people"
    name = _("People")
    icon = "/assets/icons/customer.svg"
    position = 2


@sub_section_menu.register
class AccountsSubSection:
    """
    Registers the accounts menu to sub section in the main sidebar.
    """

    section = "people"
    verbose_name = _("Accounts")
    icon = "assets/icons/account.svg"
    url = reverse_lazy("accounts:accounts_view")
    app_label = "accounts"
    perm = ["accounts.view_account", "accounts.view_own_account"]
    position = 1
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
