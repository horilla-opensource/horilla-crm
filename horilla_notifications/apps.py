from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_notifications"
    verbose_name = _("Notifications")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "notifications/",
                "view_or_include": "horilla_notifications.api.urls",
                "name": "horilla_notifications_api",
                "namespace": "horilla_notifications",
            }
        ]

    def ready(self):
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("notifications/", include("horilla_notifications.urls")),
            )

            __import__("horilla_notifications.signals")

        except Exception as e:
            import logging

            logging.warning(f"NotificationsConfig.ready failed: {e}")

        super().ready()
