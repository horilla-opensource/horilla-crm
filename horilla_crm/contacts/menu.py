"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla CRM Contacts app
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import floating_menu, sub_section_menu
from horilla_crm.contacts.models import Contact


@floating_menu.register
class ContactFloating:
    """Configuration for the Contact floating menu."""

    title = Contact()._meta.verbose_name
    url = reverse_lazy("contacts:contact_create_form")
    icon = "/assets/icons/contact.svg"
    items = {
        "hx-target": "#modalBox",
        "hx-swap": "innerHTML",
        "onclick": "openModal()",
        "perm": ["contacts.add_contact"],
    }


@sub_section_menu.register
class ContactsSubSection:
    """
    Registers the contacts menu to sub section in the main sidebar.
    """

    section = "people"
    verbose_name = _("Contacts")
    icon = "assets/icons/contact.svg"
    url = reverse_lazy("contacts:contacts_view")
    app_label = "contacts"
    perm = ["contacts.view_contact", "contacts.view_own_contact"]
    position = 2
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }
