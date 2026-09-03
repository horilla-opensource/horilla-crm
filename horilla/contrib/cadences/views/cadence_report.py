"""
View for Cadence Report
"""

# Standard library imports
from functools import cached_property

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Concat

from horilla.contrib.activity.models import Activity
from horilla.contrib.generics.views import HorillaListView
from horilla.contrib.generics.views.core import HorillaTabView
from horilla.contrib.mail.models import HorillaMail
from horilla.db.models import CharField, Count, F, Q, Value
from horilla.shortcuts import get_object_or_404, redirect
from horilla.urls import reverse_lazy
from horilla.utils import timezone
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _

# First party imports (Horilla)
from horilla.views.generic import TemplateView

# Local imports
from ..models import Cadence, CadenceFollowUp


def get_cadence_activity_queryset(cadence, activity_type):
    """Return activities of the given type tied to the cadence's current followups."""
    if not cadence:
        return Activity.objects.none()

    current_followup_ids = list(cadence.followups.values_list("id", flat=True))
    if not current_followup_ids:
        return Activity.objects.none()

    return Activity.objects.filter(
        activity_type=activity_type,
        additional_info__cadence_runtime__cadence_id=cadence.pk,
        additional_info__cadence_runtime__followup_id__in=current_followup_ids,
    )


def get_cadence_task_queryset(cadence):
    """Return task activities tied to the cadence's current followups."""
    return get_cadence_activity_queryset(cadence, "task")


def get_cadence_call_queryset(cadence):
    """Return call activities tied to the cadence's current followups."""
    return get_cadence_activity_queryset(cadence, "log_call")


def get_cadence_email_queryset(cadence):
    """Return HorillaMail objects tied to the cadence's current followups."""
    if not cadence:
        return HorillaMail.objects.none()

    current_followup_ids = list(cadence.followups.values_list("id", flat=True))
    if not current_followup_ids:
        return HorillaMail.objects.none()

    return HorillaMail.objects.filter(
        additional_info__cadence_runtime__cadence_id=cadence.pk,
        additional_info__cadence_runtime__followup_id__in=current_followup_ids,
    )


class CadenceReportView(LoginRequiredMixin, TemplateView):
    """View for cadence report."""

    template_name = "cadence_report/cadence_report_view.html"

    def get(self, request, *args, **kwargs):
        """Validate cadence_pk when present; redirect with an error if the cadence is missing."""
        cadence_pk = request.GET.get("cadence_pk")
        if cadence_pk:
            try:
                get_object_or_404(Cadence, pk=cadence_pk)
            except Exception as e:
                messages.error(request, str(e))
                fallback = request.META.get(
                    "HTTP_REFERER",
                    reverse_lazy("cadences:cadence_view"),
                )
                return redirect(fallback)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add cadence context for report header and navigation."""
        context = super().get_context_data(**kwargs)
        cadence_pk = self.request.GET.get("cadence_pk")
        cadence = None
        back_url = reverse_lazy("cadences:cadence_view")

        if cadence_pk:
            cadence = Cadence.objects.filter(pk=cadence_pk).first()
            if cadence:
                back_url = reverse_lazy(
                    "cadences:cadence_detail_view", kwargs={"pk": cadence.pk}
                )

        context["cadence"] = cadence
        context["back_url"] = back_url
        return context


class CadenceReportTabView(LoginRequiredMixin, HorillaTabView):
    """Tab view for cadence report."""

    view_id = "cadence-report-tab-view"
    background_class = "bg-primary-100 rounded-md"

    @cached_property
    def tabs(self):
        """
        Get the list of tabs for the cadence report view.
        """
        tabs = []

        if self.request.user.has_perm("activity.view_activity"):
            # Activity Task Tab
            tabs.append(
                {
                    "title": _("Task"),
                    "url": reverse_lazy("cadences:cadence_task_tab_view"),
                    "target": "task-view-content",
                    "id": "cadence-task-tab-view",
                }
            )

            # Activity Call Tab
            tabs.append(
                {
                    "title": _("Call"),
                    "url": reverse_lazy("cadences:cadence_call_tab_view"),
                    "target": "call-view-content",
                    "id": "cadence-call-tab-view",
                }
            )

            # Activity Email Tab
            tabs.append(
                {
                    "title": _("Email"),
                    "url": reverse_lazy("cadences:cadence_email_tab_view"),
                    "target": "email-view-content",
                    "id": "cadence-email-tab-view",
                }
            )

        return tabs


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["activity.view_activity"]), name="dispatch"
)
class CadenceTaskTabView(LoginRequiredMixin, TemplateView):
    """Tab view for cadence tasks."""

    template_name = "cadence_report/cadence_task_tab.html"

    def get_context_data(self, **kwargs):
        """Provide current cadence context for task tab."""
        context = super().get_context_data(**kwargs)
        cadence_pk = self.request.GET.get("cadence_pk")
        cadence = Cadence.objects.filter(pk=cadence_pk).first() if cadence_pk else None
        context["cadence"] = cadence

        task_stats = {
            "triggered_count": 0,
            "completed_count": 0,
            "pending_count": 0,
            "unresolved_count": 0,
            "completed_pct": 0,
            "pending_pct": 0,
            "unresolved_pct": 0,
        }
        if cadence:
            task_activities = get_cadence_task_queryset(cadence)
            task_stats = task_activities.aggregate(
                triggered_count=Count("id"),
                completed_count=Count("id", filter=Q(status="completed")),
                pending_count=Count("id", filter=Q(status="not_started")),
                unresolved_count=Count(
                    "id", filter=Q(status__in=["cancelled", "deferred"])
                ),
            )

            total_triggered = task_stats.get("triggered_count") or 0
            completed = task_stats.get("completed_count") or 0
            pending = task_stats.get("pending_count") or 0
            unresolved = task_stats.get("unresolved_count") or 0

            if total_triggered:
                task_stats["completed_pct"] = (completed * 100) / total_triggered
                task_stats["pending_pct"] = (pending * 100) / total_triggered
                task_stats["unresolved_pct"] = (unresolved * 100) / total_triggered

        context["task_stats"] = task_stats
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["activity.view_activity"]), name="dispatch"
)
class CadenceTaskListView(LoginRequiredMixin, HorillaListView):
    """Follow-up analytics list for cadence task report tab."""

    model = CadenceFollowUp
    view_id = "cadence-task-followup-analytics-list-view"
    bulk_select_option = False
    bulk_update_option = False
    bulk_export_option = False
    save_to_list_option = False
    list_column_visibility = False
    actions = []
    columns = [
        (_("Follow-Up"), "followup_label"),
        "subject",
        (_("Completed"), "completed_count"),
        (_("Pending"), "pending_count"),
        (_("Unresolved"), "unresolved_count"),
    ]

    def dispatch(self, request, *args, **kwargs):
        """Set list URLs from the request path before dispatch."""
        self.main_url = request.path
        self.search_url = request.path
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        cadence_pk = self.request.GET.get("cadence_pk")
        cadence = Cadence.objects.filter(pk=cadence_pk).first() if cadence_pk else None
        if not cadence:
            return CadenceFollowUp.objects.none()
        triggered_followup_ids = list(
            get_cadence_task_queryset(cadence)
            .values_list("additional_info__cadence_runtime__followup_id", flat=True)
            .distinct()
        )
        if not triggered_followup_ids:
            return CadenceFollowUp.objects.none()
        return (
            cadence.followups.filter(
                followup_type="task",
                pk__in=triggered_followup_ids,
            )
            .annotate(
                followup_label=Concat(
                    Value("Follow-up "), F("followup_number"), output_field=CharField()
                )
            )
            .order_by("followup_number", "order", "id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = context.get("queryset", [])
        followup_ids = [row.pk for row in rows]
        stats_map = {}
        if followup_ids:
            followup_stats = (
                Activity.objects.filter(
                    activity_type="task",
                    additional_info__cadence_runtime__followup_id__in=followup_ids,
                )
                .values("additional_info__cadence_runtime__followup_id")
                .annotate(
                    completed_count=Count("id", filter=Q(status="completed")),
                    pending_count=Count("id", filter=Q(status="not_started")),
                    unresolved_count=Count(
                        "id", filter=Q(status__in=["cancelled", "deferred"])
                    ),
                )
            )
            stats_map = {
                row["additional_info__cadence_runtime__followup_id"]: row
                for row in followup_stats
            }
        for followup in rows:
            data = stats_map.get(followup.pk, {})
            followup.completed_count = data.get("completed_count", 0)
            followup.pending_count = data.get("pending_count", 0)
            followup.unresolved_count = data.get("unresolved_count", 0)
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["activity.view_activity"]), name="dispatch"
)
class CadenceCallTabView(LoginRequiredMixin, TemplateView):
    """Tab view for cadence calls."""

    template_name = "cadence_report/cadence_call_tab.html"

    def get_context_data(self, **kwargs):
        """Provide current cadence context for call tab."""
        context = super().get_context_data(**kwargs)
        cadence_pk = self.request.GET.get("cadence_pk")
        cadence = Cadence.objects.filter(pk=cadence_pk).first() if cadence_pk else None
        context["cadence"] = cadence

        call_stats = {
            "triggered_count": 0,
            "completed_count": 0,
            "scheduled_count": 0,
            "cancelled_count": 0,
            "completed_pct": 0,
        }
        if cadence:
            call_activities = get_cadence_call_queryset(cadence)
            call_stats = call_activities.aggregate(
                triggered_count=Count("id"),
                completed_count=Count("id", filter=Q(status="completed")),
                scheduled_count=Count("id", filter=Q(status="scheduled")),
                cancelled_count=Count("id", filter=Q(status="cancelled")),
            )

            total_triggered = call_stats.get("triggered_count") or 0
            completed = call_stats.get("completed_count") or 0

            if total_triggered:
                call_stats["completed_pct"] = (completed * 100) / total_triggered

        context["call_stats"] = call_stats
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["activity.view_activity"]), name="dispatch"
)
class CadenceCallListView(LoginRequiredMixin, HorillaListView):
    """Follow-up analytics list for cadence call report tab."""

    model = CadenceFollowUp
    view_id = "cadence-call-followup-analytics-list-view"
    bulk_select_option = False
    bulk_update_option = False
    bulk_export_option = False
    save_to_list_option = False
    list_column_visibility = False
    actions = []
    columns = [
        (_("Follow-Up"), "followup_label"),
        "purpose",
        (_("Completed"), "completed_count"),
        (_("Scheduled"), "scheduled_count"),
        (_("Overdue"), "overdue_count"),
        (_("Cancelled"), "cancelled_count"),
    ]

    def dispatch(self, request, *args, **kwargs):
        """Set list URLs from the request path before dispatch."""
        self.main_url = request.path
        self.search_url = request.path
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        cadence_pk = self.request.GET.get("cadence_pk")
        cadence = Cadence.objects.filter(pk=cadence_pk).first() if cadence_pk else None
        if not cadence:
            return CadenceFollowUp.objects.none()
        triggered_followup_ids = list(
            get_cadence_call_queryset(cadence)
            .values_list("additional_info__cadence_runtime__followup_id", flat=True)
            .distinct()
        )
        if not triggered_followup_ids:
            return CadenceFollowUp.objects.none()
        return (
            cadence.followups.filter(
                followup_type="call",
                pk__in=triggered_followup_ids,
            )
            .annotate(
                followup_label=Concat(
                    Value("Follow-up "), F("followup_number"), output_field=CharField()
                )
            )
            .order_by("followup_number", "order", "id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = context.get("queryset", [])
        followup_ids = [row.pk for row in rows]
        stats_map = {}
        if followup_ids:
            now = timezone.now()
            followup_stats = (
                Activity.objects.filter(
                    activity_type="log_call",
                    additional_info__cadence_runtime__followup_id__in=followup_ids,
                )
                .values("additional_info__cadence_runtime__followup_id")
                .annotate(
                    completed_count=Count("id", filter=Q(status="completed")),
                    scheduled_count=Count("id", filter=Q(status="scheduled")),
                    overdue_count=Count(
                        "id",
                        filter=Q(status="scheduled", start_datetime__lt=now),
                    ),
                    cancelled_count=Count("id", filter=Q(status="cancelled")),
                )
            )
            stats_map = {
                row["additional_info__cadence_runtime__followup_id"]: row
                for row in followup_stats
            }
        for followup in rows:
            data = stats_map.get(followup.pk, {})
            followup.completed_count = data.get("completed_count", 0)
            followup.scheduled_count = data.get("scheduled_count", 0)
            followup.overdue_count = data.get("overdue_count", 0)
            followup.cancelled_count = data.get("cancelled_count", 0)
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["activity.view_activity"]), name="dispatch"
)
class CadenceEmailTabView(LoginRequiredMixin, TemplateView):
    """Tab view for cadence emails."""

    template_name = "cadence_report/cadence_email_tab.html"

    def get_context_data(self, **kwargs):
        """Provide current cadence context for email tab."""
        context = super().get_context_data(**kwargs)
        cadence_pk = self.request.GET.get("cadence_pk")
        cadence = Cadence.objects.filter(pk=cadence_pk).first() if cadence_pk else None
        context["cadence"] = cadence

        email_stats = {
            "triggered_count": 0,
            "delivered_count": 0,
            "bounced_count": 0,
            "opened_count": 0,
            "failed_count": 0,
            "delivered_pct": 0,
            "bounced_pct": 0,
            "opened_pct": 0,
            "failed_pct": 0,
        }
        if cadence:
            email_mails = get_cadence_email_queryset(cadence)
            email_stats = email_mails.aggregate(
                triggered_count=Count("id"),
                delivered_count=Count(
                    "id",
                    filter=Q(mail_status="delivered"),
                ),
                bounced_count=Count("id", filter=Q(mail_status="bounced")),
                opened_count=Count("id", filter=Q(mail_status="opened")),
                failed_count=Count("id", filter=Q(mail_status="failed")),
            )

            total_triggered = email_stats.get("triggered_count") or 0
            delivered = email_stats.get("delivered_count") or 0
            bounced = email_stats.get("bounced_count") or 0
            opened = email_stats.get("opened_count") or 0
            failed = email_stats.get("failed_count") or 0

            if total_triggered:
                email_stats["delivered_pct"] = (delivered * 100) / total_triggered
                email_stats["bounced_pct"] = (bounced * 100) / total_triggered
                email_stats["opened_pct"] = (opened * 100) / total_triggered
                email_stats["failed_pct"] = (failed * 100) / total_triggered

        context["email_stats"] = email_stats
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["activity.view_activity"]), name="dispatch"
)
class CadenceEmailListView(LoginRequiredMixin, HorillaListView):
    """Follow-up analytics list for cadence email report tab."""

    model = CadenceFollowUp
    view_id = "cadence-email-followup-analytics-list-view"
    bulk_select_option = False
    bulk_update_option = False
    bulk_export_option = False
    save_to_list_option = False
    list_column_visibility = False
    actions = []
    columns = [
        (_("Follow-Up"), "followup_label"),
        (_("Email Template"), "email_template_name"),
        (_("Delivered"), "delivered_count"),
        (_("Bounced"), "bounced_count"),
        (_("Opened"), "opened_count"),
        (_("Failed"), "failed_count"),
    ]

    def dispatch(self, request, *args, **kwargs):
        """Set list URLs from the request path before dispatch."""
        self.main_url = request.path
        self.search_url = request.path
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        cadence_pk = self.request.GET.get("cadence_pk")
        cadence = Cadence.objects.filter(pk=cadence_pk).first() if cadence_pk else None
        if not cadence:
            return CadenceFollowUp.objects.none()
        triggered_followup_ids = list(
            get_cadence_email_queryset(cadence)
            .values_list("additional_info__cadence_runtime__followup_id", flat=True)
            .distinct()
        )
        if not triggered_followup_ids:
            return CadenceFollowUp.objects.none()
        return (
            cadence.followups.filter(
                followup_type="email",
                pk__in=triggered_followup_ids,
            )
            .annotate(
                followup_label=Concat(
                    Value("Follow-up "), F("followup_number"), output_field=CharField()
                )
            )
            .order_by("followup_number", "order", "id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = context.get("queryset", [])
        followup_ids = [row.pk for row in rows]
        stats_map = {}
        if followup_ids:
            followup_stats = (
                HorillaMail.objects.filter(
                    additional_info__cadence_runtime__followup_id__in=followup_ids,
                )
                .values("additional_info__cadence_runtime__followup_id")
                .annotate(
                    delivered_count=Count(
                        "id",
                        filter=Q(mail_status="delivered"),
                    ),
                    bounced_count=Count("id", filter=Q(mail_status="bounced")),
                    opened_count=Count("id", filter=Q(mail_status="opened")),
                    failed_count=Count("id", filter=Q(mail_status="failed")),
                )
            )
            stats_map = {
                row["additional_info__cadence_runtime__followup_id"]: row
                for row in followup_stats
            }
        for followup in rows:
            data = stats_map.get(followup.pk, {})
            followup.email_template_name = (
                str(followup.email_template) if followup.email_template else ""
            )
            followup.delivered_count = data.get("delivered_count", 0)
            followup.bounced_count = data.get("bounced_count", 0)
            followup.opened_count = data.get("opened_count", 0)
            followup.failed_count = data.get("failed_count", 0)
        return context
