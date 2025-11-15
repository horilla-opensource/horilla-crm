from typing import Any, List, Type

my_settings_menu: List[Any] = []


def register(cls: Type[Any]):
    """Decorator to register a settings menu class."""
    my_settings_menu.append(cls)
    return cls


def get_my_settings_menu(request=None) -> list[dict]:
    items = []
    for cls in my_settings_menu:
        obj = cls()

        condition = getattr(obj, "condition", True)
        if callable(condition):
            if not request or not condition(request):
                continue
        elif not condition:
            continue

        perms = getattr(obj, "permissions", [])
        if perms and request:
            if not request.user.is_authenticated or not request.user.has_perms(perms):
                continue

        data = {
            "title": getattr(obj, "title", None),
            "url": getattr(obj, "url", None),
            "active_urls": getattr(obj, "active_urls", []),
            "icon": getattr(obj, "icon", None),
            "order": getattr(obj, "order", 100),
            "attrs": getattr(obj, "attrs", {}),
        }
        items.append(data)

    return sorted(items, key=lambda x: x["order"])
