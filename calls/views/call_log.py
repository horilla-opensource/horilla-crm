"""Views for call logs: list, detail, delete."""

# Standard library imports
import logging
from functools import cached_property

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views import View

from horilla.contrib.core.models import HorillaContentType

# First party imports (Horilla)
from horilla.contrib.generics.views import HorillaListView, HorillaNavView, HorillaView
from horilla.contrib.generics.views.delete import HorillaSingleDeleteView
from horilla.shortcuts import render
from horilla.urls import reverse, reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla.web import HttpResponse, HxTriggerResponse, JsonResponse, ScriptResponse

# Local imports
from ..adapters.factory import get_adapter
from ..filters import CallLogFilter
from ..models import AgentMapping, CallLog, CallProvider

logger = logging.getLogger(__name__)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("calls.view_calllog"), name="dispatch")
class CallLogNavView(LoginRequiredMixin, HorillaNavView):
    """
    Navigation bar for the Call Logs main page.
    Provides search, filter, and layout switcher.
    """

    search_url = reverse_lazy("calls:call_log_list")
    main_url = reverse_lazy("calls:call_log_view")
    filterset_class = CallLogFilter
    model_name = "CallLog"
    model_app_label = "calls"
    enable_actions = True


@method_decorator(permission_required_or_denied("calls.view_calllog"), name="dispatch")
class CallLogView(LoginRequiredMixin, HorillaView):
    """
    Main Call Logs page — renders the nav bar + list layout.
    This is the entry point users see when clicking Call Logs in the menu.
    """

    nav_url = reverse_lazy("calls:call_log_nav")
    list_url = reverse_lazy("calls:call_log_list")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("calls.view_calllog"), name="dispatch")
class CallLogListView(LoginRequiredMixin, HorillaListView):
    """HTMX list of call logs."""

    model = CallLog
    view_id = "call-log-list"
    filterset_class = CallLogFilter
    search_url = reverse_lazy("calls:call_log_list")
    main_url = reverse_lazy("calls:call_log_view")
    columns = [
        "direction",
        "from_number",
        "to_number",
        "status",
        "get_duration_display",
        "started_at",
        "provider",
    ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("calls.delete_calllog", modal=True),
    name="dispatch",
)
class CallLogDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Delete a call log."""

    model = CallLog

    def get_post_delete_response(self):
        """Return HTMX response to reload shortcut key list after deletion."""

        return HxTriggerResponse()


# ── Click-to-Call ──────────────────────────────────────────────────────────────


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("calls.add_calllog", modal=True), name="dispatch"
)
class ClickToCallView(LoginRequiredMixin, View):
    """
    Initiates an outbound call from any record detail page.

    GET  — renders the click-to-call modal with providers + phone number pre-filled.
    POST — calls adapter.initiate_call(), creates CallLog(status='initiated'),
           returns HTMX success fragment.
    """

    def get(self, request, *args, **kwargs):
        """Render the click-to-call modal with a list of active providers and pre-filled phone number if provided."""
        providers = CallProvider.objects.filter(status=CallProvider.STATUS_ACTIVE)
        return render(
            request,
            "calls/click_to_call_modal.html",
            {
                "providers": providers,
                "phone_number": request.GET.get("phone_number", ""),
                "related_model_name": request.GET.get("model_name", ""),
                "related_object_id": request.GET.get("object_id", ""),
            },
        )

    def post(self, request, *args, **kwargs):
        """Initiate the call via the selected provider's adapter, create a CallLog entry, and return an HTMX response indicating success or failure."""
        provider_id = request.POST.get("provider_id")
        from_number = request.POST.get("from_number", "")
        to_number = request.POST.get("to_number", "")
        related_model_name = request.POST.get("related_model_name", "")
        related_object_id = request.POST.get("related_object_id") or None

        if not to_number:
            return render(
                request,
                "calls/click_to_call_modal.html",
                {
                    "providers": CallProvider.objects.filter(
                        status=CallProvider.STATUS_ACTIVE
                    ),
                    "phone_number": "",
                    "related_model_name": related_model_name,
                    "related_object_id": related_object_id,
                    "error": str(_("Please enter a phone number to call.")),
                },
            )

        provider = CallProvider.objects.filter(pk=provider_id).first()
        if not provider:
            return JsonResponse({"error": str(_("Provider not found."))}, status=400)

        company = request.active_company
        related_object_id = self._validate_related_object(
            related_model_name, related_object_id, company
        )
        if related_object_id is None:
            related_model_name = ""

        agent_mapping, _created = AgentMapping.all_objects.get_or_create(
            provider=provider,
            user=request.user,
            defaults={"company": company, "created_by": request.user},
        )

        # For providers that bridge via the agent's phone (e.g. Exotel), use the
        # agent's configured Caller ID when the modal doesn't supply a from_number.
        if not from_number and agent_mapping and agent_mapping.agent_id:
            from_number = agent_mapping.agent_id
        # Final fallback: use the provider's admin-configured default caller ID.
        if not from_number and provider.caller_id:
            from_number = provider.caller_id

        callback_url = request.build_absolute_uri(
            reverse(
                "calls:provider_webhook",
                kwargs={
                    "provider_type": provider.provider_type,
                    "provider_pk": provider.pk,
                },
            )
        )
        twiml_url = (
            request.build_absolute_uri(
                reverse("calls:twilio_twiml", kwargs={"provider_pk": provider.pk})
            )
            if provider.provider_type in ("twilio", "signalwire")
            else ""
        )

        try:
            adapter = get_adapter(provider)
            result = adapter.initiate_call(
                from_number, to_number, callback_url, twiml_url=twiml_url
            )
        except Exception as exc:
            logger.error("Click-to-call failed for provider %s: %s", provider, exc)
            messages.error(request, str(exc))
            return HttpResponse()

        call_log = CallLog.objects.create(
            provider=provider,
            agent=agent_mapping,
            direction=CallLog.DIRECTION_OUTBOUND,
            status=result.get("status", CallLog.STATUS_INITIATED),
            from_number=from_number,
            to_number=to_number,
            started_at=timezone.now(),
            provider_call_id=result.get("call_id", ""),
            related_model_name=related_model_name,
            related_object_id=related_object_id,
            company=company,
            created_by=request.user,
        )

        return render(
            request,
            "calls/call_status_modal.html",
            {
                "call_log": call_log,
                "is_terminal": False,
                "status_label": _("Initiating…"),
            },
        )

    @staticmethod
    def _validate_related_object(model_name, object_id, company):
        """Return object_id only when the object exists and belongs to company.
        Works for any model — no hardcoded app names."""
        if not object_id or not model_name or not company:
            return object_id
        try:
            pk = int(object_id)
        except (TypeError, ValueError):
            return None
        try:
            model_class = HorillaContentType.objects.get(
                model=model_name.lower()
            ).model_class()
            manager = getattr(model_class, "all_objects", model_class.objects)
            qs = (
                manager.filter(pk=pk, company=company)
                if hasattr(model_class, "company")
                else manager.filter(pk=pk)
            )
            return pk if qs.exists() else None
        except Exception:
            pass
        return None


# ── Call Status Polling & Cancel ───────────────────────────────────────────────


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("calls.view_calllog"), name="dispatch")
class CallStatusView(LoginRequiredMixin, View):
    """
    Polled by the calling modal every 3 seconds via HTMX.
    Returns the updated modal fragment; stops polling once the call reaches
    a terminal status and auto-closes the modal.
    """

    TERMINAL = {
        CallLog.STATUS_COMPLETED,
        CallLog.STATUS_NO_ANSWER,
        CallLog.STATUS_FAILED,
        CallLog.STATUS_CANCELLED,
        CallLog.STATUS_BUSY,
    }

    MAX_CALL_AGE_MINUTES = 5
    MAX_RINGING_SECONDS = 30

    STATUS_LABELS = {
        CallLog.STATUS_INITIATED: _("Initiating…"),
        CallLog.STATUS_RINGING: _("Ringing…"),
        CallLog.STATUS_IN_PROGRESS: _("In Progress"),
        CallLog.STATUS_COMPLETED: _("Call Ended"),
        CallLog.STATUS_NO_ANSWER: _("No Answer"),
        CallLog.STATUS_BUSY: _("Call Declined"),
        CallLog.STATUS_FAILED: _("Call Failed"),
        CallLog.STATUS_CANCELLED: _("Call Cancelled"),
    }

    def get(self, request, pk, *args, **kwargs):
        """Refresh call status from timeouts or the provider and return the modal fragment."""
        call_log = CallLog.objects.filter(pk=pk, company=request.active_company).first()
        if not call_log:
            return ScriptResponse(close=True)

        # If non-terminal, try to get live status from the provider API (works
        # even when webhooks can't reach localhost in development).
        if call_log.status not in self.TERMINAL:
            if call_log.started_at:
                age = (timezone.now() - call_log.started_at).total_seconds()
                # Ringing with no answer after 30 s → busy (treat as declined/unreachable)
                ringing_states = {CallLog.STATUS_RINGING, CallLog.STATUS_INITIATED}
                if (
                    call_log.status in ringing_states
                    and age >= self.MAX_RINGING_SECONDS
                ):
                    call_log.status = CallLog.STATUS_BUSY
                    call_log.ended_at = call_log.ended_at or timezone.now()
                    call_log.save(update_fields=["status", "ended_at"])
                # Hard cap: any non-terminal call older than 5 min → no_answer
                elif age >= self.MAX_CALL_AGE_MINUTES * 60:
                    call_log.status = CallLog.STATUS_NO_ANSWER
                    call_log.ended_at = call_log.ended_at or timezone.now()
                    call_log.save(update_fields=["status", "ended_at"])

            if call_log.status not in self.TERMINAL and call_log.provider_call_id:
                try:
                    live_status = get_adapter(call_log.provider).fetch_status(
                        call_log.provider_call_id
                    )
                    if live_status and live_status != call_log.status:
                        call_log.status = live_status
                        update_fields = ["status"]
                        if live_status in self.TERMINAL and not call_log.ended_at:
                            call_log.ended_at = timezone.now()
                            update_fields.append("ended_at")
                        call_log.save(update_fields=update_fields)
                except Exception as exc:
                    logger.warning(
                        "Live status fetch failed for CallLog %s: %s", pk, exc
                    )

        return render(
            request,
            "calls/call_status_modal.html",
            {
                "call_log": call_log,
                "is_terminal": call_log.status in self.TERMINAL,
                "status_label": self.STATUS_LABELS.get(
                    call_log.status, call_log.status
                ),
            },
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("calls.add_calllog", modal=True), name="dispatch"
)
class CancelCallView(LoginRequiredMixin, View):
    """Cancel an active call via the provider adapter and update the CallLog."""

    def post(self, request, pk, *args, **kwargs):
        """Cancel the active call via the provider and mark the CallLog as cancelled."""
        call_log = CallLog.objects.filter(pk=pk, company=request.active_company).first()
        if not call_log:
            return ScriptResponse(close=True)
        try:
            adapter = get_adapter(call_log.provider)
            in_progress = call_log.status == CallLog.STATUS_IN_PROGRESS
            adapter.cancel_call(call_log.provider_call_id, in_progress=in_progress)
        except Exception as exc:
            logger.error("Cancel call failed for CallLog %s: %s", pk, exc)
        call_log.status = CallLog.STATUS_CANCELLED
        call_log.save(update_fields=["status"])
        return render(
            request,
            "calls/call_status_modal.html",
            {
                "call_log": call_log,
                "is_terminal": True,
                "status_label": _("Call Cancelled"),
            },
        )


# ── Object Call Log (activity tab) ─────────────────────────────────────────────


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("calls.view_calllog"), name="dispatch")
class ObjectCallLogView(LoginRequiredMixin, HorillaListView):
    """
    HorillaListView listing real CallLog records for a any record.
    Used in the Call History sub-tab of the activity tab via HTMX.
    """

    model = CallLog
    view_id = "object-call-log-list"
    bulk_select_option = False
    list_column_visibility = False
    columns = [
        "direction",
        "provider",
        "status",
        ("duration_seconds", "get_duration_display"),
        "agent",
        "started_at",
    ]

    @cached_property
    def col_attrs(self):
        """Make the Direction cell clickable to open the call log detail view."""
        return [
            {
                "direction": {
                    "hx-get": "{get_detail_url}",
                    "hx-target": "#mainContent",
                    "hx-swap": "outerHTML",
                    "hx-push-url": "true",
                    "hx-select": "#mainContent",
                    "permission": "calls.view_calllog",
                }
            }
        ]

    @property
    def search_url(self):
        """Construct the search URL for this object's call log list based on the model_name and object_id query parameters."""
        model_name = self.request.GET.get("model_name", "")
        object_id = self.request.GET.get("object_id", "")
        return f"{reverse_lazy('calls:object_call_logs')}?model_name={model_name}&object_id={object_id}"

    @property
    def main_url(self):
        """Return the main URL for the activity tabbed view."""
        return self.search_url

    def get_queryset(self):
        model_name = self.request.GET.get("model_name", "")
        object_id = self.request.GET.get("object_id", "")
        return (
            CallLog.all_objects.filter(
                related_model_name__iexact=model_name,
                related_object_id=str(object_id),
            )
            .select_related("provider", "agent__user")
            .order_by("-started_at")
        )
