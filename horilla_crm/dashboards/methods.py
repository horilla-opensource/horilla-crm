# Define your dashboards helper methods here
from django.apps import apps
from django.db import models

from horilla.registry.feature import FEATURE_REGISTRY


def limit_content_types():
    """
    Limit ContentType choices to only models that have
    'dashboard_component_models = True'.
    """
    includable_models = []
    for model in FEATURE_REGISTRY["dashboard_component_models"]:
        includable_models.append(model._meta.model_name.lower())

    return models.Q(model__in=includable_models)
