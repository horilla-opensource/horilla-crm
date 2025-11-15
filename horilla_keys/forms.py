"""
Forms for the horilla_keys app
"""

import platform

from django import forms

from horilla.menu.main_section_menu import get_main_section_menu
from horilla.menu.my_settings_menu import get_my_settings_menu
from horilla.menu.settings_menu import get_settings_menu
from horilla.menu.sub_section_menu import get_sub_section_menu
from horilla_core.models import Company, HorillaUser
from horilla_generics.forms import HorillaModelForm
from horilla_keys.models import ShortcutKey
from horilla_utils.middlewares import _thread_local


class ShortcutKeyForm(HorillaModelForm):
    class Meta:
        model = ShortcutKey
        fields = ["user", "page", "command", "key", "company"]

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        choices = []
        company = getattr(request, "active_company", None)

        self.fields["user"].queryset = HorillaUser.objects.filter(id=request.user.id)
        self.fields["company"].queryset = Company.objects.filter(id=company.id)

        main_sections = get_main_section_menu(request)
        for item in main_sections:
            name = item.get("name")
            url = item.get("url")

            if not url:
                if item.get("section") == "home":
                    url = "/"
            if name and url:
                choices.append((url, name))

        sub_sections = get_sub_section_menu(request)
        for section_name, items in sub_sections.items():
            for item in items:
                app_label = item.get("app_label")
                label = item.get("label")
                url = item.get("url")
                if app_label and url:
                    choices.append((url, label))

        my_settings = get_my_settings_menu(request)
        for item in my_settings:
            title = item.get("title")
            url = item.get("url")
            if title and url:
                choices.append((url, title))

        main_settings = get_settings_menu(request)
        for item in main_settings:
            title = item.get("title")
            for subitem in item.get("items", []):
                label = subitem.get("label")
                url = subitem.get("url")
                if label and url:
                    choices.append((url, label))

        self.fields["page"] = forms.ChoiceField(
            choices=[("", "Select Page")] + choices,
            label="Page",
            required=True,
            widget=forms.Select(
                attrs={
                    "class": "js-example-basic-single headselect w-full text-sm",
                    "data-placeholder": "Select Page",
                    "id": "id_page",
                }
            ),
        )

        command_choices = self._get_command_choices()

        self.fields["command"] = forms.ChoiceField(
            choices=[("", "Select Command Key")] + command_choices,
            label="Command Key",
            required=True,
            widget=forms.Select(
                attrs={
                    "class": "js-example-basic-single headselect w-full text-sm",
                    "data-placeholder": "Select Command Key",
                    "id": "id_command",
                }
            ),
        )

        if self.instance and self.instance.pk:
            self.fields["command"].initial = "alt"

    def _get_command_choices(self):
        """
        Get OS-specific command key choices
        """
        request = getattr(_thread_local, "request", None)
        user_agent = ""
        if request:
            user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        if "windows" in user_agent:
            os_name = "windows"

        elif "mac" in user_agent or "darwin" in user_agent:
            os_name = "mac"

        elif "linux" in user_agent or "ubuntu" in user_agent:
            os_name = "linux"
        else:
            os_name = platform.system().lower()

        if os_name == "mac":
            return [
                ("alt", "Option (⌥)"),
            ]
        else:
            return [
                ("alt", "Alt"),
            ]

    def clean_command(self):
        """
        Normalize command to always be 'alt' regardless of OS.
        """
        command = self.cleaned_data.get("command", "").lower()
        if command in ["option", "alt"]:
            return "alt"
        return command
