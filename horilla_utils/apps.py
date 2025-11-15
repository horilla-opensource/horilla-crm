"""
App configuration for the Horilla utilities module.

This file defines the configuration class for the Horilla utilities
application, specifying its metadata and settings.
"""

from django.apps import AppConfig

from horilla.settings import horilla_apps


class HorillaUtilsConfig(AppConfig):
    """
    Configuration class for the Horilla utilities application.

    This class specifies the default auto field type and the name of
    the application, which is used by Django to identify the app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_utils"
