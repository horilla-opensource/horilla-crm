"""
Forms for the horilla_keys app
"""

from django import forms

from horilla.menu import (
    main_section_menu,
    my_settings_menu,
    settings_menu,
    sub_section_menu,
)
from horilla_core.models import Company
from horilla_generics.forms import HorillaModelForm
from horilla_keys.models import ShortcutKey
from horilla_utils.middlewares import _thread_local


class ShortcutKeyForm(HorillaModelForm):
    """
    Form for creating and updating keyboard shortcut keys for users.
    """

    class Meta:
        """
        Meta configuration for ShortcutKeyForm.
        """

        model = ShortcutKey
        fields = ["user", "page", "command", "key", "company"]

    def __init__(self, *args, **kwargs):
        """Initialize form and dynamically populate page and command choices."""
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        choices = []
        company = getattr(request, "active_company", None)

        self.fields["user"].queryset = self.fields["user"].queryset.filter(
            id=request.user.id
        )
        self.fields["company"].queryset = Company.objects.filter(id=company.id)

        main_sections = main_section_menu.get_main_section_menu(request)
        for item in main_sections:
            name = item.get("name")
            url = item.get("url")

            if not url:
                if item.get("section") == "home":
                    url = "/"
            if name and url:
                choices.append((url, name))

        sub_sections = sub_section_menu.get_sub_section_menu(request)
        for _, items in sub_sections.items():
            for item in items:
                app_label = item.get("app_label")
                label = item.get("label")
                url = item.get("url")
                if app_label and url:
                    choices.append((url, label))

        my_settings = my_settings_menu.get_my_settings_menu(request)
        for item in my_settings:
            title = item.get("title")
            url = item.get("url")
            if title and url:
                choices.append((url, title))

        main_settings = settings_menu.get_settings_menu(request)
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
        Return OS-specific command key choices.
        """
        request = getattr(_thread_local, "request", None)
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower() if request else ""

        is_mac = "mac" in user_agent or "darwin" in user_agent

        if is_mac:
            return [("alt", "Option (⌥)")]

        return [("alt", "Alt")]

    def clean_command(self):
        """
        Normalize command to always be 'alt' regardless of OS.
        """
        command = self.cleaned_data.get("command", "").lower()
        if command in ["option", "alt"]:
            return "alt"
        return command

    def clean(self):
        cleaned = super().clean()

        for field in ["user", "company"]:
            if field in self.errors:
                self.add_error(None, self.errors[field])
                del self.errors[field]
        return cleaned
