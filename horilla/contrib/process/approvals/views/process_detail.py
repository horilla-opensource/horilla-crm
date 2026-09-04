"""
Process detail views for the approvals app.
"""

# Standard library imports
import json
from functools import cached_property

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.views import View

# First party imports (Horilla)
from horilla.apps import apps

# First party imports (Horilla)
from horilla.contrib.generics.views import HorillaNavView, HorillaSingleDeleteView
from horilla.shortcuts import render
from horilla.urls import reverse, reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla.views.generic import DetailView
from horilla.web import HttpNotFound, RefreshResponse, ScriptResponse

# Local imports
from ..filters import ApprovalRuleFilter
from ..models import ApprovalProcessRule, ApprovalRule


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["approvals.change_approvalrule"]),
    name="dispatch",
)
class ApprovalProcessRuleRecordFieldsFragmentView(LoginRequiredMixin, View):
    """HTMX fragment for record-modification specific fields picker."""

    @staticmethod
    def _record_field_choices(process_pk):
        process = (
            ApprovalRule.objects.filter(pk=process_pk).select_related("model").first()
        )
        if not (process and process.model_id):
            return []
        try:
            model_cls = process.model.model_class()
        except Exception:
            model_cls = None
        if model_cls is None:
            try:
                model_cls = apps.get_model(process.model.app_label, process.model.model)
            except Exception:
                model_cls = None
        if model_cls is None:
            return []

        fields = []
        seen = set()
        for f in model_cls._meta.get_fields():
            if not getattr(f, "concrete", False):
                continue
            if getattr(f, "many_to_many", False) or getattr(f, "one_to_many", False):
                continue
            if getattr(f, "auto_created", False) or getattr(f, "primary_key", False):
                continue
            if hasattr(f, "editable") and not f.editable:
                continue
            seen.add(f.name)
            fields.append(
                {
                    "name": f.name,
                    "label": str(
                        getattr(f, "verbose_name", None)
                        or f.name.replace("_", " ").title()
                    ),
                }
            )
        return fields

    def get(self, request):
        """Render the record modification policy fragment for a given process and side."""
        process_pk = request.GET.get("process_pk")
        side = request.GET.get("side", "waiting")
        if side not in ("waiting", "rejected"):
            side = "waiting"
        stage_key = (request.GET.get("stage_key") or "").strip()
        if stage_key:
            scope = request.GET.get(f"record_{side}_scope_{stage_key}", "")
            selected = request.GET.getlist(f"record_{side}_fields_{stage_key}")
        else:
            scope = request.GET.get(f"record_{side}_scope", "")
            selected = request.GET.getlist(f"record_{side}_fields")
        field_choices = self._record_field_choices(process_pk)
        return render(
            request,
            "record_fields_fragment.html",
            {
                "side": side,
                "stage_key": stage_key,
                "scope": scope,
                "selected_values": set(selected),
                "record_field_choices": field_choices,
            },
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["approvals.change_approvalrule"]),
    name="dispatch",
)
class ApprovalProcessRuleActionValueWidgetView(LoginRequiredMixin, View):
    """Return value widget for selected model field in update-field popup."""

    @staticmethod
    def _resolve_model(process_pk=None, model_name=None):
        if process_pk:
            process = (
                ApprovalRule.objects.filter(pk=process_pk)
                .select_related("model")
                .first()
            )
            if process and process.model_id:
                try:
                    model_cls = process.model.model_class()
                except Exception:
                    model_cls = None
                if model_cls is None:
                    try:
                        model_cls = apps.get_model(
                            process.model.app_label, process.model.model
                        )
                    except Exception:
                        model_cls = None
                if model_cls:
                    return model_cls
        if model_name:
            for app_config in apps.get_app_configs():
                try:
                    return apps.get_model(
                        app_label=app_config.label, model_name=model_name.lower()
                    )
                except Exception:
                    continue
        return None

    def get(self, request):
        """Return the widget metadata for a single model field as JSON."""
        process_pk = request.GET.get("process_pk")
        model_name = request.GET.get("model_name")
        field_name = request.GET.get("field_name", "")
        model_cls = self._resolve_model(process_pk=process_pk, model_name=model_name)
        widget = {"kind": "text", "input_type": "text", "choices": []}
        if model_cls and field_name:
            try:
                f = model_cls._meta.get_field(field_name)
                if getattr(f, "choices", None):
                    widget = {
                        "kind": "select",
                        "input_type": "select",
                        "choices": [
                            {"value": str(c[0]), "label": str(c[1])}
                            for c in (f.choices or [])
                        ],
                    }
                elif getattr(f, "many_to_one", False) and getattr(
                    f, "related_model", None
                ):
                    rel_qs = f.related_model.objects.all()[:200]
                    widget = {
                        "kind": "select",
                        "input_type": "fk",
                        "choices": [
                            {"value": str(obj.pk), "label": str(obj)} for obj in rel_qs
                        ],
                    }
                elif f.get_internal_type() in ("BooleanField",):
                    widget = {
                        "kind": "select",
                        "input_type": "boolean",
                        "choices": [
                            {"value": "true", "label": "True"},
                            {"value": "false", "label": "False"},
                        ],
                    }
                elif f.get_internal_type() in ("DateField",):
                    widget = {"kind": "input", "input_type": "date", "choices": []}
                elif f.get_internal_type() in ("DateTimeField",):
                    widget = {
                        "kind": "input",
                        "input_type": "datetime-local",
                        "choices": [],
                    }
                elif f.get_internal_type() in (
                    "IntegerField",
                    "BigIntegerField",
                    "PositiveIntegerField",
                    "SmallIntegerField",
                ):
                    widget = {"kind": "input", "input_type": "number", "choices": []}
            except Exception:
                pass
        return render(
            request,
            "action_value_widget_fragment.html",
            {"widget": widget},
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        "approvals.delete_approvalrule",
        modal=True,
    ),
    name="dispatch",
)
class ApprovalProcessDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Delete approval process."""

    model = ApprovalRule

    def get_post_delete_response(self):
        return ScriptResponse(reload=True)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["approvals.view_approvalrule"]),
    name="dispatch",
)
class ApprovalProcessDetailNavbar(LoginRequiredMixin, HorillaNavView):
    """Navbar for approval process detail (back to list, title, reload, Add rule, Edit process)."""

    search_url = reverse_lazy("approvals:approval_process_list_view")
    main_url = reverse_lazy("approvals:approval_process_view")
    filterset_class = ApprovalRuleFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    model_name = "ApprovalRule"
    model_app_label = "approvals"
    nav_width = False
    url_name = "approval_process_list_view"
    search_option = False
    border_enabled = False
    navbar_indication = True
    reload_option = False
    navbar_indication_attrs = {
        "hx-get": reverse_lazy("approvals:approval_process_view"),
        "hx-target": "#approval-process-view",
        "hx-swap": "outerHTML",
        "hx-push-url": "true",
        "hx-select": "#approval-process-view",
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_id = self.request.GET.get("obj")
        if obj_id:
            obj_id_clean = str(obj_id).split("?")[0].strip()
            try:
                obj_id_int = int(obj_id_clean)
                obj = ApprovalRule.objects.filter(pk=obj_id_int).first()
                if obj:
                    self.nav_title = obj.name
                    context["nav_title"] = self.nav_title
            except ValueError:
                pass
        return context

    @cached_property
    def new_button(self):
        """Primary: add rule (opens modal)."""
        if not self.request.user.has_perm("approvals.change_approvalrule"):
            return None
        obj = self.request.GET.get("obj")
        if not obj:
            return None
        try:
            obj_id = int(str(obj).split("?")[0].strip())
        except (TypeError, ValueError):
            return None
        return {
            "url": reverse(
                "approvals:approval_process_rule_create_view",
                kwargs={"process_pk": obj_id},
            ),
            "title": _("Add Rule"),
            "attrs": {"id": "approval-rule-add"},
        }

    @cached_property
    def second_button(self):
        """Secondary: edit process (opens modal)."""
        if not self.request.user.has_perm("approvals.change_approvalrule"):
            return None
        obj = self.request.GET.get("obj")
        if not obj:
            return None
        try:
            obj_id = int(str(obj).split("?")[0].strip())
        except (TypeError, ValueError):
            return None
        return {
            "url": reverse(
                "approvals:approval_process_update_view",
                kwargs={"pk": obj_id},
            ),
            "title": _("Edit Process"),
            "attrs": {"id": "approval-process-edit"},
        }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        "approvals.change_approvalrule",
        modal=True,
    ),
    name="dispatch",
)
class ApprovalProcessRuleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Delete a process rule from the detail view."""

    model = ApprovalProcessRule

    def get_post_delete_response(self):
        return ScriptResponse(reload=True)


@method_decorator(
    permission_required_or_denied(["approvals.view_approvalrule"]),
    name="dispatch",
)
class ApprovalProcessDetailView(LoginRequiredMixin, DetailView):
    """Full-page detail view for an approval process (rules accordion)."""

    model = ApprovalRule
    template_name = "approval_process_detail.html"
    context_object_name = "approval_rule"

    @staticmethod
    def _normalize_rule_config(config):
        """Normalize stringified JSON fragments for display templates."""
        if not isinstance(config, dict):
            return config
        normalized = dict(config)
        for key in ("record_modification", "process_admins"):
            value = normalized.get(key)
            if isinstance(value, dict):
                continue
            if isinstance(value, str):
                value = value.strip()
                while (
                    isinstance(value, str)
                    and value.startswith("{")
                    and value.endswith("}")
                ):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, dict):
                            normalized[key] = parsed
                            break
                        if isinstance(parsed, str):
                            value = parsed.strip()
                            continue
                        break
                    except Exception:
                        break
        return normalized

    @staticmethod
    def _resolve_field_verbose_name(field_name, model_cls):
        """Return the verbose name for a model field."""
        if not model_cls or not field_name:
            return field_name
        try:
            field = model_cls._meta.get_field(field_name)
            return str(
                getattr(field, "verbose_name", None)
                or field_name.replace("_", " ").title()
            )
        except Exception:
            return field_name

    @staticmethod
    def _resolve_condition_value(condition, model_cls):
        """Return a human-readable display string for condition.value."""
        if not model_cls or not condition.field or not condition.value:
            return condition.value
        try:
            field = model_cls._meta.get_field(condition.field)
        except Exception:
            return condition.value

        if getattr(field, "is_relation", False) and getattr(
            field, "related_model", None
        ):
            try:
                obj = field.related_model.objects.get(pk=condition.value)
                return str(obj)
            except Exception:
                pass
            return condition.value

        choices = getattr(field, "choices", None)
        if choices:
            for key, label in choices:
                if str(key) == str(condition.value):
                    return str(label)
            return condition.value

        return condition.value

    def get_queryset(self):
        """Return approval rules with related process rules and steps."""
        return ApprovalRule.objects.select_related("model").prefetch_related(
            "process_rules__conditions",
            "process_rules__steps__approver_user",
        )

    def get_context_data(self, **kwargs):
        """Build context with the process detail and its normalized rules."""
        context = super().get_context_data(**kwargs)
        process = self.object
        context["current_obj"] = process
        context["nav_url"] = reverse_lazy(
            "approvals:approval_process_detail_navbar_view"
        )

        model_cls = None
        try:
            model_cls = process.model.model_class()
        except Exception:
            pass
        if model_cls is None:
            try:
                model_cls = apps.get_model(process.model.app_label, process.model.model)
            except Exception:
                pass

        rules = list(process.process_rules.order_by("order", "id"))
        for rule in rules:
            rule.rule_config = self._normalize_rule_config(rule.rule_config or {})
            enriched = []
            for condition in rule.conditions.all():
                condition.value_display = self._resolve_condition_value(
                    condition, model_cls
                )
                condition.field_verbose_name = self._resolve_field_verbose_name(
                    condition.field, model_cls
                )
                enriched.append(condition)
            rule.enriched_conditions = enriched
        context["process_rules"] = rules
        return context

    def dispatch(self, request, *args, **kwargs):
        """Authenticate and resolve the process object before dispatch."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        try:
            self.object = self.get_object()
        except Exception as exc:
            if request.headers.get("HX-Request") == "true":
                messages.error(self.request, exc)
                return RefreshResponse(request)
            raise HttpNotFound(exc) from exc
        return super().dispatch(request, *args, **kwargs)
