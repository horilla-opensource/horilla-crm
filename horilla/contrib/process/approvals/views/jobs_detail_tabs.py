"""
Jobs detail tab views for the approvals app.
"""

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.views import View

from horilla.contrib.activity.models import Activity

# First party imports (Horilla)
from horilla.contrib.generics.views import HorillaListView, HorillaTabView
from horilla.core.exceptions import ValidationError
from horilla.db.models import Case, CharField, Value, When
from horilla.shortcuts import get_object_or_404
from horilla.urls import reverse_lazy
from horilla.utils.decorators import htmx_required, method_decorator
from horilla.utils.translation import gettext_lazy as _
from horilla.views.generic import TemplateView

# First party imports (Horilla)
from horilla.web import ScriptResponse

# Local imports
from ..models import ApprovalDecision, ApprovalInstance
from ..utils import (
    get_cycle_started_at,
    get_rejected_policy,
    get_waiting_policy,
    is_user_pending_approver,
    safe_content_object,
)
from ..views.jobs_detail import ApprovalJobReviewView


@method_decorator(htmx_required, name="dispatch")
class ApprovalJobFieldUpdateView(LoginRequiredMixin, View):
    """Inline field update from approval detail page."""

    @staticmethod
    def _reload_response(pk):
        """Reload the job detail tab in place, showing any queued messages."""
        url = reverse_lazy("approvals:approval_job_review_view", kwargs={"pk": pk})
        return ScriptResponse(
            msgs=True,
            extra=f"htmx.ajax('GET', '{url}',{{target:'#mainContent',swap:'outerHTML'}});",
        )

    def post(self, request, pk):
        """Save an inline field edit on the approval job detail page."""
        job = get_object_or_404(
            ApprovalInstance.objects.select_related("current_step"),
            pk=pk,
            status__in=("pending", "rejected", "approved"),
        )
        if job.status == "pending":
            if not is_user_pending_approver(job, request.user):
                messages.error(
                    request, _("You are not the approver for this pending job.")
                )
                return self._reload_response(pk)
        elif job.status == "rejected":
            if not (
                request.user.is_superuser
                or (job.requested_by_id and job.requested_by_id == request.user.id)
            ):
                messages.error(
                    request,
                    _("Only the original requester can edit this rejected record."),
                )
                return self._reload_response(pk)
        elif job.status == "approved":
            if not (
                request.user.is_superuser
                or (job.requested_by_id and job.requested_by_id == request.user.id)
            ):
                messages.error(
                    request,
                    _("Only the original requester can edit this approved record."),
                )
                return self._reload_response(pk)
        else:
            messages.error(
                request, _("This record's approval status does not allow edits.")
            )
            return self._reload_response(pk)
        record = safe_content_object(job)
        if record is None:
            messages.error(request, _("Record not found."))
            return self._reload_response(pk)

        field_name = (request.POST.get("field_name") or "").strip()
        if not field_name:
            messages.error(request, _("Invalid field."))
            return self._reload_response(pk)

        if job.status == "pending":
            editable_fields = ApprovalJobReviewView._editable_fields_for_job(job)
            if editable_fields is not None and field_name not in editable_fields:
                messages.error(request, _("Field is not editable."))
                return self._reload_response(pk)
        elif job.status == "rejected":
            rejected_policy = get_rejected_policy(job)
            rejected_scope = rejected_policy.get("scope", "all_fields")
            rejected_fields = set(rejected_policy.get("fields", []) or [])
            if rejected_scope == "no_fields":
                messages.error(request, _("Field is not editable."))
                return self._reload_response(pk)
            if (
                rejected_scope == "specific_fields"
                and field_name not in rejected_fields
            ):
                messages.error(request, _("Field is not editable."))
                return self._reload_response(pk)

        try:
            field = record._meta.get_field(field_name)
        except Exception:
            messages.error(request, _("Unknown field."))
            return self._reload_response(pk)

        raw_value = request.POST.get("value")
        if getattr(field, "many_to_one", False):
            setattr(record, f"{field_name}_id", raw_value or None)
        elif getattr(field, "get_internal_type", lambda: "")() == "BooleanField":
            setattr(
                record,
                field_name,
                (raw_value or "").lower() in ("true", "1", "on", "yes"),
            )
        else:
            try:
                value = field.to_python(raw_value)
            except Exception:
                value = raw_value
            setattr(record, field_name, value)

        try:
            record.full_clean()
            record.save()
        except ValidationError:
            messages.error(request, _("Invalid value."))
            return self._reload_response(pk)
        except Exception:
            messages.error(request, _("Failed to update field."))
            return self._reload_response(pk)

        messages.success(request, _("Field updated successfully."))
        return self._reload_response(pk)


@method_decorator(htmx_required, name="dispatch")
class ApprovalJobDetailTabView(LoginRequiredMixin, HorillaTabView):
    """Tab container view for the approval job detail page."""

    view_id = "approval-job-detail-tab-view"

    def dispatch(self, request, *args, **kwargs):
        """Ensure the user is authenticated before rendering tabs."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return TemplateView.dispatch(self, request, *args, **kwargs)

    def setup(self, request, *args, **kwargs):
        """Configure approval job detail tabs."""
        super().setup(request, *args, **kwargs)
        self.tabs = [
            {
                "title": _("Details"),
                "url": reverse_lazy("approvals:approval_job_detail_details_tab_view"),
                "target": "tab-job-details-content",
                "id": "job-details",
            },
            {
                "title": _("Decision Timeline"),
                "url": reverse_lazy("approvals:approval_job_detail_timeline_tab_view"),
                "target": "tab-job-timeline-content",
                "id": "job-timeline",
            },
            {
                "title": _("Tasks"),
                "url": reverse_lazy("approvals:approval_job_detail_tasks_tab_view"),
                "target": "tab-job-tasks-content",
                "id": "job-tasks",
            },
        ]


class ApprovalJobDetailDetailsTabView(LoginRequiredMixin, TemplateView):
    """Renders the Details tab for an approval job."""

    template_name = "approval_tabs/job_details_tab.html"

    def get_context_data(self, **kwargs):
        """Build context with the approval job record and editable fields."""
        context = super().get_context_data(**kwargs)
        pk = self.request.GET.get("pk")
        job = get_object_or_404(ApprovalInstance, pk=pk)
        record = safe_content_object(job)
        policy = get_waiting_policy(job)
        editable_fields = ApprovalJobReviewView._editable_fields_for_job(job)
        body = ApprovalJobReviewView._detail_tab_body(record)
        field_permissions = {}
        editable_now = job.status == "pending"
        for _label, field_name in body:
            if not editable_now:
                field_permissions[field_name] = "readonly"
            elif editable_fields is None:
                field_permissions[field_name] = "readwrite"
            elif field_name in editable_fields:
                field_permissions[field_name] = "readwrite"
            else:
                field_permissions[field_name] = "readonly"
        context.update(
            {
                "job": job,
                "obj": record,
                "body": body,
                "field_permissions": field_permissions,
                "app_label": record._meta.app_label if record else "",
                "model_name": record._meta.model_name if record else "",
                "edit_field": True,
                "non_editable_fields": [],
                "can_update": editable_now,
                "pipeline_field": None,
                "editable_scope": policy.get("scope", "no_fields"),
                "editable_fields": policy.get("fields", []) or [],
            }
        )
        return context


@method_decorator(htmx_required, name="dispatch")
class ApprovalJobDetailTimelineTabView(LoginRequiredMixin, HorillaListView):
    """Renders the Decision Timeline tab for an approval job."""

    model = ApprovalDecision
    view_id = "approval-job-timeline-list"
    search_url = reverse_lazy("approvals:approval_job_detail_timeline_tab_view")
    main_url = reverse_lazy("approvals:approval_job_detail_timeline_tab_view")
    owner_filtration = False
    save_to_list_option = False
    list_column_visibility = False
    bulk_select_option = False
    bulk_export_option = False
    bulk_update_option = False
    bulk_delete_enabled = False
    filterset_class = None
    enable_sorting = False
    columns = [
        "step",
        (_("Cycle"), "cycle_label"),
        "get_decision_display",
        "decided_by",
        "comment",
        "decided_at",
    ]

    def get_queryset(self):
        pk = self.request.GET.get("pk")
        job = get_object_or_404(ApprovalInstance, pk=pk)
        user = self.request.user
        allowed = (
            user.is_superuser
            or is_user_pending_approver(job, user)
            or (job.requested_by_id and job.requested_by_id == user.id)
            or ApprovalDecision.objects.filter(instance=job, decided_by=user).exists()
        )
        if not allowed:
            return ApprovalDecision.objects.none()
        qs = (
            super()
            .get_queryset()
            .filter(instance=job)
            .select_related("step", "decided_by")
        )
        cycle_started_at = get_cycle_started_at(job)
        if cycle_started_at:
            qs = qs.annotate(
                cycle_label=Case(
                    When(
                        decided_at__gte=cycle_started_at,
                        then=Value(str(_("Current (After Resubmit)"))),
                    ),
                    default=Value(str(_("Previous"))),
                    output_field=CharField(),
                )
            )
        else:
            qs = qs.annotate(
                cycle_label=Value(str(_("Current")), output_field=CharField())
            )
        return qs.order_by("-decided_at", "-id")


class ApprovalJobDetailTasksTabView(LoginRequiredMixin, HorillaListView):
    """Renders the Tasks tab for an approval job."""

    model = Activity
    owner_filtration = False
    save_to_list_option = False
    list_column_visibility = False
    bulk_select_option = False
    bulk_export_option = False
    bulk_update_option = False
    bulk_delete_enabled = False
    filterset_class = None
    enable_sorting = False
    search_url = reverse_lazy("approvals:approval_job_detail_tasks_tab_view")
    main_url = reverse_lazy("approvals:approval_job_detail_tasks_tab_view")
    view_id = "approval-job-tasks-list"
    columns = [
        "subject",
        ("status", "get_status_update_html"),
        "get_task_priority_display",
        "due_datetime",
    ]
    col_attrs = [
        {
            "subject": {
                "hx-get": "{get_detail_url}?section=schedule",
                "hx-target": "#mainContent",
                "hx-select": "#mainContent",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "style": "cursor:pointer",
                "class": "hover:text-primary-600",
            }
        }
    ]

    def get_queryset(self):
        if not hasattr(self, "_tasks_cache"):
            pk = self.request.GET.get("pk")
            job = get_object_or_404(ApprovalInstance, pk=pk)
            tasks = list(ApprovalJobReviewView._related_tasks(job))

            class _ListQuerysetProxy(list):
                """Thin list proxy that satisfies HorillaListView's queryset API."""

                def count(self):
                    return len(self)

                def values_list(self, *fields, flat=False):
                    """Return a flat list or list of tuples from the proxy list."""
                    if flat and len(fields) == 1:
                        return [getattr(obj, fields[0]) for obj in self]
                    return [tuple(getattr(obj, f) for f in fields) for obj in self]

            self._tasks_cache = _ListQuerysetProxy(tasks)
        return self._tasks_cache
