"""
Horilla Core App configuration.
Handles app setup, demo data, and scheduler,signals and menu initialization.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    """
    Configuration for the Horilla Core application.
    Includes URL registration and optional scheduler,signals and menu startup.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_core"
    verbose_name = _("Core System")
    demo_data_files = [
        (1, "load_data/company.json"),
        (2, "load_data/role.json"),
        (3, "load_data/users.json"),
    ]

    demo_data_config = {
        "key": "users_count",
        "display_name": _("Users"),
        "order": 1,
    }

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "core/",
                "view_or_include": "horilla_core.api.urls",
                "name": "horilla_core_api",
                "namespace": "horilla_core",
            }
        ]

    def ready(self):
        try:
            # Auto-register this app's main URLs (non-API)
            from django.urls import include, path

            from horilla.urls import urlpatterns

            # Add app URLs to main urlpatterns
            urlpatterns.append(
                path("", include("horilla_core.urls", namespace="horilla_core")),
            )

            # Import required modules
            __import__("horilla_core.signals")
            __import__("horilla_core.scheduler")
            __import__("horilla_core.login_history")
            __import__("horilla_core.menu")

            from django.conf import settings

            from .celery_schedules import HORILLA_BEAT_SCHEDULE

            if not hasattr(settings, "CELERY_BEAT_SCHEDULE"):
                settings.CELERY_BEAT_SCHEDULE = {}

            settings.CELERY_BEAT_SCHEDULE.update(HORILLA_BEAT_SCHEDULE)

        except Exception as e:
            import logging

            logging.warning(f"Horilla CoreConfig.ready failed: {e}")

        super().ready()

        # import sys
        # if any(cmd in sys.argv for cmd in ['runserver', 'apscheduler']):
        #     threading.Thread(target=scheduler.start_scheduler, daemon=True).start()
