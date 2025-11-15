"""
This view handles the methods for team role view
"""

import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView

from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.filters import ScoringRuleFilter
from horilla_core.forms import ScoringCriterionForm
from horilla_core.models import ScoringCondition, ScoringCriterion, ScoringRule
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)


class ScoringRuleView(LoginRequiredMixin, HorillaView):
    """
    Template view for scoring rule page
    """

    template_name = "scoring_rule/scoring_rule_view.html"
    nav_url = reverse_lazy("horilla_core:scoring_rule_nav_view")
    list_url = reverse_lazy("horilla_core:scoring_rule_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_scoringrule"), name="dispatch")
class ScoringRuleNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar for scoring rule
    """

    nav_title = ScoringRule._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_core:scoring_rule_list_view")
    main_url = reverse_lazy("horilla_core:scoring_rule_view")
    filterset_class = ScoringRuleFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "ScoringRule"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    url_name = "scoring_rule_list_view"

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_core.add_scoringrule"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:scoring_rule_create_form')}?new=true""",
            }

    @cached_property
    def actions(self):
        if self.request.user.has_perm("horilla_core.view_scoringrule"):
            return [
                {
                    "action": _("Add column to list"),
                    "attrs": f"""
                            hx-get="{reverse_lazy('horilla_generics:column_selector')}?app_label={self.model_app_label}&model_name={self.model_name}&url_name={self.url_name}"
                            onclick="openModal()"
                            hx-vals='{{"exclude":"is_active"}}'
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            """,
                }
            ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_scoringrule"), name="dispatch"
)
class ScoringRuleListView(LoginRequiredMixin, HorillaListView):
    """
    List view of scoring rule
    """

    model = ScoringRule
    view_id = "scoring_rule_list"
    filterset_class = ScoringRuleFilter
    search_url = reverse_lazy("horilla_core:scoring_rule_list_view")
    main_url = reverse_lazy("horilla_core:scoring_rule_view")
    table_width = False
    table_height_as_class = "h-[500px]"
    bulk_select_option = False
    header_attrs = [
        {"description": {"style": "width: 300px;"}},
    ]

    # def no_record_add_button(self):
    #     if self.request.user.has_perm("horilla_core.add_scoringrule"):
    #         return {
    #             "url": f"""{ reverse_lazy('horilla_core:scoring_rule_create_form')}?new=true""",
    #             "attrs": 'id="partner-role-create"',
    #         }

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("name").verbose_name, "name"),
            (instance._meta.get_field("module").verbose_name, "get_module_display"),
            (instance._meta.get_field("is_active").verbose_name, "is_active_col"),
            (instance._meta.get_field("description").verbose_name, "description"),
        ]

    @cached_property
    def col_attrs(self):
        attrs = {}
        if self.request.user.has_perm("horilla_core.view_scoringrule"):
            attrs = {
                "hx-get": f"{{get_detail_view_url}}",
                "hx-target": "#scoring-rule-view",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "hx-select": "#scoring-rule-view",
            }
        return [
            {
                "name": {
                    "style": "cursor:pointer",
                    "class": "hover:text-primary-600",
                    **attrs,
                }
            }
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_scoringrule"):
            actions.append(
                {
                    "action": "Edit",
                    "src": "assets/icons/edit.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                            hx-get="{get_edit_url}?new=true"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
                },
            )
        if self.request.user.has_perm("horilla_core.delete_scoringrule"):
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                        hx-post="{get_delete_url}"
                        hx-target="#deleteModeBox"
                        hx-swap="innerHTML"
                        hx-trigger="click"
                        hx-vals='{{"check_dependencies": "true"}}'
                        onclick="openDeleteModeModal()"
                    """,
                }
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.add_scoringrule"), name="dispatch"
)
class ScoringRuleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for scoring rule
    """

    model = ScoringRule
    fields = ["name", "module", "description", "is_active"]
    full_width_fields = ["name", "module", "description"]
    modal_height = False

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_core:scoring_rule_update_form", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_core:scoring_rule_create_form")

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk:
            try:
                self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                messages.error(request, "The requested data does not exist.")
                return HttpResponse("<script>$('reloadButton').click();</script>")

        return super().get(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_scoringrule"), name="dispatch"
)
class ScoringRuleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = ScoringRule

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(
    permission_required_or_denied("horilla_core.view_scoringrule"), name="dispatch"
)
class ScoringRuleDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for user page
    """

    template_name = "scoring_rule/scoring_rule_detail_view.html"
    model = ScoringRule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_obj = self.get_object()
        scoring_criteria = ScoringCriterion.objects.filter(rule=current_obj)
        context["current_obj"] = current_obj
        context["scoring_criteria"] = scoring_criteria
        context["nav_url"] = reverse_lazy("horilla_core:scoring_rule_detail_nav_view")
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Exception as e:
            if request.headers.get("HX-Request") == "true":
                messages.error(self.request, e)
                return HttpResponse(headers={"HX-Refresh": "true"})
            raise HorillaHttp404(e)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_scoringrule"), name="dispatch")
class ScoringRuleDetailNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar for scoring rule
    """

    search_url = reverse_lazy("horilla_core:scoring_rule_list_view")
    main_url = reverse_lazy("horilla_core:scoring_rule_view")
    filterset_class = ScoringRuleFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "ScoringRule"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    url_name = "scoring_rule_list_view"
    search_option = False
    navbar_indication = True
    navbar_indication_attrs = {
        "hx-get": reverse_lazy("horilla_core:scoring_rule_view"),
        "hx-target": "#scoring-rule-view",
        "hx-swap": "outerHTML",
        "hx-push-url": "true",
        "hx-select": "#scoring-rule-view",
    }

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     obj_id = self.request.GET.get("obj")
    #     obj = ScoringRule.objects.filter(pk=obj_id).first()
    #     self.nav_title = obj.name
    #     context["nav_title"] = self.nav_title
    #     return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_id = self.request.GET.get("obj")
        if obj_id:
            obj_id_clean = obj_id.split("?")[0].strip()
            try:
                obj_id_int = int(obj_id_clean)
                obj = ScoringRule.objects.filter(pk=obj_id_int).first()
                if obj:
                    self.nav_title = obj.name
                    context["nav_title"] = self.nav_title
            except ValueError:
                logger.error(f"Invalid obj_id parameter: {obj_id}")
        return context

    @cached_property
    def new_button(self):
        model_name = self.request.GET.get("model_name")
        obj = self.request.GET.get("obj")
        if self.request.user.has_perm("horilla_core.add_scoringcriterion"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:scoring_rule_criteria_create_form')}?model_name={model_name}&obj={obj}""",
                "attrs": {"id": "scroring-criteria-create-form"},
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.add_scoringcriterion"), name="dispatch"
)
class ScoringCriterionCreateUpdateView(HorillaSingleFormView):
    model = ScoringCriterion
    form_class = ScoringCriterionForm
    fields = ["rule", "points", "operation_type"]
    condition_fields = ["field", "operator", "value", "logical_operator"]
    hidden_fields = ["rule"]
    modal_height = False
    form_title = _("Create New Rule Criteria")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        model_name = self.request.GET.get("model_name") or self.request.POST.get(
            "model_name"
        )

        if self.object and self.object.rule:
            model_name = self.object.rule.module

        if model_name:
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            kwargs["initial"]["model_name"] = model_name

        kwargs["condition_model"] = ScoringCondition
        kwargs["request"] = self.request

        return kwargs

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk:
            try:
                self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                messages.error(request, "The requested data does not exist.")
                return HttpResponse("<script>$('reloadButton').click();</script>")

        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if not self.kwargs.get("pk"):
            obj = self.request.GET.get("obj") or self.request.POST.get("obj")
            if obj:
                obj_clean = obj.split("?")[0].strip()
                try:
                    obj_id = int(obj_clean)
                    initial["rule"] = ScoringRule.objects.get(pk=obj_id)
                except (ValueError, ScoringRule.DoesNotExist) as e:
                    logger.error(f"Invalid obj parameter: {obj}, error: {e}")
                    pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object and self.object.pk:
            existing_conditions = self.object.conditions.all().order_by("order")
            context["existing_conditions"] = existing_conditions
            form = context.get("form")
            if form and hasattr(form, "condition_field_choices"):
                context["condition_field_choices"] = form.condition_field_choices

        return context

    def form_valid(self, form):
        """Override to handle multiple condition rows"""
        if not self.request.user.is_authenticated:
            messages.error(
                self.request, "You must be logged in to perform this action."
            )
            return self.form_invalid(form)

        condition_rows = form.cleaned_data.get("condition_rows", [])

        if not condition_rows:
            messages.error(self.request, "At least one condition must be provided.")
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                # Save the main ScoringCriterion
                self.object = form.save(commit=False)

                if self.kwargs.get("pk"):
                    self.object.updated_at = timezone.now()
                    self.object.updated_by = self.request.user
                else:
                    self.object.created_at = timezone.now()
                    self.object.created_by = self.request.user
                    self.object.updated_at = timezone.now()
                    self.object.updated_by = self.request.user

                self.object.company = (
                    getattr(_thread_local, "request", None).active_company
                    if hasattr(_thread_local, "request")
                    else self.request.user.company
                )
                self.object.save()

                if self.kwargs.get("pk"):
                    self.object.conditions.all().delete()

                created_conditions = []
                for row_data in condition_rows:
                    condition = ScoringCondition(
                        criterion=self.object,
                        field=row_data["field"],
                        operator=row_data["operator"],
                        value=row_data.get("value", ""),
                        logical_operator=row_data.get("logical_operator", "and"),
                        order=row_data.get("order", 0),
                        created_at=timezone.now(),
                        created_by=self.request.user,
                        updated_at=timezone.now(),
                        updated_by=self.request.user,
                        company=(
                            getattr(_thread_local, "request", None).active_company
                            if hasattr(_thread_local, "request")
                            else self.request.user.company
                        ),
                    )
                    condition.save()
                    created_conditions.append(condition)
                self.request.session["condition_row_count"] = 0
                self.request.session.modified = True
                messages.success(
                    self.request,
                    f"Successfully {'updated' if self.kwargs.get('pk') else 'created'} scoring criterion with {len(created_conditions)} conditions!",
                )

        except Exception as e:
            messages.error(self.request, f"Error saving criterion: {str(e)}")
            return self.form_invalid(form)

        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")

    @cached_property
    def form_url(self):
        model_name = self.request.GET.get("model_name")
        obj = self.request.GET.get("obj")
        pk = self.kwargs.get("pk")
        if pk:
            base_url = reverse_lazy(
                "horilla_core:scoring_rule_criteria_edit_form",
                kwargs={"pk": pk} if pk else None,
            )
        else:
            base_url = reverse_lazy("horilla_core:scoring_rule_criteria_create_form")

        if model_name:
            return f"{base_url}?{urlencode({'model_name': model_name,'obj': obj})}"
        return base_url


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_scoringcriterion"),
    name="dispatch",
)
class ScoringCriteriaDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = ScoringCriterion

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(htmx_required, name="dispatch")
class ScroringActiveToggleView(LoginRequiredMixin, View):
    """Toggle default dashboard for the current user via HTMX"""

    def post(self, request, *args, **kwargs):
        try:
            rule = ScoringRule.objects.get(pk=kwargs["pk"])
            user = request.user
            if user.is_superuser or user.has_perm("horilla_core.scoringrule"):
                if not rule.is_active:
                    rule.is_active = True
                    messages.success(request, f"{rule.name} activated successfully")
                else:
                    rule.is_active = False
                    messages.success(request, f"{rule.name} deactivated successfully")
                rule.save()
                return HttpResponse("<script>$('#reloadButton').click();</script>")

        except Exception as e:
            messages.error(request, e)
            return HttpResponse(("<script>$('#reloadButton').click();</script>"))
