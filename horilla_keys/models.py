"""
Models for the horilla_keys app
"""

from django.conf import settings
from django.db import models
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from horilla.menu.main_section_menu import get_main_section_menu
from horilla.menu.my_settings_menu import get_my_settings_menu
from horilla.menu.settings_menu import get_settings_menu
from horilla.menu.sub_section_menu import get_sub_section_menu
from horilla_core.models import HorillaCoreModel
from horilla_utils.middlewares import _thread_local


class ShortcutKey(HorillaCoreModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shortcut_keys",
        verbose_name=_("User"),
    )
    page = models.CharField(max_length=100, verbose_name=_("Page"))
    key = models.CharField(max_length=1, verbose_name=_("Key"))
    command = models.CharField(
        max_length=20,
        verbose_name=_("Command Key"),
    )

    OWNER_FIELDS = ["user"]

    class Meta:
        unique_together = ("user", "page")
        verbose_name = _("Shortcut Key")
        verbose_name_plural = _("Shortcut Keys")

    def __str__(self):
        return self.page

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("horilla_keys:short_key_update", kwargs={"pk": self.pk})

    def custom_key_col(self):
        """Display formatted key combination based on OS."""
        request = getattr(_thread_local, "request", None)
        command_lower = self.command.lower()

        is_modifier = command_lower == "alt"

        if request and is_modifier:
            user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
            is_mac = "mac" in user_agent or "darwin" in user_agent

            if is_mac:
                display_command = "OPTION (⌥)"
            else:
                display_command = "ALT"
        else:
            display_command = self.command.upper()

        return mark_safe(
            f'<span style="color:red;">{display_command}</span> + {self.key.upper()}'
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy("horilla_keys:short_key_delete", kwargs={"pk": self.pk})

    def get_page_title(self):
        """
        Returns the human-readable title or label for this page.
        Checks both main and sub-section menus.
        """

        request = getattr(_thread_local, "request", None)

        if self.page == "/":
            return "Home"

        for item in get_main_section_menu(None):
            if item.get("url") == self.page:
                return item.get("name") or item.get("label") or item.get("title")

        sub_sections = get_sub_section_menu(None)
        for section_name, items in sub_sections.items():
            for item in items:
                if item.get("url") == self.page:
                    return item.get("label") or item.get("name") or item.get("title")

        main_settings = get_settings_menu(request)
        for item in main_settings:
            title = item.get("title")
            for subitem in item.get("items", []):
                label = subitem.get("label")
                url = subitem.get("url")
                if url == self.page:
                    return label or title

        my_settings = get_my_settings_menu(request)
        for item in my_settings:
            title = item.get("title")
            url = item.get("url")
            if url == self.page:
                return title

        return self.page

    def get_section(self):
        """
        Returns the main or sub-section for this page.
        Only returns 'home' if the page is '/'.
        Otherwise, returns None if no section is found.
        """
        if self.page == "/":
            return "home"

        for item in get_main_section_menu(None):
            if item.get("url") == self.page:
                return item.get("section")

        sub_sections = get_sub_section_menu(None)
        for section_name, items in sub_sections.items():
            for item in items:
                if item.get("url") == self.page:
                    return section_name

        return None
