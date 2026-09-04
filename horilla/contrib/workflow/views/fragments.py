"""
views for workflow rule fragments (conditions, actions, time triggers)
"""

# Standard library imports
import logging

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views import View

# First party imports (Horilla)
from horilla.apps import apps
from horilla.auth.models import User
from horilla.contrib.mail.models import HorillaMailTemplate
from horilla.contrib.notifications.models import NotificationTemplate
from horilla.shortcuts import render
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla.web import HttpResponse, ScriptResponse

from ..forms import (
    WorkflowActionForm,
    WorkflowConditionForm,
    WorkflowTimeTriggerActionForm,
)

# Local imports
from ..models import (
    WorkflowAction,
    WorkflowCondition,
    WorkflowRule,
    WorkflowTimeTriggerAction,
)

logger = logging.getLogger(__name__)


def _get_model_fields(rule):
    """Return list of (name, label) tuples for editable fields on the rule's model."""
    if not rule or not rule.model_id:
        return []
    model_cls = None
    try:
        model_cls = rule.model.model_class()
    except Exception:
        pass
    if model_cls is None:
        try:
            model_cls = apps.get_model(rule.model.app_label, rule.model.model)
        except Exception:
            pass
    if model_cls is None:
        return []
    skip = {
        "id",
        "pk",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "company",
        "additional_info",
    }
    fields = []
    for f in list(model_cls._meta.fields) + list(model_cls._meta.many_to_many):
        if f.name in skip or not getattr(f, "editable", True):
            continue
        label = str(
            getattr(f, "verbose_name", None) or f.name.replace("_", " ").title()
        )
        fields.append((f.name, label))
    return fields


def _build_field_meta(rule):
    """Return list of field metadata dicts for the action config popup."""
    if not rule or not rule.model_id:
        return [], [], []
    model_cls = None
    try:
        model_cls = rule.model.model_class()
    except Exception:
        pass
    if model_cls is None:
        try:
            model_cls = apps.get_model(rule.model.app_label, rule.model.model)
        except Exception:
            pass

    field_meta = []
    email_to_choices = [("self", "Self (User who triggered)")]
    notification_to_choices = [("self", "Self (User who triggered)")]

    if model_cls is None:
        return field_meta, email_to_choices, notification_to_choices

    skip = {
        "id",
        "pk",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "company",
        "additional_info",
    }
    for f in model_cls._meta.get_fields():
        if not getattr(f, "concrete", False) or getattr(f, "many_to_many", False):
            continue
        if not getattr(f, "editable", True) or f.name in skip:
            continue
        if getattr(f, "is_relation", False) and not getattr(f, "many_to_one", False):
            continue
        dtype = "text"
        itype = f.get_internal_type()
        if getattr(f, "choices", None):
            dtype = "choice"
        elif itype == "BooleanField":
            dtype = "boolean"
        elif itype == "DateField":
            dtype = "date"
        elif itype == "DateTimeField":
            dtype = "datetime-local"
        elif itype in (
            "IntegerField",
            "BigIntegerField",
            "PositiveIntegerField",
            "SmallIntegerField",
        ):
            dtype = "number"
        choices = [
            {"value": str(c[0]), "label": str(c[1])}
            for c in (getattr(f, "choices", None) or [])
        ]
        field_meta.append(
            {
                "name": f.name,
                "label": str(
                    getattr(f, "verbose_name", None) or f.name.replace("_", " ").title()
                ),
                "type": dtype,
                "choices": choices,
            }
        )

    for f in model_cls._meta.get_fields():
        if not hasattr(f, "name"):
            continue
        try:
            if f.get_internal_type() == "EmailField":
                label = str(
                    getattr(f, "verbose_name", None) or f.name.replace("_", " ").title()
                )
                email_to_choices.append((f"instance.{f.name}", label))
                notification_to_choices.append((f"instance.{f.name}", label))
        except Exception:
            pass
        if (
            getattr(f, "many_to_one", False)
            and getattr(f, "related_model", None) == User
        ):
            fk_label = str(
                getattr(f, "verbose_name", None) or f.name.replace("_", " ").title()
            )
            email_to_choices.append((f"instance.{f.name}.email", f"{fk_label} Email"))
            notification_to_choices.append((f"instance.{f.name}", fk_label))

    return field_meta, email_to_choices, notification_to_choices


def _get_date_field_choices(rule):
    """Return (field_name, verbose_label) pairs for DateField/DateTimeField on the rule's model."""
    if not rule or not rule.model_id:
        return []
    model_cls = None
    try:
        model_cls = rule.model.model_class()
    except Exception:
        pass
    if model_cls is None:
        try:
            model_cls = apps.get_model(rule.model.app_label, rule.model.model)
        except Exception:
            pass
    if model_cls is None:
        return []
    choices = []
    for f in model_cls._meta.get_fields():
        if not getattr(f, "concrete", False):
            continue
        itype = f.get_internal_type() if hasattr(f, "get_internal_type") else ""
        if itype in ("DateField", "DateTimeField"):
            label = str(
                getattr(f, "verbose_name", None) or f.name.replace("_", " ").title()
            )
            choices.append((f.name, label))
    return choices


def _build_tt_context(rule, instance=None, current_values=None):
    """Build shared context dict for the time-trigger form template."""

    field_meta, email_to_choices, notification_to_choices = _build_field_meta(rule)
    rule_ct = rule.model if rule and rule.model_id else None

    mail_templates = HorillaMailTemplate.objects.filter(
        Q(content_type__isnull=True) | Q(content_type=rule_ct)
    )
    notification_templates = NotificationTemplate.objects.filter(
        Q(content_type__isnull=True) | Q(content_type=rule_ct)
    )
    users = User.objects.filter(is_active=True)
    return {
        "rule": rule,
        "field_meta": field_meta,
        "mail_templates": mail_templates.distinct(),
        "notification_templates": notification_templates.distinct(),
        "users": users,
        "email_to_choices": email_to_choices,
        "notification_to_choices": notification_to_choices,
        "current_values": current_values or {},
    }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("workflow.change_workflowrule"),
    name="dispatch",
)
class WorkflowConditionSaveView(LoginRequiredMixin, View):
    """HTMX view: GET returns condition form modal; POST saves the condition."""

    def _get_rule(self, rule_pk):
        return WorkflowRule.objects.filter(pk=rule_pk).select_related("model").first()

    def get(self, request, rule_pk=None, pk=None):
        """Render the WorkflowAction form in a modal for creating or editing an action."""
        instance = None
        rule = None
        if pk:
            instance = (
                WorkflowCondition.objects.filter(pk=pk)
                .select_related("rule__model")
                .first()
            )
            if instance:
                rule = instance.rule
        if rule_pk and not rule:
            rule = self._get_rule(rule_pk)
        if not rule:
            return HttpResponse(_("Workflow rule not found."), status=404)

        model_fields = _get_model_fields(rule)
        next_order = rule.conditions.count() + 1
        form = WorkflowConditionForm(instance=instance, model_fields=model_fields)
        return render(
            request,
            "workflow_condition_form.html",
            {
                "form": form,
                "rule": rule,
                "next_order": instance.order if instance else next_order,
                "model_fields": model_fields,
                "edit_pk": pk,
            },
        )

    def post(self, request, rule_pk=None, pk=None):
        """Save the WorkflowCondition and return HTMX response to close modal and refresh condition list. The form is used for both creating a new condition (when pk is not provided) and editing an existing condition (when pk is provided). The rule_pk is used to associate a new condition with the correct WorkflowRule."""
        instance = None
        if pk:
            instance = (
                WorkflowCondition.objects.filter(pk=pk)
                .select_related("rule__model")
                .first()
            )
            rule = instance.rule if instance else None
        else:
            rule_id = request.POST.get("rule") or rule_pk
            rule = self._get_rule(rule_id)

        model_fields = _get_model_fields(rule) if rule else []
        form = WorkflowConditionForm(
            request.POST, instance=instance, model_fields=model_fields
        )
        if form.is_valid():
            form.save()
            messages.success(request, _("Condition saved."))
            return ScriptResponse(
                close=True,
                reload=True,
            )

        return render(
            request,
            "workflow_condition_form.html",
            {
                "form": form,
                "rule": rule,
                "next_order": request.POST.get("order", 0),
                "model_fields": model_fields,
                "edit_pk": pk,
            },
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("workflow.change_workflowrule"),
    name="dispatch",
)
class WorkflowActionFieldsView(LoginRequiredMixin, View):
    """HTMX fragment: render inline action fields for the selected action type."""

    def get(self, request):
        """Return the appropriate fields for the selected action type, which are rendered in the action configuration popup. The fields differ based on the action type (update_field, assign_task, email, notification) and may include dynamic options based on the rule's model."""
        action = request.GET.get("action_type", "") or request.GET.get("action", "")
        rule_pk = request.GET.get("rule_pk", "")
        if action not in ("update_field", "assign_task", "email", "notification"):
            return HttpResponse("")

        rule = (
            WorkflowRule.objects.filter(pk=rule_pk).select_related("model").first()
            if rule_pk
            else None
        )
        field_meta, email_to_choices, notification_to_choices = _build_field_meta(rule)

        rule_ct = rule.model if rule and rule.model_id else None
        mail_templates = HorillaMailTemplate.objects.filter(
            Q(content_type__isnull=True) | Q(content_type=rule_ct)
        )
        notification_templates = NotificationTemplate.objects.filter(
            Q(content_type__isnull=True) | Q(content_type=rule_ct)
        )
        active_company = getattr(request, "active_company", None)
        users = User.objects.filter(is_active=True)
        if active_company is not None:
            users = users.filter(company=active_company)
            mail_templates = mail_templates.filter(
                Q(company=active_company) | Q(company__isnull=True)
            )
            notification_templates = notification_templates.filter(
                Q(company=active_company) | Q(company__isnull=True)
            )

        return render(
            request,
            "workflow_action_fields_fragment.html",
            {
                "action": action,
                "rule_pk": rule_pk,
                "field_meta": field_meta,
                "mail_templates": mail_templates.distinct(),
                "notification_templates": notification_templates.distinct(),
                "users": users,
                "email_to_choices": email_to_choices,
                "notification_to_choices": notification_to_choices,
                "current_values": {},
            },
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("workflow.change_workflowrule"),
    name="dispatch",
)
class WorkflowActionValueWidgetView(LoginRequiredMixin, View):
    """HTMX fragment: return the value widget for a model field (used in update_field popup)."""

    def get(self, request):
        """Return the appropriate input widget configuration for a given field on the rule's model."""
        rule_pk = request.GET.get("rule_pk", "")
        field_name = request.GET.get("field_name", "")
        rule = (
            WorkflowRule.objects.filter(pk=rule_pk).select_related("model").first()
            if rule_pk
            else None
        )
        model_cls = None
        if rule and rule.model_id:
            try:
                model_cls = rule.model.model_class()
            except Exception:
                pass
            if model_cls is None:
                try:
                    model_cls = apps.get_model(rule.model.app_label, rule.model.model)
                except Exception:
                    pass

        widget = {"kind": "text", "input_type": "text", "choices": []}
        if model_cls and field_name:
            try:
                f = model_cls._meta.get_field(field_name)
                if getattr(f, "choices", None):
                    widget = {
                        "kind": "select",
                        "input_type": "select",
                        "choices": [
                            {"value": str(c[0]), "label": str(c[1])} for c in f.choices
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
                elif f.get_internal_type() == "BooleanField":
                    widget = {
                        "kind": "select",
                        "input_type": "boolean",
                        "choices": [
                            {"value": "true", "label": "True"},
                            {"value": "false", "label": "False"},
                        ],
                    }
                elif f.get_internal_type() == "DateField":
                    widget = {"kind": "input", "input_type": "date", "choices": []}
                elif f.get_internal_type() == "DateTimeField":
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
            request, "workflow_action_value_widget_fragment.html", {"widget": widget}
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("workflow.change_workflowrule"),
    name="dispatch",
)
class WorkflowActionSaveView(LoginRequiredMixin, View):
    """HTMX view: GET returns action selector modal; POST saves the WorkflowAction."""

    def _get_rule(self, rule_pk):
        return WorkflowRule.objects.filter(pk=rule_pk).select_related("model").first()

    def get(self, request, rule_pk=None, pk=None):
        """Render the WorkflowAction form in a modal for creating or editing an action."""
        instance = None
        rule = None
        if pk:
            instance = (
                WorkflowAction.objects.filter(pk=pk)
                .select_related("rule__model")
                .first()
            )
            if instance:
                rule = instance.rule
        if rule_pk and not rule:
            rule = self._get_rule(rule_pk)
        if not rule:
            return HttpResponse(_("Workflow rule not found."), status=404)

        next_order = rule.actions.count() + 1
        form = WorkflowActionForm(instance=instance)

        current_values = {}
        if instance and instance.action_type:
            cfg = instance.action_config or {}
            at = instance.action_type
            if at == "update_field":
                current_values = {
                    "update_field": cfg.get("field", ""),
                    "update_value": cfg.get("value", ""),
                }
            elif at == "assign_task":
                current_values = {
                    "task_title": cfg.get("title", ""),
                    "task_due_basis": cfg.get("due_basis", "record_submission_date"),
                    "task_due_in_days": cfg.get("due_in_days", "1"),
                    "task_status": cfg.get("status", "not_started"),
                    "task_priority": cfg.get("priority", "low"),
                    "task_description": cfg.get("description", ""),
                }
            elif at == "email":
                current_values = {
                    "email_template_id": cfg.get("template_id", ""),
                    "email_to": cfg.get("to", ""),
                    "email_also_send_to": cfg.get("also_send_to", ""),
                }
            elif at == "notification":
                current_values = {
                    "notification_template_id": cfg.get("template_id", ""),
                    "notification_to": cfg.get("to", ""),
                    "notification_also_notify_to": cfg.get("also_notify_to", ""),
                    "notification_custom_message": cfg.get("custom_message", ""),
                }

        field_meta, email_to_choices, notification_to_choices = _build_field_meta(rule)
        rule_ct = rule.model if rule and rule.model_id else None
        mail_templates = HorillaMailTemplate.objects.filter(
            Q(content_type__isnull=True) | Q(content_type=rule_ct)
        )
        notification_templates = NotificationTemplate.objects.filter(
            Q(content_type__isnull=True) | Q(content_type=rule_ct)
        )
        active_company = getattr(request, "active_company", None)
        users = User.objects.filter(is_active=True)
        if active_company is not None:
            users = users.filter(company=active_company)
            mail_templates = mail_templates.filter(
                Q(company=active_company) | Q(company__isnull=True)
            )
            notification_templates = notification_templates.filter(
                Q(company=active_company) | Q(company__isnull=True)
            )

        return render(
            request,
            "workflow_action_form.html",
            {
                "form": form,
                "rule": rule,
                "next_order": instance.order if instance else next_order,
                "edit_pk": pk,
                "current_values": current_values,
                "field_meta": field_meta,
                "mail_templates": mail_templates.distinct(),
                "notification_templates": notification_templates.distinct(),
                "users": users,
                "email_to_choices": email_to_choices,
                "notification_to_choices": notification_to_choices,
            },
        )

    def post(self, request, rule_pk=None, pk=None):
        """Save the WorkflowAction and return HTMX response to close modal and refresh action list."""
        instance = None
        if pk:
            instance = (
                WorkflowAction.objects.filter(pk=pk)
                .select_related("rule__model")
                .first()
            )
            rule = instance.rule if instance else None
        else:
            rule_id = request.POST.get("rule") or rule_pk
            rule = self._get_rule(rule_id)

        form = WorkflowActionForm(request.POST, instance=instance)
        if form.is_valid():
            action = form.save(commit=False)
            if not action.pk:
                action.company = getattr(request, "active_company", None)
            action.save()
            messages.success(request, _("Action saved."))
            return ScriptResponse(
                close=True,
                reload=True,
            )

        next_order = rule.actions.count() + 1 if rule else 0
        return render(
            request,
            "workflow_action_form.html",
            {
                "form": form,
                "rule": rule,
                "next_order": request.POST.get("order", next_order),
                "edit_pk": pk,
            },
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("workflow.change_workflowrule"),
    name="dispatch",
)
class WorkflowTimeTriggerSaveView(LoginRequiredMixin, View):
    """GET: render the time-trigger form modal. POST: save the time-trigger action."""

    def _get_rule(self, rule_pk):
        return WorkflowRule.objects.filter(pk=rule_pk).select_related("model").first()

    def get(self, request, rule_pk=None, pk=None):
        """Render the time-trigger action form modal for create or edit."""
        instance = None
        rule = None
        if pk:
            instance = (
                WorkflowTimeTriggerAction.objects.filter(pk=pk)
                .select_related("rule__model")
                .first()
            )
            if instance:
                rule = instance.rule
        if rule_pk and not rule:
            rule = self._get_rule(rule_pk)
        if not rule:
            return HttpResponse(_("Workflow rule not found."), status=404)

        date_choices = _get_date_field_choices(rule)
        next_order = rule.time_trigger_actions.count() + 1
        form = WorkflowTimeTriggerActionForm(
            instance=instance, date_field_choices=date_choices
        )

        current_values = {}
        if instance and instance.action_type:
            cfg = instance.action_config or {}
            at = instance.action_type
            if at == "update_field":
                current_values = {
                    "update_field": cfg.get("field", ""),
                    "update_value": cfg.get("value", ""),
                }
            elif at == "assign_task":
                current_values = {
                    "task_title": cfg.get("title", ""),
                    "task_due_basis": cfg.get("due_basis", "rule_trigger_date"),
                    "task_due_in_days": cfg.get("due_in_days", "1"),
                    "task_status": cfg.get("status", "not_started"),
                    "task_priority": cfg.get("priority", "low"),
                    "task_description": cfg.get("description", ""),
                }
            elif at == "email":
                current_values = {
                    "email_template_id": cfg.get("template_id", ""),
                    "email_to": cfg.get("to", ""),
                    "email_also_send_to": cfg.get("also_send_to", ""),
                }
            elif at == "notification":
                current_values = {
                    "notification_template_id": cfg.get("template_id", ""),
                    "notification_to": cfg.get("to", ""),
                    "notification_also_notify_to": cfg.get("also_notify_to", ""),
                    "notification_custom_message": cfg.get("custom_message", ""),
                }

        ctx = _build_tt_context(rule, instance=instance, current_values=current_values)
        active_company = getattr(request, "active_company", None)
        if active_company is not None:
            ctx["mail_templates"] = ctx["mail_templates"].filter(
                Q(company=active_company) | Q(company__isnull=True)
            )
            ctx["notification_templates"] = ctx["notification_templates"].filter(
                Q(company=active_company) | Q(company__isnull=True)
            )
            ctx["users"] = ctx["users"].filter(company=active_company)

        ctx.update(
            {
                "form": form,
                "next_order": instance.order if instance else next_order,
                "edit_pk": pk,
                "rule_pk": rule.pk,
            }
        )
        return render(request, "workflow_time_trigger_form.html", ctx)

    def post(self, request, rule_pk=None, pk=None):
        """Save or re-render the time-trigger action form from POST data."""
        instance = None
        if pk:
            instance = (
                WorkflowTimeTriggerAction.objects.filter(pk=pk)
                .select_related("rule__model")
                .first()
            )
            rule = instance.rule if instance else None
        else:
            rule_id = request.POST.get("rule") or rule_pk
            rule = self._get_rule(rule_id)

        date_choices = _get_date_field_choices(rule) if rule else []
        form = WorkflowTimeTriggerActionForm(
            request.POST, instance=instance, date_field_choices=date_choices
        )
        if form.is_valid():
            tt = form.save(commit=False)
            if not tt.pk:
                tt.company = getattr(request, "active_company", None)
            tt.save()
            messages.success(request, _("Time trigger action saved."))
            return ScriptResponse(
                close=True,
                reload=True,
            )

        next_order = rule.time_trigger_actions.count() + 1 if rule else 0
        ctx = _build_tt_context(rule, current_values={})
        ctx.update(
            {
                "form": form,
                "next_order": request.POST.get("order", next_order),
                "edit_pk": pk,
                "rule_pk": rule.pk if rule else "",
            }
        )
        return render(request, "workflow_time_trigger_form.html", ctx)
