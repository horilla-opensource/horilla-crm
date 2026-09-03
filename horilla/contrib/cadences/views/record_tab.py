"""Cadence tab view for generic platform record detail pages."""

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin

# First party imports (Horilla)
from horilla.apps import apps
from horilla.contrib.activity.models import Activity
from horilla.contrib.automations.methods import evaluate_condition
from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.core.utils import is_owner
from horilla.contrib.generics.views import HorillaListView
from horilla.contrib.mail.models import HorillaMail
from horilla.utils.decorators import htmx_required, method_decorator
from horilla.utils.translation import gettext_lazy as _
from horilla.web import Http404

# Local imports
from ..models import Cadence
from ..signals import ensure_initial_followups_for_instance


@method_decorator(htmx_required, name="dispatch")
class CadenceRecordTabView(LoginRequiredMixin, HorillaListView):
    """Cadence tab for platform record detail pages using Horilla generic list view."""

    model = Cadence
    view_id = "cadence-record-tab-list"
    filterset_class = None
    columns = [
        "name",
        (_("Start Date"), "created_at"),
        (_("Next Follow-up"), "next_followup_type"),
        (_("Next Follow-up Response"), "next_followup_response"),
    ]
    actions = []
    bulk_select_option = False
    bulk_update_option = False
    bulk_export_option = False
    save_to_list_option = False
    list_column_visibility = False
    no_record_section = True
    no_record_fit_height = False
    no_record_msg = _("No active cadences match this record right now.")
    enable_quick_filters = False
    app_label = None
    model_name = None

    def _get_model(self):
        model = apps.get_model(self.app_label, self.model_name)
        if not model:
            raise Http404(_("Invalid model for cadence tab."))
        return model

    def _check_view_permission(self, model, pk):
        user = self.request.user
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        view_perm = f"{app_label}.view_{model_name}"
        view_own_perm = f"{app_label}.view_own_{model_name}"
        return user.has_perm(view_perm) or (
            user.has_perm(view_own_perm) and is_owner(model, pk)
        )

    def dispatch(self, request, *args, **kwargs):
        """Resolve the record, check view permission, and set list URLs."""
        self.main_url = request.path
        self.search_url = request.path
        model = self._get_model()
        obj = model.objects.filter(pk=kwargs.get("pk")).first()
        if not obj:
            raise Http404(_("Object not found."))
        if not self._check_view_permission(model, obj.pk):
            raise Http404(_("You don't have permission to view this item."))
        self._record_obj = obj
        self._record_model = model
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _evaluate_cadence_conditions(cadence, instance):
        conditions = list(cadence.conditions.all().order_by("order", "id"))
        if not conditions:
            return True
        result = None
        for idx, condition in enumerate(conditions):
            current = evaluate_condition(condition, instance)
            if idx == 0 or condition.logical_operator == "and":
                result = current if result is None else (result and current)
            elif condition.logical_operator == "or":
                result = current if result is None else (result or current)
            else:
                result = current if result is None else (result and current)
        return bool(result)

    # Maps Activity.activity_type → human label matching CadenceFollowUp display values
    _ACTIVITY_TYPE_LABELS = {
        "task": _("Task"),
        "log_call": _("Call"),
        "email": _("Email"),
    }

    @staticmethod
    def _next_followup_response_for(followup):
        if not followup:
            return "—"
        if followup.followup_type == "task":
            return followup.get_task_status_display() if followup.task_status else "—"
        if followup.followup_type == "call":
            return (
                followup.call_status.replace("_", " ").title()
                if followup.call_status
                else "—"
            )
        return "—"

    @staticmethod
    def _get_latest_runtime_activity(cadence_pk, obj, content_type):
        """Return the most-advanced cadence runtime Activity for this record+cadence."""
        activities = list(
            Activity.all_objects.filter(
                content_type=content_type,
                object_id=obj.pk,
                additional_info__cadence_runtime__cadence_id=cadence_pk,
            ).only("activity_type", "status", "additional_info", "id")
        )
        if not activities:
            return None
        activities.sort(
            key=lambda a: (
                (a.additional_info or {})
                .get("cadence_runtime", {})
                .get("followup_number", 0),
                a.id,
            ),
            reverse=True,
        )
        return activities[0]

    @staticmethod
    def _get_latest_runtime_mail(cadence_pk, obj, content_type):
        """Return the most-advanced cadence runtime HorillaMail for this record+cadence."""
        mails = list(
            HorillaMail.objects.filter(
                content_type=content_type,
                object_id=obj.pk,
                additional_info__cadence_runtime__cadence_id=cadence_pk,
            ).only("mail_status", "additional_info", "id")
        )
        if not mails:
            return None
        mails.sort(
            key=lambda m: (
                (m.additional_info or {})
                .get("cadence_runtime", {})
                .get("followup_number", 0),
                m.id,
            ),
            reverse=True,
        )
        return mails[0]

    def get_queryset(self):
        obj = self._record_obj
        try:
            ensure_initial_followups_for_instance(obj)
        except Exception:
            pass
        content_type = HorillaContentType.objects.get_for_model(self._record_model)
        cadences = (
            Cadence.objects.filter(module=content_type, is_active=True)
            .prefetch_related("conditions", "followups")
            .order_by("-created_at")
        )
        applicable_ids = []
        cadence_extra = {}
        for cadence in cadences:
            if self._evaluate_cadence_conditions(cadence, obj):
                applicable_ids.append(cadence.pk)
            latest_activity = self._get_latest_runtime_activity(
                cadence.pk, obj, content_type
            )
            latest_mail = self._get_latest_runtime_mail(cadence.pk, obj, content_type)
            activity_fn = (
                (latest_activity.additional_info or {})
                .get("cadence_runtime", {})
                .get("followup_number", 0)
                if latest_activity
                else 0
            )
            mail_fn = (
                (latest_mail.additional_info or {})
                .get("cadence_runtime", {})
                .get("followup_number", 0)
                if latest_mail
                else 0
            )
            if latest_mail and mail_fn >= activity_fn:
                next_followup_type = _("Email")
                next_response = latest_mail.get_mail_status_display()
            elif latest_activity:
                next_followup_type = self._ACTIVITY_TYPE_LABELS.get(
                    latest_activity.activity_type, "—"
                )
                next_response = latest_activity.get_status_display()
            else:
                followups = list(
                    cadence.followups.all().order_by("followup_number", "order", "id")
                )
                first_followup = followups[0] if followups else None
                next_followup_type = (
                    first_followup.get_followup_type_display()
                    if first_followup
                    else "—"
                )
                next_response = self._next_followup_response_for(first_followup)
            cadence_extra[cadence.pk] = {
                "next_followup_response": next_response,
                "next_followup_type": next_followup_type,
            }
        self._cadence_extra = cadence_extra
        return Cadence.objects.filter(pk__in=applicable_ids).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra = getattr(self, "_cadence_extra", {})
        for cadence in context.get("queryset", []):
            row_extra = extra.get(cadence.pk, {})
            cadence.next_followup_response = row_extra.get(
                "next_followup_response", "—"
            )
            cadence.next_followup_type = row_extra.get("next_followup_type", "—")
        return context
