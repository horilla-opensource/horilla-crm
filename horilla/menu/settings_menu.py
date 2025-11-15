# horilla/settings_page.py
from typing import Any, Callable, Dict, List, Type

settings_registry: List[Any] = []


def register(cls: Type[Any]):
    """Decorator to register a settings page class."""
    settings_registry.append(cls)
    return cls


def get_settings_menu(request=None) -> List[Dict]:
    """Return all registered settings pages as dicts (optionally filter by request)."""
    pages = []

    for cls in sorted(settings_registry, key=lambda c: getattr(c, "order", 0)):
        obj = cls()

        condition = getattr(obj, "condition", True)
        if callable(condition):
            if not request or not condition(request):
                continue
        elif not condition:
            continue

        data = {
            "title": getattr(obj, "title", None),
            "icon": getattr(obj, "icon", None),
            "items": [],
        }

        perm_list = []
        items = getattr(obj, "items", [])
        items = sorted(items, key=lambda i: i.get("order", 0))

        for item in items:
            if callable(item):
                item = item(request) or {}
                if not item:
                    continue

            item_condition = item.get("condition", True)
            if callable(item_condition):
                if not request or not item_condition(request):
                    continue
            elif not item_condition:
                continue

            data["items"].append(item)

            if (
                isinstance(item, dict)
                and item.get("perm")
                and isinstance(item["perm"], str)
            ):
                perm_list.append(item["perm"])

        if (
            request
            and request.user.is_authenticated
            and (not perm_list or request.user.has_any_perms(perm_list))
        ):
            pages.append(data)

    return pages
