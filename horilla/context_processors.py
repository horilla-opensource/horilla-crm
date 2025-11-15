"""
Context processors for the Horilla application.

Provides sidebar, company, language, recently viewed items, notifications,
and menu context for templates.
"""

import json

from django.conf import settings
from django.utils.translation import get_language

from horilla.menu.floating_menu import get_floating_menu
from horilla.menu.main_section_menu import get_main_section_menu
from horilla.menu.my_settings_menu import get_my_settings_menu
from horilla.menu.settings_menu import get_settings_menu
from horilla.menu.sub_section_menu import get_sub_section_menu
from horilla_core.models import Company, RecentlyViewed
from horilla_notifications.models import Notification


def company_list(request):
    """Return all available companies."""
    return {"available_companies": Company.objects.all()}


def allowed_languages(request):
    """
    Return only languages defined in ALLOWED_LANGUAGES.
    """
    return {
        "allowed_languages": [
            {
                "code": code,
                "name": name,
                "flag": flag,
                "active": (code == get_language()),
            }
            for code, name, flag in settings.ALLOWED_LANGUAGES
        ]
    }


def recently_viewed_items(request):
    """
    Return the user's 6 most recently viewed items, cleaning invalid references.
    """
    if request.user.is_authenticated:
        items = []
        for rv in RecentlyViewed.objects.filter(user=request.user).order_by(
            "-viewed_at"
        )[:6]:
            try:
                if rv.content_object:
                    items.append(rv)
            except Exception:
                rv.delete()
        return {"recently_viewed_items": items}
    return {}


def unread_notifications(request):
    """Return unread notifications for the current user."""
    if request.user.is_authenticated:
        return {
            "unread_notifications": Notification.objects.filter(
                user=request.user, read=False
            ).order_by("-created_at")
        }
    return {}


def menu_context_processor(request):
    """Return context for various menus."""

    current_app_label = (
        request.resolver_match.app_name if request.resolver_match else None
    )
    section_param = request.GET.get("section")

    return {
        "main_section_menu": get_main_section_menu(request),
        "sub_section_menu": get_sub_section_menu(request),
        "settings_menu": get_settings_menu(request),
        "floating_menu": get_floating_menu(request),
        "my_settings_menu": get_my_settings_menu(request),
        "current_section": section_param,
        "current_app_label": current_app_label,
    }


def currency_context(request):
    """
    Add currency information to all templates automatically
    This makes user_currency and default_currency available in ALL templates
    """
    if not request.user.is_authenticated:
        return {}

    from horilla_core.models import MultipleCurrency

    user_currency = MultipleCurrency.get_user_currency(request.user)
    default_currency = None

    if hasattr(request.user, "company") and request.user.company:
        default_currency = MultipleCurrency.get_default_currency(request.user.company)

    return {
        "user_currency": user_currency,
        "default_currency": default_currency,
    }
