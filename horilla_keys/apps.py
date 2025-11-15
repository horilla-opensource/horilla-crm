"""
AppConfig for the horilla_keys app
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class Horilla_keysConfig(AppConfig):
    """App configuration class for horilla_keys."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_keys"
    verbose_name = _("Keyboard Shortcuts")
    js_files = "horilla_keys/assets/js/short_key.js"

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "keys/",
                "view_or_include": "horilla_keys.api.urls",
                "name": "horilla_keys_api",
                "namespace": "horilla_keys",
            }
        ]

    def ready(self):
        """Run app initialization logic (executed after Django setup).
        Used to auto-register URLs and connect signals if required.
        """
        try:
            # Auto-register this app's main URLs (non-API)
            from django.urls import include, path

            from horilla.registry.js_registry import register_js
            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("shortkeys/", include("horilla_keys.urls")),
            )

            __import__("horilla_keys.menu")
            __import__("horilla_keys.signals")

            register_js(self.js_files)

        except Exception as e:
            import logging

            logging.warning(f"Horilla_keysConfig.ready failed  :  ", e)
            pass

        super().ready()
