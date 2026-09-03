"""Lead Stage Views"""

# Third-party imports (Django)
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View

# First party imports (Horilla)
from horilla.auth.models import User
from horilla.contrib.core.models import Company
from horilla.contrib.core.progress import BASE_STEPS, ProgressStepsMixin
from horilla.contrib.core.views.initialiaze_database import InitializeRoleView
from horilla.contrib.generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla.contrib.utils.middlewares import _thread_local
from horilla.db import transaction
from horilla.shortcuts import get_object_or_404, redirect, render
from horilla.urls import reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required,
    permission_required_or_denied,
)
from horilla.utils.functional import cached_property
from horilla.utils.translation import gettext_lazy as _
from horilla.web import (
    HttpNotFound,
    HttpResponse,
    HxTriggerResponse,
    JsonResponse,
    ScriptResponse,
)

# Local imports
from horilla_crm.leads.filters import LeadStatusFilter
from horilla_crm.leads.forms import LeadStatusForm
from horilla_crm.leads.models import DEFAULT_LEAD_INIT_STAGES, LeadStatus
from horilla_crm.leads.signals import lead_stage_created


class LeadsStageView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for company information settings page.
    """

    template_name = "settings/settings_list_shell.html"
    view_id = "leads-status-view"
    nav_url = reverse_lazy("leads:lead_stage_nav_view")
    list_url = reverse_lazy("leads:lead_stage_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("leads.view_leadstatus"), name="dispatch")
class LeadStageNavbar(LoginRequiredMixin, HorillaNavView):
    """Navbar for LeadStage"""

    nav_description = _("Define the stages a lead moves through in your pipeline.")
    search_url = reverse_lazy("leads:lead_stage_list_view")
    main_url = reverse_lazy("leads:lead_stage_view")
    filterset_class = LeadStatusFilter
    model_name = "LeadStatus"
    model_app_label = "leads"
    nav_width = False
    all_view_types = False
    recently_viewed_option = False
    filter_option = False
    one_view_only = True
    reload_option = False
    border_enabled = False

    @cached_property
    def new_button(self):
        """New button configuration"""
        if self.request.user.has_perm("leads.add_leadstatus"):
            return {
                "url": f"""{reverse_lazy("leads:create_lead_stage")}?new=true""",
                "attrs": {"id": "lead-stage-create"},
            }
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.view_leadstatus"), name="dispatch"
)
class LeadStageListView(LoginRequiredMixin, HorillaListView):
    """
    Lead List view
    """

    model = LeadStatus
    view_id = "lead-stage-list"
    filterset_class = LeadStatusFilter
    search_url = reverse_lazy("leads:lead_stage_list_view")
    main_url = reverse_lazy("leads:lead_stage_view")
    save_to_list_option = False
    bulk_select_option = False
    enable_sorting = False

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.order_by("order")
        return queryset

    @cached_property
    def col_attrs(self):
        """Define column attributes for the list view"""
        return [
            {
                "order": {
                    "is_draggable": "true",
                    "sort_url": reverse_lazy("leads:update_lead_stage_order"),
                    "permission": "leads.change_leadstatus",
                }
            }
        ]

    def no_record_add_button(self):
        """Button to show when no records exist"""
        if self.request.user.has_perm("leads.add_leadstatus"):
            return {
                "url": f"""{reverse_lazy("leads:create_lead_stage")}?new=true""",
                "attrs": 'id="lead-stage-create"',
            }
        return None

    columns = ["order", "name", ("is_final", "is_final_col"), "probability"]
    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "permission": "leads.change_leadstatus",
            "attrs": """
                        hx-get="{get_edit_url}?new=true"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "leads.delete_leadstatus",
            "attrs": """
                    hx-post="{get_delete_url}"
                    hx-target="#deleteModeBox"
                    hx-swap="innerHTML"
                    hx-trigger="click"
                    hx-vals='{{"check_dependencies": "true"}}'
                    onclick="openDeleteModeModal()"
                """,
        },
    ]


@method_decorator(
    permission_required_or_denied("leads.change_leadstatus"), name="dispatch"
)
class ChangeFinalStage(LoginRequiredMixin, View):
    """
    View to change the default currency for a company and update conversion rates.
    """

    def post(self, request, *_args, **kwargs):
        """Handle changing the final lead stage."""
        stage_id = kwargs.get("pk")
        try:
            company = getattr(request, "active_company", None) or request.user.company
            new_final_stage = LeadStatus.objects.get(id=stage_id, company=company)
            with transaction.atomic():
                new_final_stage.is_final = True
                new_final_stage.save()
            messages.success(request, _("Final Stage  changed successfully."))
            return HxTriggerResponse()

        except Exception as e:
            messages.error(request, e)
            return ScriptResponse(reload=True)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadstatus"), name="dispatch"
)
class CreateLeadStage(LoginRequiredMixin, HorillaSingleFormView):
    """View to create or edit a LeadStatus instance."""

    model = LeadStatus
    modal_height = False
    form_class = LeadStatusForm

    def get_initial(self):
        """Provide default stage order when creating a new lead stage."""
        initial = super().get_initial()
        if not self.kwargs.get("pk"):  # Only set initial order for new stages
            company = (
                getattr(_thread_local, "request", None).active_company
                if hasattr(_thread_local, "request")
                else self.request.user.company
            )
            if company:
                initial["order"] = LeadStatus.get_next_order_for_company(company)
        return initial

    @cached_property
    def form_url(self):
        """URL to load the form"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("leads:edit_lead_stage", kwargs={"pk": pk})
        return reverse_lazy("leads:create_lead_stage")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.change_leadstatus"), name="dispatch"
)
class ToggleOrderFieldView(LoginRequiredMixin, TemplateView):
    """
    HTMX endpoint to toggle the visibility of the order field based on is_final checkbox
    """

    template_name = "lead_status/order_field.html"

    def get_context_data(self, **kwargs):
        """Return template state for order-field visibility and default value."""
        context = super().get_context_data(**kwargs)
        is_final = self.request.POST.get("is_final") or self.request.GET.get("is_final")
        current_order_value = self.request.POST.get(
            "order", ""
        ) or self.request.GET.get("order", "")

        context["show_order_field"] = is_final != "on"

        if context["show_order_field"] and not current_order_value:
            company = (
                getattr(_thread_local, "request", None).active_company
                if hasattr(_thread_local, "request")
                else self.request.user.company
            )
            if company:
                current_order_value = LeadStatus.get_next_order_for_company(company)

        context["order_value"] = current_order_value
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests to toggle order field visibility."""
        return self.get(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.delete_leadstatus", modal=True),
    name="dispatch",
)
class LeadStatusDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """View to handle deletion of a LeadStatus instance."""

    model = LeadStatus

    def get_post_delete_response(self):
        return HxTriggerResponse()


@method_decorator(
    permission_required_or_denied("leads.change_leadstatus"), name="dispatch"
)
class UpdateLeadStageOrderView(LoginRequiredMixin, View):
    """
    Handles AJAX requests for updating lead stage order via drag-and-drop
    """

    def post(self, request, *_args, **_kwargs):
        """Handle updating lead stage order via drag-and-drop."""
        try:
            ids = request.POST.getlist("ids[]") or request.POST.getlist("ids")
            if not ids:
                return JsonResponse(
                    {"status": "error", "message": "No IDs provided"}, status=400
                )

            with transaction.atomic():
                # Get all statuses at once for efficiency
                statuses = {str(s.id): s for s in LeadStatus.objects.filter(id__in=ids)}

                # Validate all IDs exist
                if len(statuses) != len(ids):
                    missing_ids = set(ids) - set(statuses.keys())
                    return JsonResponse(
                        {"status": "error", "message": f"Invalid IDs: {missing_ids}"},
                        status=400,
                    )

                # Update orders while maintaining final stage constraints
                for order, status_id in enumerate(ids, start=1):
                    status = statuses[status_id]
                    if not status.is_final:  # Only update order for non-final stages
                        if status.order != order:
                            status.order = order
                            status.save(update_fields=["order"])

                # Ensure final stages are always last
                self._ensure_final_stages_last(company=statuses[ids[0]].company)

            return JsonResponse({"status": "success"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    def _ensure_final_stages_last(self, company):
        """
        Ensures all final stages are ordered after non-final stages
        """
        non_final = list(
            LeadStatus.objects.filter(company=company, is_final=False).order_by(
                "order", "id"
            )
        )

        final = list(
            LeadStatus.objects.filter(company=company, is_final=True).order_by(
                "order", "id"
            )
        )

        with transaction.atomic():
            for order, status in enumerate(non_final + final, start=1):
                if status.order != order:
                    LeadStatus.objects.filter(id=status.id).update(order=order)


@method_decorator(htmx_required(), name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.view_leadstatus"), name="dispatch"
)
class LoadLeadStagesView(LoginRequiredMixin, View):
    """View to display the lead stages modal."""

    def get(self, request, company_id):
        """Handle displaying the lead stages modal."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HttpNotFound(e) from e
        initialization = request.GET.get("initialization") == "true"
        default_stages = DEFAULT_LEAD_INIT_STAGES

        all_stages = LeadStatus.all_objects.values(
            "name", "order", "probability", "is_final", "company__name", "company_id"
        ).order_by("company_id", "order")

        raw_company_stages = {}
        for stage in all_stages:
            company_id = stage["company_id"]
            if company_id not in raw_company_stages:
                raw_company_stages[company_id] = {
                    "company_name": stage["company__name"],
                    "stages": [],
                }
            raw_company_stages[company_id]["stages"].append(
                {
                    "name": stage["name"],
                    "order": stage["order"],
                    "probability": stage["probability"],
                    "is_final": stage["is_final"],
                }
            )

        # Create signature for stage comparison
        def create_stage_signature(stages):
            """Create a hashable signature for a set of stages"""
            return tuple(
                (s["name"], s["order"], s["probability"], s["is_final"])
                for s in sorted(stages, key=lambda x: x["order"])
            )

        # Group companies by their stage signatures
        signature_groups = {}
        default_signature = create_stage_signature(default_stages)

        for _comp_id, comp_data in raw_company_stages.items():
            signature = create_stage_signature(comp_data["stages"])

            if signature == default_signature:
                continue

            if signature not in signature_groups:
                signature_groups[signature] = []
            signature_groups[signature].append(comp_data)

        company_stages = {}

        group_counter = 1
        for signature, companies in signature_groups.items():
            representative = companies[0]

            if len(companies) > 1:
                _company_names = [comp["company_name"] for comp in companies]
                representative["company_name"] = (
                    f"{representative['company_name']} (+{len(companies) - 1} others)"
                )

            company_stages[f"group_{group_counter}"] = representative
            group_counter += 1

        # Build context dictionary
        context = {
            "default_stages": default_stages,
            "company_stages": company_stages,
            "company": company,
            "initialization": initialization,
            "hx_target": (
                "initialize-lead-stages" if initialization else "stage-messages"
            ),
            "hx_swap": "outerHTML" if initialization else "innerHTML",
            "hx_push_url": (
                reverse_lazy("opportunities:initialiaze_opportunity_stages")
                if initialization
                else "false"
            ),
        }

        # Only add hx_select when initialization is True
        if initialization:
            context["hx_select"] = "#initialize-opportunity-stages"

        return render(
            request,
            "lead_status/lead_stages_modal.html",
            context,
        )


@method_decorator(htmx_required(), name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadstatus"), name="dispatch"
)
class CustomStagesFormView(LoginRequiredMixin, View):
    """View to display the custom stages form."""

    def get(self, request, company_id):
        """Handle displaying the custom stages form."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HttpNotFound(e) from e

        initialization = request.GET.get("initialization") == "True"
        all_stages_from_db = LeadStatus.all_objects.values(
            "name", "order", "probability", "is_final", "company__name", "company_id"
        ).order_by("company_id", "order")

        default_stages = DEFAULT_LEAD_INIT_STAGES

        unique_stages = {}

        for stage in default_stages:
            unique_stages[stage["name"]] = stage

        for stage in all_stages_from_db:
            stage_name = stage["name"]
            if stage_name not in unique_stages:
                unique_stages[stage_name] = {
                    "name": stage["name"],
                    "order": stage["order"],
                    "probability": stage["probability"],
                    "is_final": stage["is_final"],
                }

        combined_stages = []
        for i, (_name, stage) in enumerate(unique_stages.items(), 1):
            stage_copy = stage.copy()
            stage_copy["order"] = i
            combined_stages.append(stage_copy)

        # Build context dictionary
        context = {
            "company": company,
            "company_stages": {company_id: combined_stages},
            "default_stages": combined_stages,
            "initialization": initialization,
            "hx_target": (
                "initialize-lead-stages" if initialization else "stage-messages"
            ),
            "hx_swap": "outerHTML" if initialization else "innerHTML",
            "hx_push_url": (
                reverse_lazy("opportunities:initialiaze_opportunity_stages")
                if initialization
                else "false"
            ),
        }

        # Only add hx_select when initialization is True
        if initialization:
            context["hx_select"] = "#initialize-opportunity-stages"

        return render(
            request,
            "lead_status/custom_stages_form.html",
            context,
        )


@method_decorator(htmx_required(), name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadstatus"), name="dispatch"
)
class SaveCustomStagesView(LoginRequiredMixin, View, ProgressStepsMixin):
    """View to handle saving custom lead stages during company creation."""

    current_step = 6

    def get_signal_kwargs(self, company, request, initialization, stages=None):
        """
        Extension point: Override this method to pass additional data to signal.
        Clients can add custom data without modifying source code.
        """
        return {
            "company": company,
            "request": request,
            "view": self,
            "initialization": initialization,
            "stages": stages or [],
        }

    def _error_response(self, request, message):
        """Return HTMX response that shows error in form (single-form-view style, oob into #custom-stages-error)."""
        return render(
            request,
            "lead_status/save_custom_stages_response.html",
            {"error_message": message},
            status=200,
        )

    def _success_response(self, request):
        """Return HTMX response that clears any previous error in the form."""
        return render(
            request,
            "lead_status/save_custom_stages_response.html",
            {"error_message": None},
            status=200,
        )

    def post(self, request, company_id):
        """Handle saving custom lead stages during company creation."""
        initialization = request.GET.get("initialization") == "True"
        if initialization:
            init_company_id = request.session.get("company_id")
            if request.session.get("db_password") != settings.DB_INIT_PASSWORD or (
                str(init_company_id) != str(company_id)
            ):
                raise HttpNotFound("Company not found.")
        else:
            active_company = getattr(request, "active_company", None) or getattr(
                request.user, "company", None
            )
            is_active_company = active_company and str(active_company.id) == str(
                company_id
            )
            newly_created_company_id = request.session.get("newly_created_company_id")
            is_newly_created = str(newly_created_company_id) == str(company_id)
            if not (is_active_company or is_newly_created):
                raise HttpNotFound("Company not found.")
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HttpNotFound(e) from e
        stage_names = request.POST.getlist("stage_name_custom[]")
        stage_orders = request.POST.getlist("stage_order_custom[]")
        stage_probabilities = request.POST.getlist("stage_probability_custom[]")
        stage_is_finals = request.POST.getlist("stage_is_final_custom[]")
        initialization = request.GET.get("initialization") == "True"

        # Validate that all lists have the same length
        n = len(stage_names)
        if len(stage_orders) != n or len(stage_probabilities) != n:
            return self._error_response(
                request,
                "Invalid form data: order or probability missing for one or more stages.",
            )

        try:
            # Validate all stages before making any DB changes
            parsed_stages = []
            seen_names = set()
            for i, name in enumerate(stage_names):
                is_final = str(i) in stage_is_finals
                name = name.strip()
                if not name:
                    return self._error_response(
                        request, f"Stage name cannot be empty for stage {i + 1}."
                    )
                if name in seen_names:
                    return self._error_response(
                        request, f'Duplicate stage name "{name}" in submission.'
                    )
                seen_names.add(name)
                try:
                    order = int(stage_orders[i])
                except (ValueError, TypeError):
                    return self._error_response(
                        request,
                        f'Invalid order for stage {i + 1} ("{name}"). Use a whole number.',
                    )
                try:
                    probability = float(stage_probabilities[i])
                except (ValueError, TypeError):
                    return self._error_response(
                        request,
                        f'Invalid probability for stage "{name}". Use a number between 0 and 100.',
                    )
                if probability < 0 or probability > 100:
                    return self._error_response(
                        request,
                        f"Probability must be between 0 and 100 for stage: {name}",
                    )
                parsed_stages.append(
                    {
                        "name": name,
                        "order": order,
                        "probability": probability,
                        "is_final": is_final,
                    }
                )

            with transaction.atomic():
                submitted_names = {s["name"] for s in parsed_stages}

                # Delete only stages with no leads attached
                for stage in LeadStatus.all_objects.filter(company=company):
                    if stage.name not in submitted_names and not stage.lead.exists():
                        stage.delete()

                for stage_data in parsed_stages:
                    LeadStatus.all_objects.update_or_create(
                        company=company,
                        name=stage_data["name"],
                        defaults={
                            "order": stage_data["order"],
                            "probability": stage_data["probability"],
                            "is_final": stage_data["is_final"],
                        },
                    )

            messages.success(
                request, f"Successfully created {company} and associated Lead Stages."
            )
            stages = list(
                LeadStatus.all_objects.filter(company=company).order_by("order")
            )
            signal_kwargs = self.get_signal_kwargs(
                company=company,
                request=request,
                initialization=initialization,
                stages=stages,
            )

            responses = lead_stage_created.send(sender=self.__class__, **signal_kwargs)

            for _receiver, response in responses:
                if isinstance(response, HttpResponse):
                    return response

            return self._success_response(request)

        except Exception:
            return self._error_response(
                request,
                "An error occurred while saving stages. Please try again.",
            )


@method_decorator(htmx_required(), name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadstatus"), name="dispatch"
)
class AddStageView(LoginRequiredMixin, View):
    """View to handle adding a new stage to the custom stages form."""

    def get(self, request, company_id):
        """Handle adding a new stage to the custom stages form."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HttpNotFound(e) from e

        stage_orders = request.GET.getlist("stage_order_custom[]", [])
        max_order = (
            max([int(order) for order in stage_orders if order], default=0)
            if stage_orders
            else 0
        )
        new_order = max_order + 1
        new_stage = {
            "name": "",
            "order": new_order,
            "probability": 0,
            "is_final": False,
        }
        stage_index = len(stage_orders)
        return render(
            request,
            "lead_status/stage_item.html",
            {
                "stage": new_stage,
                "company": company,
                "stage_index": stage_index,
            },
        )


@method_decorator(htmx_required(), name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadstatus"), name="dispatch"
)
class RemoveStageView(LoginRequiredMixin, View):
    """View to handle removing a stage from the custom stages form."""

    def post(self, request, company_id):
        """Handle removing a stage from the custom stages form."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HttpNotFound(e) from e
        stage_names = request.POST.getlist("stage_name_custom[]")
        stage_orders = request.POST.getlist("stage_order_custom[]")
        stage_probabilities = request.POST.getlist("stage_probability_custom[]")
        stage_is_finals = request.POST.getlist("stage_is_final_custom[]")
        remove_index = request.POST.get("remove_index", "-1")

        try:
            remove_index = int(remove_index)
        except ValueError:
            response = render(
                request,
                "common/message_fragment.html",
                {"message": "Invalid remove index."},
            )
            response.status_code = 400
            return response

        stages = []
        for i, name in enumerate(stage_names):
            if i != remove_index:
                stages.append(
                    {
                        "name": name.strip(),
                        "order": int(stage_orders[i]),
                        "probability": float(stage_probabilities[i]),
                        "is_final": str(i) in stage_is_finals,
                    }
                )
        return render(
            request,
            "lead_status/custom_stages_form.html",
            {
                "company": company,
                "company_stages": {company_id: {"stages": stages}},
                "default_stages": [],
            },
        )


@method_decorator(htmx_required(), name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadstatus"), name="dispatch"
)
class CreateStageGroupView(LoginRequiredMixin, View, ProgressStepsMixin):
    """View to handle saving custom lead stages during database setup."""

    current_step = 6

    def get_signal_kwargs(self, company, stages, request, initialization):
        """
        Extension point: Override this method to pass additional data to signal.
        Clients can add custom data without modifying source code.
        """
        return {
            "company": company,
            "stages": stages,
            "request": request,
            "view": self,
            "initialization": initialization,
        }

    def post(self, request, pk):
        """Handle saving custom lead stages during database setup."""
        initialization = request.GET.get("initialization") == "True"
        if initialization:
            init_company_id = request.session.get("company_id")
            if request.session.get("db_password") != settings.DB_INIT_PASSWORD or (
                str(init_company_id) != str(pk)
            ):
                raise HttpNotFound("Company not found.")
        else:
            active_company = getattr(request, "active_company", None) or getattr(
                request.user, "company", None
            )
            is_active_company = active_company and str(active_company.id) == str(pk)
            newly_created_company_id = request.session.get("newly_created_company_id")
            is_newly_created = str(newly_created_company_id) == str(pk)
            if not (is_active_company or is_newly_created):
                raise HttpNotFound("Company not found.")
        try:
            company = get_object_or_404(Company, pk=pk)
        except Exception as e:
            raise HttpNotFound(e) from e
        stage_names = request.POST.getlist("stage_name")
        stage_orders = request.POST.getlist("stage_order")
        stage_probabilities = request.POST.getlist("stage_probability")
        stage_is_finals = request.POST.getlist("stage_is_final")

        try:
            created_stages = []
            for i in range(len(stage_names)):
                is_final_value = (
                    stage_is_finals[i] if i < len(stage_is_finals) else "false"
                )
                is_final = is_final_value.lower() in ["true", "on", "1", "yes"]

                try:
                    order = int(stage_orders[i])
                    probability = float(stage_probabilities[i])
                except (ValueError, IndexError) as e:
                    response = render(
                        request,
                        "common/message_fragment.html",
                        {
                            "message": f"Invalid numeric value for stage {i + 1}: {str(e)}"
                        },
                    )
                    response.status_code = 400
                    return response

                if probability < 0 or probability > 100:
                    response = render(
                        request,
                        "common/message_fragment.html",
                        {
                            "message": f"Probability must be between 0 and 100 for stage: {stage_names[i]}",
                        },
                    )
                    response.status_code = 400
                    return response

                if LeadStatus.objects.filter(
                    name=stage_names[i], company=company
                ).exists():
                    response = render(
                        request,
                        "common/message_fragment.html",
                        {
                            "message": f'Stage "{stage_names[i]}" already exists for this company.',
                        },
                    )
                    response.status_code = 400
                    return response

                stage = LeadStatus.objects.create(
                    name=stage_names[i],
                    order=order,
                    probability=probability,
                    is_final=is_final,
                    company=company,
                    created_by=(
                        request.user
                        if request.user.is_authenticated
                        else User.objects.first()
                    ),
                )
                created_stages.append(stage)
            messages.success(
                request, f"Successfully created {company} and associated Lead Stages."
            )
            signal_kwargs = self.get_signal_kwargs(
                company=company,
                stages=created_stages,
                request=request,
                initialization=initialization,
            )

            responses = lead_stage_created.send(sender=self.__class__, **signal_kwargs)

            for _receiver, response in responses:
                if isinstance(response, HttpResponse):
                    return response

            return None

        except Exception as e:
            response = render(
                request,
                "common/message_fragment.html",
                {
                    "message": "An error occurred while creating stages. Please try again."
                },
            )
            response.status_code = 500
            return response


BASE_STEPS.append({"step": 5, "title": "Lead Stages"})
BASE_STEPS.append({"step": 6, "title": "Opportunity Stages"})


class InitializeDatabaseLeadStages(LoginRequiredMixin, View, ProgressStepsMixin):
    """View to handle the initialization of lead stages during database setup."""

    current_step = 5

    def get(self, request, *_args, **_kwargs):
        """Render the lead stages initialization page if the user has the correct permissions"""
        company_id = request.POST.get("company_id") or request.session.get("company_id")
        if request.session.get("db_password") == settings.DB_INIT_PASSWORD:
            context = {
                "progress_steps": self.get_progress_steps(),
                "current_step": self.current_step,
                "company_id": company_id,
            }
            return render(request, "lead_status/lead_stages_initialize.html", context)
        return redirect("/")


InitializeRoleView.response_template = "lead_status/lead_stages_initialize.html"
InitializeRoleView.push_url = reverse_lazy("leads:initialize_lead_stages")
InitializeRoleView.select_id = "initialize-lead-stages"
