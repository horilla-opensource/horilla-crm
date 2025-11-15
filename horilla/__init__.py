# horilla/__init__.py
from .horilla_celery import app as celery_app

__all__ = ("celery_app",)
