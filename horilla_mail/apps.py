from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class Horilla_mailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_mail"
    verbose_name = _("Mail System")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "mail/",
                "view_or_include": "horilla_mail.api.urls",
                "name": "horilla_mail_api",
                "namespace": "horilla_mail",
            }
        ]

    def ready(self):
        try:
            # Auto-register this app's main URLs (non-API)
            from django.urls import include, path

            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("mail/", include("horilla_mail.urls")),
            )

            __import__("horilla_mail.signals")
            __import__("horilla_mail.scheduler")
            __import__("horilla_mail.menu")

            from django.conf import settings

            from .celery_schedules import HORILLA_BEAT_SCHEDULE

            if not hasattr(settings, "CELERY_BEAT_SCHEDULE"):
                settings.CELERY_BEAT_SCHEDULE = {}

            settings.CELERY_BEAT_SCHEDULE.update(HORILLA_BEAT_SCHEDULE)

        except Exception as e:
            import logging

            logging.warning(f"Command.ready failed  :   ", e)
            pass

        super().ready()
