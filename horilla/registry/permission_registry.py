"""
Permission registry for Horilla core models.

This module provides a decorator and a set to manage models that should be
excluded from permission checks.
"""

PERMISSION_EXEMPT_MODELS = {
    "Session",
    "Migration",
    "LogEntry",
    "Group",
    "Permission",
    "ContentType",
}


def permission_exempt_model(cls):
    """
    Decorator to mark a model to be excluded from permission checks.

    Usage:
        @exclude_no_perm
        class HorillaModel(models.Model):
            ...
    """
    PERMISSION_EXEMPT_MODELS.add(cls.__name__)
    return cls
