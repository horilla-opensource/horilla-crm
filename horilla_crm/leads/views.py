"""Views for Lead model."""

from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render  # type: ignore
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_crm.accounts.models import Account
from horilla_crm.contacts.models import Contact, ContactAccountRelationship
from horilla_crm.leads.filters import LeadFilter
from horilla_crm.leads.forms import LeadConversionForm, LeadFormClass  # type: ignore
from horilla_crm.leads.models import Lead, LeadStatus
from horilla_crm.opportunities.models import (
    Opportunity,
    OpportunityContactRole,
    OpportunityStage,
)
from horilla_generics.mixins import RecentlyViewedMixin  # type: ignore
from horilla_generics.views import (
    HorillaActivitySectionView,
    HorillaDetailSectionView,
    HorillaDetailTabView,
    HorillaDetailView,
    HorillaHistorySectionView,
    HorillaKanbanView,
    HorillaListView,
    HorillaMultiStepFormView,
    HorillaNavView,
    HorillaNotesAttachementSectionView,
    HorillaRelatedListSectionView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_utils.middlewares import _thread_local


class LeadView(LoginRequiredMixin, HorillaView):
    """
    Render the lead page.
    """

    nav_url = reverse_lazy("leads:leads_nav")
    list_url = reverse_lazy("leads:leads_list")
    kanban_url = reverse_lazy("leads:leads_kanban")

    def dispatch(self, request, *args, **kwargs):
        view_type = request.GET.get("view_type")
        if view_type == "converted_lead" and request.GET.get("kanban") == "true":
            get_params = request.GET.copy()
            del get_params["kanban"]
            query_string = get_params.urlencode()
            redirect_url = request.path
            if query_string:
                redirect_url += f"?{query_string}"

            return HttpResponseRedirect(redirect_url)

        return super().dispatch(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required(["leads.view_lead", "leads.view_own_lead"]), name="dispatch"
)
class LeadNavbar(LoginRequiredMixin, HorillaNavView):
    """Lead Navbar"""

    nav_title = Lead._meta.verbose_name_plural
    search_url = reverse_lazy("leads:leads_list")
    main_url = reverse_lazy("leads:leads_view")
    filterset_class = LeadFilter
    kanban_url = reverse_lazy("leads:leads_kanban")
    model_name = "Lead"
    model_app_label = "leads"
    exclude_kanban_fields = "lead_owner"
    enable_actions = True

    @cached_property
    def custom_view_type(self):
        """Custom view type for lead"""
        custom_view_type = {
            "converted_lead": {"name": "Converted Lead", "show_list_only": True},
        }
        return custom_view_type

    @cached_property
    def new_button(self):
        """New button for lead"""
        if self.request.user.has_perm("leads.add_lead"):
            return {
                "url": f"""{ reverse_lazy('leads:leads_create')}?new=true""",
                "attrs": {"id": "lead-create"},
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadListView(LoginRequiredMixin, HorillaListView):
    """
    Lead List view
    """

    model = Lead
    view_id = "Lead_List"
    filterset_class = LeadFilter
    search_url = reverse_lazy("leads:leads_list")
    main_url = reverse_lazy("leads:leads_view")
    max_visible_actions = 4
    bulk_update_fields = [
        "annual_revenue",
        "no_of_employees",
        "lead_source",
        "lead_owner",
        "industry",
        "lead_status",
    ]
    header_attrs = [
        {"email": {"style": "width: 300px;"}, "title": {"style": "width: 200px;"}},
    ]

    @cached_property
    def col_attrs(self):
        """Column attributes for lead"""
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        attrs = {}
        if self.request.user.has_perm("leads.view_lead") or self.request.user.has_perm(
            "leads.view_own_lead"
        ):
            attrs = {
                "hx-get": f"{{get_detail_url}}?{query_string}",
                "hx-target": "#mainContent",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "hx-select": "#mainContent",
                "class": "hover:text-primary-600",
                "style": "cursor:pointer",
            }
        return [
            {
                "title": {
                    **attrs,
                }
            }
        ]

    def no_record_add_button(self):
        """No record add button for lead"""
        if self.request.user.has_perm("leads.add_lead"):
            return {
                "url": f"""{ reverse_lazy('leads:leads_create')}?new=true""",
                "attrs": 'id="lead-create"',
            }

    @cached_property
    def columns(self):
        """Columns for lead"""
        instance = self.model()
        return [
            (instance._meta.get_field("title").verbose_name, "title"),
            (instance._meta.get_field("first_name").verbose_name, "first_name"),
            (instance._meta.get_field("email").verbose_name, "email"),
            (
                instance._meta.get_field("lead_source").verbose_name,
                "get_lead_source_display",
            ),
            (instance._meta.get_field("industry").verbose_name, "get_industry_display"),
            (instance._meta.get_field("annual_revenue").verbose_name, "annual_revenue"),
        ]

    @cached_property
    def actions(self):
        """
        Return actions if user is superuser, has global perms, or owns any lead in the queryset.
        Actions are shown globally (for all rows) but backend views enforce ownership/perms.
        """
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("leads.change_lead")
            or self.get_queryset().filter(lead_owner=self.request.user).exists()
        )
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)

        if show_actions:
            actions.extend(
                [
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
                    {
                        "action": "Change Owner",
                        "src": "assets/icons/a2.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                            hx-get="{get_change_owner_url}"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
                    },
                    {
                        "action": "Convert",
                        "src": "assets/icons/a3.svg",
                        "img_class": "w-4 h-4",
                        "attrs": f"""
                            hx-get="{{get_lead_convert_url}}?{query_string}"
                            hx-target="#contentModalBox"
                            hx-swap="innerHTML"
                            onclick="openContentModal()"
                            """,
                    },
                ]
            )

            if self.request.user.has_perm("leads.delete_lead"):
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

    def get_queryset(self):
        queryset = super().get_queryset()
        view_type = self.request.GET.get("view_type") or self.get_default_view_type()
        if view_type == "converted_lead":
            queryset = queryset.filter(is_convert=True)
            self.actions = None
            self.no_record_add_button = False
            self.no_record_msg = "Not found coverted leads"
            self.bulk_update_option = False
        else:
            queryset = queryset.filter(is_convert=False)
        return queryset


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("leads.delete_lead"), name="dispatch")
class LeadDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Lead Delete View"""

    model = Lead

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadKanbanView(LoginRequiredMixin, HorillaKanbanView):
    """
    Lead Kanban view
    """

    model = Lead
    view_id = "Lead_Kanban"
    filterset_class = LeadFilter
    search_url = reverse_lazy("leads:leads_list")
    main_url = reverse_lazy("leads:leads_view")
    group_by_field = "industry"

    @cached_property
    def actions(self):
        """
        Return actions if user is superuser, has global perms, or owns any lead in the queryset.
        Actions are shown globally (for all rows) but backend views enforce ownership/perms.
        """
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("leads.change_lead")
            or self.get_queryset().filter(lead_owner=self.request.user).exists()
        )

        if show_actions:
            actions.extend(
                [
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
                    {
                        "action": "Change Owner",
                        "src": "assets/icons/a2.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                            hx-get="{get_change_owner_url}"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
                    },
                    {
                        "action": "Convert",
                        "src": "assets/icons/a3.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                            hx-get="{get_lead_convert_url}"
                            hx-target="#contentModalBox"
                            hx-swap="innerHTML"
                            onclick="openContentModal()"
                            """,
                    },
                ]
            )

            if self.request.user.has_perm("leads.delete_lead"):
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

    @cached_property
    def kanban_attrs(self):
        """Kanban attributes for lead"""
        query_params = self.request.GET.dict()
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        if self.request.user.has_perm("leads.view_lead") or self.request.user.has_perm(
            "leads.view_own_lead"
        ):
            return f""""
                    hx-get="{{get_detail_url}}?{query_string}"
                    hx-target="#mainContent"
                    hx-swap="outerHTML"
                    hx-push-url="true"
                    hx-select="#mainContent"
                    style ="cursor:pointer",

            """

    @cached_property
    def columns(self):
        """Columns for lead"""
        instance = self.model()
        return [
            (instance._meta.get_field("title").verbose_name, "title"),
            (instance._meta.get_field("first_name").verbose_name, "first_name"),
            (instance._meta.get_field("email").verbose_name, "email"),
            (instance._meta.get_field("lead_source").verbose_name, "lead_source"),
            (instance._meta.get_field("industry").verbose_name, "industry"),
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group_by = self.get_group_by_field()

        if group_by == "lead_status" and "grouped_items" in context:
            filtered_grouped_items = {}
            num_columns = 0

            for key, group_data in context["grouped_items"].items():
                is_final_stage = False
                if key is not None:
                    try:
                        lead_status = LeadStatus.objects.get(pk=key)
                        is_final_stage = lead_status.is_final
                    except LeadStatus.DoesNotExist:
                        pass

                if not is_final_stage:
                    filtered_grouped_items[key] = group_data
                    num_columns += 1

            context["grouped_items"] = filtered_grouped_items
            context["num_columns"] = num_columns

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        view_type = self.request.GET.get("view_type") or self.get_default_view_type()
        if view_type == "converted_lead":
            queryset = queryset.filter(is_convert=True)
            self.actions = None
        else:
            queryset = queryset.filter(is_convert=False)
        return queryset


@method_decorator(htmx_required, name="dispatch")
class LeadFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    """Lead Create/Update View"""

    form_class = LeadFormClass
    model = Lead
    fullwidth_fields = ["requirements"]
    dynamic_create_fields = ["lead_status"]
    dynamic_create_field_mapping = {
        "lead_status": {
            "fields": ["name", "order", "color", "probability"],
            "full_width_fields": ["name"],
        },
    }

    @cached_property
    def form_url(self):
        """Form URL for lead"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("leads:leads_edit", kwargs={"pk": pk})
        return reverse_lazy("leads:leads_create")

    step_titles = {
        "1": "Basic Information",
        "2": "Company Details",
        "3": "Location",
        "4": "Requirements",
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get(self, request, *args, **kwargs):
        lead_id = self.kwargs.get("pk")
        if request.user.has_perm("leads.change_lead") or request.user.has_perm(
            "leads.add_lead"
        ):
            return super().get(request, *args, **kwargs)

        if lead_id:
            lead = get_object_or_404(Lead, pk=lead_id)
            if lead.lead_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadDetailView(RecentlyViewedMixin, LoginRequiredMixin, HorillaDetailView):
    """Lead Detail View"""

    model = Lead
    body = [
        "title",
        "first_name",
        "last_name",
        "email",
        "lead_source",
        "industry",
        "lead_owner",
    ]
    excluded_fields = [
        "id",
        "created_at",
        "additional_info",
        "updated_at",
        "history",
        "is_active",
    ]
    pipeline_field = "lead_status"
    tab_url = reverse_lazy("leads:lead_detail_view_tabs")

    @cached_property
    def final_stage_action(self):
        """Final stage action for lead"""
        return {
            "hx-get": reverse_lazy("leads:convert_lead", kwargs={"pk": self.object.pk}),
            "hx-target": "#contentModalBox",
            "hx-swap": "innerHTML",
            "hx-on:click": "openContentModal();",
        }

    @cached_property
    def actions(self):
        """
        Return actions if user is superuser, has global perms, or owns any lead in the queryset.
        Actions are shown globally (for all rows) but backend views enforce ownership/perms.
        """
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("leads.change_lead")
            or self.get_queryset().filter(lead_owner=self.request.user).exists()
        )

        if show_actions:
            actions.extend(
                [
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
                    {
                        "action": "Change Owner",
                        "src": "assets/icons/a2.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                            hx-get="{get_change_owner_url}"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
                    },
                ]
            )

            if self.request.user.has_perm("leads.delete_lead"):
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

    def get_context_data(self, **kwargs):
        obj = self.get_object()
        context = super().get_context_data(**kwargs)
        if obj.is_convert:
            self.pipeline_field = None
            self.actions = None
            context["pipeline_field"] = self.pipeline_field
            context["actions"] = self.actions
        return context

    def get(self, request, *args, **kwargs):
        if not self.model.objects.filter(
            lead_owner_id=self.request.user, pk=self.kwargs["pk"]
        ).first() and not self.request.user.has_perm("leads.view_lead"):
            return render(self.request, "error/403.html")
        return super().get(request, *args, **kwargs)


@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadsDetailTab(LoginRequiredMixin, HorillaDetailSectionView):
    """Lead Detail Tab View"""

    model = Lead

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.excluded_fields.append("lead_status")
        self.excluded_fields.append("is_convert")
        self.excluded_fields.append("lead_owner")
        self.excluded_fields.append("email_message_id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        if obj.is_convert:
            self.edit_field = False
            context["edit_field"] = self.edit_field
        return context

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        user = request.user

        is_owner = Lead.objects.filter(lead_owner_id=user, pk=pk).exists()
        has_permission = user.has_perm("leads.view_lead")

        if not (is_owner or has_permission):
            return render(request, "error/403.html", status=403)

        return super().get(request, *args, **kwargs)


@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadsNotesAndAttachments(LoginRequiredMixin, HorillaNotesAttachementSectionView):
    """Notes and Attachments Tab View"""

    model = Lead


@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadsDetailViewTabView(LoginRequiredMixin, HorillaDetailTabView):
    """Lead Detail Tab View"""

    def __init__(self, **kwargs):
        request = getattr(_thread_local, "request", None)
        self.request = request
        self.object_id = self.request.GET.get("object_id")
        if self.object_id:
            obj = Lead.objects.get(pk=self.object_id)
            if obj.is_convert:
                self.urls = {
                    "details": "leads:leads_details_tab",
                    "history": "leads:leads_history_tab_view",
                }
            else:
                self.urls = {
                    "details": "leads:leads_details_tab",
                    "activity": "leads:lead_activity_detail_view",
                    "related_lists": "leads:lead_related_lists",
                    "notes_attachments": "leads:leads_notes_attachments",
                    "history": "leads:leads_history_tab_view",
                }
        super().__init__(**kwargs)

    def get(self, request, *args, **kwargs):
        user = request.user
        lead_id = self.object_id

        is_owner = Lead.objects.filter(lead_owner_id=user, pk=lead_id).exists()
        has_permission = user.has_perm("leads.view_lead") or user.has_perm(
            "leads.view_own_lead"
        )

        if not (is_owner or has_permission):
            return render(request, "error/403.html", status=403)

        return super().get(request, *args, **kwargs)


@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadsActivityTabView(LoginRequiredMixin, HorillaActivitySectionView):
    """
    Activity Tab View
    """

    model = Lead


@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadsHistoryTabView(LoginRequiredMixin, HorillaHistorySectionView):
    """
    History Tab View
    """

    model = Lead


@method_decorator(
    permission_required_or_denied(["leads.view_lead", "leads.view_own_lead"]),
    name="dispatch",
)
class LeadRelatedLists(LoginRequiredMixin, HorillaRelatedListSectionView):
    """Related Lists Tab View"""

    model = Lead

    @cached_property
    def related_list_config(self):
        """Related list config for lead"""
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        pk = self.request.GET.get("object_id")
        referrer_url = "leads_detail"
        col_attrs = []
        if self.request.user.has_perm("campaigns.view_campaign"):
            col_attrs = [
                {
                    "campaign_name": {
                        "style": "cursor:pointer",
                        "class": "hover:text-primary-600",
                        "hx-get": (
                            f"{{get_detail_view_url}}?referrer_app={self.model._meta.app_label}"
                            f"&referrer_model={self.model._meta.model_name}"
                            f"&referrer_id={pk}&referrer_url={referrer_url}&{query_string}"
                        ),
                        "hx-target": "#mainContent",
                        "hx-swap": "outerHTML",
                        "hx-push-url": "true",
                        "hx-select": "#mainContent",
                    }
                }
            ]
        return {
            "custom_related_lists": {
                "campaigns": {
                    "app_label": "campaigns",
                    "model_name": "Campaign",
                    "intermediate_model": "CampaignMember",
                    "intermediate_field": "members",
                    "related_field": "lead",
                    "config": {
                        "title": Lead._meta.get_field("lead_campaign_members")
                        .related_model._meta.get_field("campaign")
                        .related_model._meta.verbose_name_plural,
                        "columns": [
                            (
                                Lead._meta.get_field("lead_campaign_members")
                                .related_model._meta.get_field("campaign")
                                .related_model._meta.get_field("campaign_name")
                                .verbose_name,
                                "campaign_name",
                            ),
                            (
                                Lead._meta.get_field("lead_campaign_members")
                                .related_model._meta.get_field("campaign")
                                .related_model._meta.get_field("status")
                                .verbose_name,
                                "get_status_display",
                            ),
                            (
                                Lead._meta.get_field("lead_campaign_members")
                                .related_model._meta.get_field("campaign")
                                .related_model._meta.get_field("start_date")
                                .verbose_name,
                                "start_date",
                            ),
                            (
                                Lead._meta.get_field("lead_campaign_members")
                                .related_model._meta.get_field("member_status")
                                .verbose_name,
                                "members__get_member_status_display",
                            ),
                        ],
                        "can_add": True,
                        "add_url": reverse_lazy("campaigns:add_to_campaign"),
                        "actions": [
                            {
                                "action": "edit",
                                "src": "/assets/icons/edit.svg",
                                "img_class": "w-4 h-4",
                                "attrs": """
                                    hx-get="{get_specific_member_edit_url}"
                                    hx-target="#modalBox"
                                    hx-swap="innerHTML"
                                    onclick="event.stopPropagation();openModal()"
                                    hx-indicator="#modalBox"
                                    """,
                            },
                        ],
                        "col_attrs": col_attrs,
                    },
                },
            },
        }

    excluded_related_lists = ["lead_campaign_members"]


@method_decorator(htmx_required, name="dispatch")
class LeadsSingleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """Lead Create/Update Single Page View"""

    model = Lead
    exclude = ["additional_info"]
    full_width_fields = ["requirements"]
    dynamic_create_fields = ["lead_status"]
    dynamic_create_field_mapping = {
        "lead_status": {
            "fields": ["name", "order", "color"],
            "full_width_fields": ["name"],
        },
    }

    @cached_property
    def form_url(self):
        """Form URL for lead"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("leads:leads_edit_single", kwargs={"pk": pk})
        return reverse_lazy("leads:leads_create_single")

    def get(self, request, *args, **kwargs):
        lead_id = self.kwargs.get("pk")
        if request.user.has_perm("leads.change_lead") or request.user.has_perm(
            "leads.add_lead"
        ):
            return super().get(request, *args, **kwargs)

        if lead_id:
            try:
                lead = get_object_or_404(Lead, pk=lead_id)
            except Http404:
                messages.error(self.request, "Lead not found.")
                return HttpResponse(
                    "<script>$('#reloadButton').click();closeModal();</script>"
                )
            if lead.lead_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
class LeadChangeOwnerForm(LoginRequiredMixin, HorillaSingleFormView):
    """
    change owner form for lead
    """

    model = Lead
    fields = ["lead_owner"]
    full_width_fields = ["lead_owner"]
    modal_height = False
    form_title = _("Change Owner")

    @cached_property
    def form_url(self):
        """Form URL for lead change owner"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("leads:lead_change_owner", kwargs={"pk": pk})

    def get(self, request, *args, **kwargs):
        lead_id = self.kwargs.get("pk")
        if request.user.has_perm("leads.change_lead") or request.user.has_perm(
            "leads.add_lead"
        ):
            return super().get(request, *args, **kwargs)

        if lead_id:
            try:
                lead = get_object_or_404(Lead, pk=lead_id)
            except Http404:
                messages.error(self.request, "Lead not found.")
                return HttpResponse(
                    "<script>$('#reloadButton').click();closeModal();</script>"
                )
            if lead.lead_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
class LeadConversionView(LoginRequiredMixin, FormView):
    """View to handle lead conversion to account, contact, and opportunity."""

    template_name = "lead_convert.html"
    form_class = LeadConversionForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.lead = Lead.objects.get(pk=self.kwargs["pk"])
        except Lead.DoesNotExist:
            messages.error(self.request, "Lead not found.")
            return HttpResponse(
                "<script>$('#reloadButton').click();closeModal();</script>"
            )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("leads:leads_detail", kwargs={"pk": self.lead.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["lead"] = self.lead

        # Get selected account for filtering opportunities
        selected_account_id = self.request.GET.get("existing_account")
        if selected_account_id:
            try:
                kwargs["selected_account"] = Account.objects.get(pk=selected_account_id)
            except Account.DoesNotExist:
                pass

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lead"] = self.lead
        context["account_action"] = self.request.GET.get(
            "account_action", self.get_initial().get("account_action", "create_new")
        )
        context["contact_action"] = self.request.GET.get(
            "contact_action", self.get_initial().get("contact_action", "create_new")
        )
        context["opportunity_action"] = self.request.GET.get(
            "opportunity_action",
            self.get_initial().get("opportunity_action", "create_new"),
        )
        context["selected_account_id"] = self.request.GET.get("existing_account")
        return context

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        if pk:
            try:
                lead = get_object_or_404(Lead, pk=pk)
            except Http404:
                messages.error(request, "Lead not found or no longer exists.")
                return HttpResponse(
                    "<script>$('#reloadButton').click();closeModal();</script>"
                )

            if lead.lead_owner != request.user and not request.user.has_perm(
                "leads.change_lead"
            ):
                return render(request, "error/403.html")

        if "HTTP_HX_REQUEST" in request.META:
            hx_target = request.META.get("HTTP_HX_TARGET", "").replace("#", "")

            if "existing_account" in request.GET and hx_target == "opportunity-field":
                context = self.get_context_data()
                return render(request, "lead_convert_opportunity.html", context)

            if hx_target:
                action = request.GET.get(f"{hx_target}_action", "create_new")
                context = self.get_context_data()
                context[f"{hx_target}_action"] = action
                if hx_target == "account-field":
                    return render(request, "lead_convert_account.html", context)
                elif hx_target == "contact-field":
                    return render(request, "lead_convert_contact.html", context)
                elif hx_target == "opportunity-field":
                    return render(request, "lead_convert_opportunity.html", context)

        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            try:
                lead_status = LeadStatus.objects.filter(is_final=True).first()
                company = getattr(self.request, "active_company", None)
                account = self._process_account(form, company)
                contact = self._process_contact(form, account, company)
                opportunity = self._process_opportunity(form, account, contact, company)

                # Update only the Lead's conversion status
                self.lead.is_convert = True
                self.lead.updated_at = timezone.now()
                self.lead.lead_status = lead_status
                self.lead.save()

                messages.success(
                    self.request,
                    f'Lead "{self.lead.title}" has been successfully converted!',
                )
                self.conversion_data = {
                    "account": account,
                    "contact": contact,
                    "opportunity": opportunity,
                    "lead": self.lead,
                }
            except Exception as e:
                messages.error(self.request, f"Error converting lead: {str(e)}")
                return self.form_invalid(form)

        response = super().form_valid(form)
        if "HTTP_HX_REQUEST" in self.request.META:
            return self._render_success_modal()
        return response

    def _render_success_modal(self):
        """Render the success modal with conversion data"""
        context = {
            "account": self.conversion_data["account"],
            "contact": self.conversion_data["contact"],
            "opportunity": self.conversion_data["opportunity"],
            "lead": self.conversion_data["lead"],
        }
        return render(self.request, "lead_convert_success_modal.html", context)

    def _process_account(self, form, company):
        if form.cleaned_data["account_action"] == "create_new":
            return Account.objects.create(
                name=form.cleaned_data["account_name"],
                account_owner=form.cleaned_data.get("owner"),
                phone=self.lead.contact_number,
                annual_revenue=self.lead.annual_revenue,
                industry=self.lead.industry,
                number_of_employees=self.lead.no_of_employees,
                fax=self.lead.fax,
                account_source=self.lead.lead_source,
                company=company,
            )
        return form.cleaned_data["existing_account"]

    def _process_contact(self, form, account, company):
        if form.cleaned_data["contact_action"] == "create_new":
            contact = Contact.objects.create(
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=self.lead.email,
                phone=self.lead.contact_number,
                contact_owner=form.cleaned_data.get("owner"),
                company=company,
            )
            ContactAccountRelationship.objects.get_or_create(
                contact=contact, account=account, company=company
            )
            return contact
        contact = form.cleaned_data["existing_contact"]
        relationship, created = ContactAccountRelationship.objects.get_or_create(
            contact=contact, defaults={"account": account}, company=company
        )
        if not created and relationship.account != account:
            relationship.account = account
            relationship.save()
        return contact

    def _process_opportunity(self, form, account, contact, company):
        if form.cleaned_data["opportunity_action"] == "create_new":
            first_stage = OpportunityStage.objects.filter(order=1).first()
            campaign_member = self.lead.lead_campaign_members.first()
            closed_date = timezone.now().date() + relativedelta(months=1)
            opportunity = Opportunity.objects.create(
                name=form.cleaned_data["opportunity_name"],
                account=account,
                owner=self.lead.lead_owner,
                stage=first_stage,
                primary_campaign_source=(
                    campaign_member.campaign if campaign_member else None
                ),
                close_date=closed_date,
                company=company,
            )
            OpportunityContactRole.objects.get_or_create(
                opportunity=opportunity,
                contact=contact,
                defaults={"is_primary": True},
                company=company,
            )
            return opportunity
        opportunity = form.cleaned_data["existing_opportunity"]
        if opportunity.account != account:
            opportunity.account = account
        role, created = OpportunityContactRole.objects.get_or_create(
            opportunity=opportunity,
            contact=contact,
            defaults={"is_primary": True},
            company=company,
        )
        if not created and role.contact != contact:
            role.contact = contact
            role.save()
        opportunity.save()
        return opportunity

    def get_initial(self):
        return {
            "account_action": "create_new",
            "contact_action": "create_new",
            "opportunity_action": "create_new",
        }

    def form_invalid(self, form):
        if "HTTP_HX_REQUEST" in self.request.META:
            # Re-render the entire form with errors for HTMX requests
            context = self.get_context_data(form=form)
            return render(self.request, self.template_name, context)
        return super().form_invalid(form)
