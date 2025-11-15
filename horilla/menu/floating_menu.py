# horilla/menu/floating_menu.py
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

        if (
            request
            and request.user.is_authenticated
            and perm_list
            and request.user.has_perms(perm_list)
        ):
            pages.append(data)

    return pages
