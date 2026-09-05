"""Version and metadata for the calls app."""

from horilla.utils.translation import gettext_lazy as _

__version__ = "1.11.6"
__module_name__ = _("Calls Integration")
__release_date__ = ""
__description__ = _(
    "Telephony integration for click-to-call from CRM records, multi-provider "
    "support (Twilio, SignalWire(Beta), Telnyx(Beta), Sinch(Beta), Exotel(Beta), call logging, agent "
    "mapping, and company-level access control."
)
__icon__ = "assets/fontawesome/svgs/solid/phone.svg"

__1_11_6__ = _(
    "Derive call-log list column labels from model verbose_name instead of hardcoded "
    "translations."
)

__1_11_5__ = _(
    "Raise requests.HTTPError and ValueError instead of bare Exception in Exotel adapter "
    "error handling."
)

__1_11_4__ = _(
    "Apply runtime viewport fit on Calls integration settings and provider tabs."
)

__1_11_3__ = _("Fix TemplateSyntaxError crashing the calls user-settings page.")

__1_11_2__ = _(
    "Lock down the calls API to company members with granted access."
    "Seed default call reports for the report engine."
)

__1_11_1__ = _(
    "Adopted ScriptResponse and HxTriggerResponse for provider and call-log actions. "
    "Preserved exception context when Exotel and SignalWire return non-JSON responses."
)

__1_11_0__ = _(
    "Initial release: multi-provider telephony (Twilio, SignalWire(Beta), Telnyx(Beta), Sinch(Beta), "
    "Exotel(Beta), Mock) with adapter factory; company enable/disable and role/user access "
    "control; Click-to-Call modal with HTMX live status, cancel, and recording toggles; "
    "CallLog history with Activity Timeline integration; agent mapping; secure "
    "credential storage; Settings → Integrations and My Settings UIs; REST API and "
    "webhook/WebSocket consumers."
)
