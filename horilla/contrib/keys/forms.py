"""
Forms for the keys app
"""

# Third-party imports (Django)
from django import forms

from horilla.contrib.core.models import Company
from horilla.contrib.generics.forms import HorillaModelForm
from horilla.contrib.utils.middlewares import _thread_local

# First party imports (Horilla)
from horilla.menu import (
    main_section_menu,
    my_settings_menu,
    settings_menu,
    sub_section_menu,
)
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .models import ShortcutKey
from .utils import normalize_page_url


class ShortcutKeyForm(HorillaModelForm):
    """
    Form for creating and updating keyboard shortcut keys for users.
    """

    class Meta:
        """
        Meta configuration for ShortcutKeyForm.
        """

        model = ShortcutKey
        fields = "__all__"
        keep_on_form = ("company",)

    def __init__(self, *args, **kwargs):
        """Initialize form and dynamically populate page and command choices."""
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        choices = []

        self.fields["user"].queryset = self.fields["user"].queryset.filter(
            id=request.user.id
        )
        user_company = getattr(request.user, "company", None)
        if user_company:
            self.fields["company"].queryset = Company.objects.filter(id=user_company.id)
        else:
            self.fields["company"].queryset = Company.objects.none()

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
        for _section, items in sub_sections.items():
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
            choices=[("", _("Select Page"))] + choices,
            label=_("Page"),
            required=True,
            widget=forms.Select(
                attrs={
                    "class": "js-example-basic-single headselect w-full text-sm",
                    "data-placeholder": _("Select Page"),
                    "id": "id_page",
                }
            ),
        )

        command_choices = self._get_command_choices()

        self.fields["command"] = forms.ChoiceField(
            choices=[("", _("Select Command Key"))] + command_choices,
            label=_("Command Key"),
            required=True,
            widget=forms.Select(
                attrs={
                    "class": "js-example-basic-single headselect w-full text-sm",
                    "data-placeholder": _("Select Command Key"),
                    "id": "id_command",
                }
            ),
        )

        if self.instance and self.instance.pk:
            self.fields["command"].initial = "alt"
            if self.instance.page:
                self.initial["page"] = normalize_page_url(self.instance.page)

    def clean_page(self):
        """Store page URLs in the same format as menu choices."""
        page = self.cleaned_data.get("page")
        return normalize_page_url(page) if page else page

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
