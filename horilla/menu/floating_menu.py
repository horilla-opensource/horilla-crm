"""
Floating menu system for Horilla, with registration and permission-based filtering.
"""

from typing import Any, Dict, List, Type

floating_registry: List[Any] = []


def register(cls: Type[Any]):
    """Decorator to register a floating menu class."""
    floating_registry.append(cls)
    return cls


def get_floating_menu(request=None) -> List[Dict]:
    """Return all registered pages as dicts (optionally filter by request)."""
    pages = []
    for cls in floating_registry:
        obj = cls()
        if hasattr(obj, "is_enabled") and callable(obj.is_enabled):
            if not obj.is_enabled(request):
                continue
        items = getattr(obj, "items", {}) or {}

        perm_list = []
        if "perm" in items:
            if isinstance(items["perm"], str):
                perm_list = [items["perm"]]
            elif isinstance(items["perm"], (list, tuple)):
                perm_list = items["perm"]

        if callable(items):
            items = items(request) or {}

        data = {
            "title": getattr(obj, "title", None),
            "url": getattr(obj, "url", None),
            "icon": getattr(obj, "icon", None),
            "items": items,
        }

        if not request or not request.user.is_authenticated:
            continue

        if not perm_list or request.user.has_perms(perm_list):
            pages.append(data)

    return pages
