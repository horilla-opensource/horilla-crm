"""
Mail configuration modal detail view (incoming and outgoing).
"""

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin

from horilla.contrib.generics.views import HorillaModalDetailView

# First party imports (Horilla)
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _

# Local imports
from ..models import HorillaMailConfiguration


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class MailConfigDetailView(LoginRequiredMixin, HorillaModalDetailView):
    """
    Modal detail view for a single mail configuration (incoming or outgoing).
    """

    model = HorillaMailConfiguration
    title = _("Mail Configuration")
    header = {
        "title": "username",
        "subtitle": "host",
        "avatar": "",
    }
    body = []

    # Fields always shown for every config
    _COMMON_FIELDS = [
        "mail_channel",
        "type",
        "host",
        "port",
        "is_primary",
    ]

    # Outgoing SMTP-only fields
    _OUTGOING_FIELDS = [
        "from_email",
        "display_name",
        "use_tls",
        "use_ssl",
        "fail_silently",
        "use_dynamic_display_name",
        "timeout",
    ]

    # Outlook OAuth-only fields
    _OUTLOOK_FIELDS = [
        "outlook_client_id",
        "outlook_tenant_id",
        "outlook_redirect_uri",
        "outlook_authorization_url",
        "outlook_token_url",
        "outlook_api_endpoint",
        "last_refreshed",
    ]

    def get_body_fields(self):
        """Return fields filtered by the instance's type and mail_channel."""
        fields = list(self._COMMON_FIELDS)
        if self.instance:
            if (
                self.instance.mail_channel == "outgoing"
                and self.instance.type == "mail"
            ):
                fields += self._OUTGOING_FIELDS
            if self.instance.type == "outlook":
                fields += self._OUTLOOK_FIELDS
        self.body = fields
        return super().get_body_fields()

    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit_white.svg",
            "img_class": "w-3 h-3 flex gap-4 filter brightness-0 invert",
            "permission": "mail.change_horillamailconfiguration",
            "attrs": """
                class="w-24 justify-center px-4 py-2 bg-primary-600 text-white rounded-md text-xs flex items-center gap-2 hover:bg-primary-800 transition duration-300 disabled:cursor-not-allowed cursor-pointer"
                hx-get="{get_edit_url}"
                hx-target="#modalBox"
                hx-swap="innerHTML"
                onclick="openModal();"
            """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "svg-themed w-3 h-3",
            "permission": "mail.delete_horillamailconfiguration",
            "attrs": """
                class="w-24 justify-center px-4 py-2 bg-[white] rounded-md text-xs flex items-center gap-2 border border-primary-500 hover:border-primary-600 transition duration-300 disabled:cursor-not-allowed text-primary-600 cursor-pointer"
                hx-get="{get_delete_url}"
                hx-target="#deleteModeBox"
                hx-vals='{{"check_dependencies": "true"}}'
                hx-trigger="click"
                onclick="openDeleteModeModal()"
            """,
        },
    ]
