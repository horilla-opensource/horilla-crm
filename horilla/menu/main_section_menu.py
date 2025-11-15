"""
This module defines a registry for managing main section menu entries in Horilla.
"""

from typing import Any, Dict, List, Type

# Registry to hold all main section menu classes
main_section_menu: List[Any] = []


def register(cls: Type[Any]):
    """Decorator to register a main section menu class."""
    main_section_menu.append(cls)
    return cls


def get_main_section_menu(request=None) -> List[Dict]:
    """
    Return all registered main section menu items.

    Returns:
        A list of dictionaries representing menu items, sorted by position.
    """
    pages = []
    for cls in main_section_menu:
        obj = cls()
        item = {
            "section": getattr(obj, "section", None),
            "name": getattr(obj, "name", None),
            "url": getattr(obj, "url", None),
            "icon": getattr(obj, "icon", None),
            "position": getattr(obj, "position", None),
        }
        pages.append(item)

    pages.sort(key=lambda x: (x["position"] is None, x["position"]))
    return pages
