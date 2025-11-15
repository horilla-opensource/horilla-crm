"""App configuration for the contacts module."""

from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class ContactsConfig(AppConfig):
    """Configuration class for the Contacts app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_crm.contacts"
    verbose_name = _("Contacts")
    demo_data_files = [
        (11, "load_data/contact.json"),
    ]

    demo_data_config = {
        "key": "contacts_count",
        "display_name": _("Contacts"),
        "order": 6,
    }

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/contacts/",
                "view_or_include": "horilla_crm.contacts.api.urls",
                "name": "horilla_crm_contacts_api",
                "namespace": "horilla_crm_contacts",
            }
        ]

    def ready(self):
        try:
            from django.urls import include, path

            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("contacts/", include("horilla_crm.contacts.urls")),
            )

            __import__("horilla_crm.contacts.menu")  # noqa: F401
            __import__("horilla_crm.contacts.signals")  # noqa:F401
        except Exception as e:
            import logging

            logging.warning("ContactsConfig.ready failed: %s", e)

        super().ready()
