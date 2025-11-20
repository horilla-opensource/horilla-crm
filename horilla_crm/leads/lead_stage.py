"""Lead Stage Views"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render  # type: ignore
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.initialiaze_database import InitializeRoleView
from horilla_core.models import Company, HorillaUser
from horilla_core.progress import BASE_STEPS, ProgressStepsMixin
from horilla_crm.leads.filters import LeadStatusFilter
from horilla_crm.leads.forms import LeadStatusForm  # type: ignore
from horilla_crm.leads.models import LeadStatus
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_utils.middlewares import _thread_local


class LeadsStageView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for company information settings page.
    """

    template_name = "lead_status/leads_status_view.html"
    nav_url = reverse_lazy("leads:lead_stage_nav_view")
    list_url = reverse_lazy("leads:lead_stage_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("leads.view_leadstatus"), name="dispatch")
class LeadStageNavbar(LoginRequiredMixin, HorillaNavView):
    """Navbar for LeadStage"""

    nav_title = LeadStatus._meta.verbose_name_plural
    search_url = reverse_lazy("leads:lead_stage_list_view")
    main_url = reverse_lazy("leads:lead_stage_view")
    filterset_class = LeadStatusFilter
    model_name = "LeadStatus"
    model_app_label = "leads"
    nav_width = False
    gap_enabled = False
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
                "url": f"""{ reverse_lazy('leads:create_lead_stage')}?new=true""",
                "attrs": {"id": "lead-stage-create"},
            }


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
    clear_session_button_enabled = False
    table_width = False
    enable_sorting = False
    table_height_as_class = "h-[500px]"

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
                }
            }
        ]

    def no_record_add_button(self):
        """Button to show when no records exist"""
        if self.request.user.has_perm("leads.add_leadstatus"):
            return {
                "url": f"""{ reverse_lazy('leads:create_lead_stage')}?new=true""",
                "attrs": 'id="lead-stage-create"',
            }

    columns = ["order", "name", (_("Is Final Stage"), "is_final_col"), "probability"]

    @cached_property
    def actions(self):
        """Define actions for each row in the list view"""
        actions = []
        if self.request.user.has_perm("leads.change_leadstatus"):
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
        if self.request.user.has_perm("leads.delete_leadstatus"):
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
            messages.success(request, "Final Stage  changed successfully.")
            return HttpResponse(
                "<script>htmx.trigger('#reloadButton','click')</script>"
            )

        except Exception as e:
            messages.error(request, e)
            return HttpResponse("<script>$('#reloadButton').click();</script>")


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
    permission_required_or_denied("leads.delete_leadstatus"), name="dispatch"
)
class LeadStatusDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """View to handle deletion of a LeadStatus instance."""

    model = LeadStatus

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


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


@method_decorator(htmx_required(login=False), name="dispatch")
class LoadLeadStagesView(View):
    """View to display the lead stages modal."""

    def get(self, request, company_id):
        """Handle displaying the lead stages modal."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HorillaHttp404(e) from e
        initialization = request.GET.get("initialization") == "true"
        default_stages = [
            {"name": "New", "order": 1, "probability": 10, "is_final": False},
            {"name": "Contacted", "order": 2, "probability": 30, "is_final": False},
            {"name": "Qualified", "order": 3, "probability": 60, "is_final": False},
            {"name": "Proposal", "order": 4, "probability": 80, "is_final": False},
            {"name": "Lost", "order": 5, "probability": 0, "is_final": False},
            {"name": "Convert", "order": 6, "probability": 100, "is_final": True},
        ]

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
        has_default_match = False

        for _comp_id, comp_data in raw_company_stages.items():
            signature = create_stage_signature(comp_data["stages"])

            if signature == default_signature:
                has_default_match = True
                continue

            if signature not in signature_groups:
                signature_groups[signature] = []
            signature_groups[signature].append(comp_data)

        company_stages = {}

        group_counter = 1
        for signature, companies in signature_groups.items():
            representative = companies[0]

            if len(companies) > 1:
                company_names = [comp["company_name"] for comp in companies]
                representative["company_name"] = (
                    f"{representative['company_name']} (+{len(companies)-1} others)"
                )

            company_stages[f"group_{group_counter}"] = representative
            group_counter += 1

        modal_content = render_to_string(
            "lead_status/lead_stages_modal.html",
            {
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
                "hx_select": "#initialize-opportunity-stages",
            },
            request=request,
        )
        return HttpResponse(modal_content)


@method_decorator(htmx_required(login=False), name="dispatch")
class CustomStagesFormView(View):
    """View to display the custom stages form."""

    def get(self, request, company_id):
        """Handle displaying the custom stages form."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HorillaHttp404(e) from e

        initialization = request.GET.get("initialization") == "True"
        all_stages_from_db = LeadStatus.all_objects.values(
            "name", "order", "probability", "is_final", "company__name", "company_id"
        ).order_by("company_id", "order")

        default_stages = [
            {"name": "New", "order": 1, "probability": 10, "is_final": False},
            {"name": "Contacted", "order": 2, "probability": 30, "is_final": False},
            {"name": "Qualified", "order": 3, "probability": 60, "is_final": False},
            {"name": "Proposal", "order": 4, "probability": 80, "is_final": False},
            {"name": "Lost", "order": 5, "probability": 0, "is_final": False},
            {"name": "Convert", "order": 6, "probability": 100, "is_final": True},
        ]

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

        modal_content = render_to_string(
            "branches/custom_stages_form.html",
            {
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
                "hx_select": "#initialize-opportunity-stages",
            },
            request=request,
        )
        return HttpResponse(modal_content)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(htmx_required(login=False), name="dispatch")
class SaveCustomStagesView(View, ProgressStepsMixin):
    """View to handle saving custom lead stages during company creation."""

    current_step = 6

    def post(self, request, company_id):
        """Handle saving custom lead stages during company creation."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HorillaHttp404(e) from e
        stage_names = request.POST.getlist("stage_name_custom[]")
        stage_orders = request.POST.getlist("stage_order_custom[]")
        stage_probabilities = request.POST.getlist("stage_probability_custom[]")
        stage_is_finals = request.POST.getlist("stage_is_final_custom[]")
        initialization = request.GET.get("initialization") == "True"

        LeadStatus.all_objects.filter(company=company).delete()

        try:
            for i in range(len(stage_names)):
                is_final = str(i) in stage_is_finals
                name = stage_names[i].strip()
                if not name:
                    return HttpResponse(
                        f'<div class="alert alert-danger">Stage name cannot be empty for stage {i+1}.</div>',
                        status=400,
                    )
                order = int(stage_orders[i])
                probability = float(stage_probabilities[i])
                if probability < 0 or probability > 100:
                    return HttpResponse(
                        f'<div class="alert alert-danger">Probability must be between 0 and 100 for stage: {name}</div>',
                        status=400,
                    )
                if LeadStatus.all_objects.filter(company=company, name=name).exists():
                    return HttpResponse(
                        f'<div class="alert alert-danger">Stage "{name}" already exists for this company.</div>',
                        status=400,
                    )
                LeadStatus.all_objects.create(
                    company=company,
                    name=name,
                    order=order,
                    probability=probability,
                    is_final=is_final,
                )

            messages.success(
                request, f"Successfully created {company} and associated Lead Stages."
            )
            if initialization:
                context = {
                    "progress_steps": self.get_progress_steps(),
                    "current_step": self.current_step,
                    "company_id": company.id,
                }
                return render(
                    request, "opportunity_stage/oppor_stages_initialize.html", context
                )
            return HttpResponse(
                """
                <script>
                    closeContentModal();
                    $('#reloadButton').click();
                     openContentModalSecond();
                        var div = document.createElement('div');
                        div.setAttribute('hx-get', '%s');
                        div.setAttribute('hx-target', '#contentModalBoxSecond');
                        div.setAttribute('hx-trigger', 'load');
                        div.setAttribute('hx-swap', 'innerHTML');
                        document.body.appendChild(div);
                        htmx.process(div);
                </script>
                """
                % reverse_lazy(
                    "opportunities:load_opp_stages", kwargs={"company_id": company_id}
                ),
                headers={"X-Debug": "Modal transition in progress"},
            )

        except:
            return HttpResponse()


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(htmx_required(login=False), name="dispatch")
class AddStageView(View):
    """View to handle adding a new stage to the custom stages form."""

    def get(self, request, company_id):
        """Handle adding a new stage to the custom stages form."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HorillaHttp404(e) from e

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
        return HttpResponse(
            render_to_string(
                "branches/stage_item.html",
                {"stage": new_stage, "company": company},
                request=request,
            )
        )


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(htmx_required(login=False), name="dispatch")
class RemoveStageView(View):
    """View to handle removing a stage from the custom stages form."""

    def post(self, request, company_id):
        """Handle removing a stage from the custom stages form."""
        try:
            company = get_object_or_404(Company, id=company_id)
        except Exception as e:
            raise HorillaHttp404(e) from e
        stage_names = request.POST.getlist("stage_name_custom[]")
        stage_orders = request.POST.getlist("stage_order_custom[]")
        stage_probabilities = request.POST.getlist("stage_probability_custom[]")
        stage_is_finals = request.POST.getlist("stage_is_final_custom[]")
        remove_index = request.POST.get("remove_index", "-1")

        try:
            remove_index = int(remove_index)
        except ValueError:
            return HttpResponse(
                '<div class="alert alert-danger">Invalid remove index.</div>',
                status=400,
            )

        stages = []
        for i in range(len(stage_names)):
            if i != remove_index:
                stages.append(
                    {
                        "name": stage_names[i].strip(),
                        "order": int(stage_orders[i]),
                        "probability": float(stage_probabilities[i]),
                        "is_final": str(i) in stage_is_finals,
                    }
                )

        return HttpResponse(
            render_to_string(
                "branches/custom_stages_form.html",
                {
                    "company": company,
                    "company_stages": {company_id: {"stages": stages}},
                    "default_stages": [],
                },
                request=request,
            )
        )


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(htmx_required(login=False), name="dispatch")
class CreateStageGroupView(View, ProgressStepsMixin):
    """View to handle saving custom lead stages during database setup."""

    current_step = 6

    def post(self, request, pk):
        """Handle saving custom lead stages during database setup."""
        try:
            company = get_object_or_404(Company, pk=pk)
        except Exception as e:
            raise HorillaHttp404(e) from e

        initialization = request.GET.get("initialization") == "True"
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
                    return HttpResponse(
                        f'<div class="alert alert-danger">Invalid numeric value for stage {i+1}: {str(e)}</div>',
                        status=400,
                    )

                if probability < 0 or probability > 100:
                    return HttpResponse(
                        f'<div class="alert alert-danger">Probability must be between 0 and 100 for stage: {stage_names[i]}</div>',
                        status=400,
                    )

                if LeadStatus.objects.filter(
                    name=stage_names[i], company=company
                ).exists():
                    return HttpResponse(
                        f'<div class="alert alert-danger">Stage "{stage_names[i]}" already exists for this company.</div>',
                        status=400,
                    )

                stage = LeadStatus.objects.create(
                    name=stage_names[i],
                    order=order,
                    probability=probability,
                    is_final=is_final,
                    company=company,
                    created_by=(
                        request.user
                        if request.user.is_authenticated
                        else HorillaUser.objects.first()
                    ),
                )
                created_stages.append(stage)
            messages.success(
                request, f"Successfully created {company} and associated Lead Stages."
            )
            if initialization:
                context = {
                    "progress_steps": self.get_progress_steps(),
                    "current_step": self.current_step,
                    "company_id": company.id,
                }
                return render(
                    request, "opportunity_stage/oppor_stages_initialize.html", context
                )
            return HttpResponse(
                """
                <script>
                    closeContentModal();
                    $('#reloadButton').click();
                     openContentModalSecond();
                        var div = document.createElement('div');
                        div.setAttribute('hx-get', '%s');
                        div.setAttribute('hx-target', '#contentModalBoxSecond');
                        div.setAttribute('hx-trigger', 'load');
                        div.setAttribute('hx-swap', 'innerHTML');
                        document.body.appendChild(div);
                        htmx.process(div);
                </script>
                """
                % reverse_lazy(
                    "opportunities:load_opp_stages", kwargs={"company_id": pk}
                ),
                headers={"X-Debug": "Modal transition in progress"},
            )

        except Exception as e:
            return HttpResponse(
                '<div class="alert alert-danger">An error occurred while creating stages. Please try again.</div>',
                status=500,
            )


BASE_STEPS.append({"step": 5, "title": "Lead Stages"})
BASE_STEPS.append({"step": 6, "title": "Opportunity Stages"})


class InitializeDatabaseLeadStages(View, ProgressStepsMixin):
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
