from urllib.parse import urlencode

from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_crm.contacts.models import ContactAccountRelationship
from horilla_crm.opportunities.filters import OpportunityFilter
from horilla_crm.opportunities.forms import OpportunityFormClass
from horilla_crm.opportunities.models import (
    Opportunity,
    OpportunityContactRole,
    OpportunitySettings,
)
from horilla_crm.opportunities.signals import set_opportunity_contact_id
from horilla_generics.mixins import RecentlyViewedMixin
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


class OpportunityView(LoginRequiredMixin, HorillaView):
    """
    Render the lead page.
    """

    nav_url = reverse_lazy("opportunities:opportunities_nav")
    list_url = reverse_lazy("opportunities:opportunities_list")
    kanban_url = reverse_lazy("opportunities:opportunities_kanban")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityNavbar(LoginRequiredMixin, HorillaNavView):

    nav_title = Opportunity._meta.verbose_name_plural
    search_url = reverse_lazy("opportunities:opportunities_list")
    main_url = reverse_lazy("opportunities:opportunities_view")
    filterset_class = OpportunityFilter
    kanban_url = reverse_lazy("opportunities:opportunities_kanban")
    model_name = "Opportunity"
    model_app_label = "opportunities"
    exclude_kanban_fields = "owner"
    enable_actions = True

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("opportunities.add_opportunity"):
            return {
                "url": f"""{reverse_lazy("opportunities:opportunity_create")}?new=true""",
                "attrs": {"id": "opportunity-create"},
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityListView(LoginRequiredMixin, HorillaListView):
    """
    Opportunity List view
    """

    model = Opportunity
    view_id = "opportunity-container"
    filterset_class = OpportunityFilter
    search_url = reverse_lazy("opportunities:opportunities_list")
    main_url = reverse_lazy("opportunities:opportunities_view")
    bulk_update_fields = ["owner", "opportunity_type", "lead_source"]
    header_attrs = [
        {"email": {"style": "width: 300px;"}, "title": {"style": "width: 200px;"}},
    ]

    @cached_property
    def col_attrs(self):
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        attrs = {}
        if self.request.user.has_perm(
            "opportunities.view_opportunity"
        ) or self.request.user.has_perm("opportunities.view_own_opportunity"):
            attrs = {
                "hx-get": f"{{get_detail_url}}?{query_string}",
                "hx-target": "#mainContent",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "hx-select": "#mainContent",
                "style": "cursor:pointer",
                "class": "hover:text-primary-600",
            }
        return [
            {
                "name": {
                    **attrs,
                }
            }
        ]

    def no_record_add_button(self):
        if self.request.user.has_perm("opportunities.add_opportunity"):
            return {
                "url": f"""{ reverse_lazy('opportunities:opportunity_create')}?new=true""",
                "attrs": 'id="opportunity-create"',
            }

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("name").verbose_name, "name"),
            (instance._meta.get_field("amount").verbose_name, "amount"),
            (instance._meta.get_field("close_date").verbose_name, "close_date"),
            (instance._meta.get_field("stage").verbose_name, "stage"),
            (
                instance._meta.get_field("opportunity_type").verbose_name,
                "get_opportunity_type_display",
            ),
            (
                instance._meta.get_field("primary_campaign_source").verbose_name,
                "primary_campaign_source__campaign_name",
            ),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("opportunities.change_opportunity")
            or self.get_queryset().filter(owner=self.request.user).exists()
        )

        if show_actions:
            actions.extend(
                [
                    {
                        "action": _("Edit"),
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
                        "action": _("Change Owner"),
                        "src": "assets/icons/a2.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                        hx-get="{get_change_owner_url}?new=true"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
                    },
                ]
            )
            if self.request.user.has_perm("opportunities.delete_opportunity"):
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
    permission_required_or_denied("opportunities.delete_opportunity"), name="dispatch"
)
class OpportunityDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = Opportunity

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityKanbanView(LoginRequiredMixin, HorillaKanbanView):
    """
    Lead Kanban view
    """

    model = Opportunity
    view_id = "opportunity-kanban"
    filterset_class = OpportunityFilter
    search_url = reverse_lazy("opportunities:opportunities_list")
    main_url = reverse_lazy("opportunities:opportunities_view")
    group_by_field = "stage"

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("opportunities.change_opportunity")
            or self.get_queryset().filter(owner=self.request.user).exists()
        )

        if show_actions:
            actions.extend(
                [
                    {
                        "action": _("Edit"),
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
                        "action": _("Change Owner"),
                        "src": "assets/icons/a2.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                        hx-get="{get_change_owner_url}?new=true"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
                    },
                ]
            )
            if self.request.user.has_perm("opportunities.delete_opportunity"):
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
        query_params = self.request.GET.dict()
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        if self.request.user.has_perm(
            "opportunities.view_opportunity"
        ) or self.request.user.has_perm("opportunities.view_own_opportunity"):
            return f"""
                    hx-get="{{get_detail_url}}?{query_string}"
                    hx-target="#mainContent"
                    hx-swap="outerHTML"
                    hx-push-url="true"
                    hx-select="#mainContent"
                    style ="cursor:pointer",
                    """

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("name").verbose_name, "name"),
            (instance._meta.get_field("amount").verbose_name, "amount"),
            (instance._meta.get_field("owner").verbose_name, "owner"),
            (instance._meta.get_field("close_date").verbose_name, "close_date"),
            (
                instance._meta.get_field("expected_revenue").verbose_name,
                "expected_revenue",
            ),
        ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("opportunities.add_opportunity"), name="dispatch"
)
class OpportunityMultiStepFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    form_class = OpportunityFormClass
    model = Opportunity
    total_steps = 3
    fullwidth_fields = ["description"]
    dynamic_create_fields = ["stage"]
    dynamic_create_field_mapping = {
        "stage": {"full_width_fields": ["description"]},
    }

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk")
        if pk:
            return reverse_lazy("opportunities:opportunity_edit", kwargs={"pk": pk})
        return reverse_lazy("opportunities:opportunity_create")

    step_titles = {
        "1": _("Opportunity Information"),
        "2": _("Additional Information"),
        "3": _("Description"),
    }

    def get_initial(self):
        initial = super().get_initial()
        account_id = self.request.GET.get("id")
        initial["account"] = account_id
        return initial

    def get(self, request, *args, **kwargs):
        opportunity_id = self.kwargs.get("pk")
        if request.user.has_perm(
            "opportunities.change_opportunity"
        ) or request.user.has_perm("opportunities.add_opportunity"):
            return super().get(request, *args, **kwargs)

        if opportunity_id:
            opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
            if opportunity.owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("opportunities.add_opportunity"), name="dispatch"
)
class RelatedOpportunityFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    form_class = OpportunityFormClass
    model = Opportunity
    total_steps = 3
    fullwidth_fields = ["description"]
    dynamic_create_fields = ["stage"]
    dynamic_create_field_mapping = {
        "stage": {"full_width_fields": ["description"]},
    }

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk")
        if pk:
            return reverse_lazy("opportunities:opportunity_edit", kwargs={"pk": pk})
        return reverse_lazy("opportunities:opportunity_create")

    step_titles = {
        "1": _("Opportunity Information"),
        "2": _("Additional Information"),
        "3": _("Description"),
    }

    def get_initial(self):
        initial = super().get_initial()
        contact_id = self.request.GET.get("id")

        if contact_id:
            Contact = apps.get_model("contacts", "Contact")
            contact = Contact.objects.filter(pk=contact_id).first()
            if contact:
                rel = contact.account_relationships.first()
                account_id = rel.account.pk if rel else None
        initial["account"] = account_id
        return initial

    def form_valid(self, form):
        step = self.get_initial_step()

        if step == self.total_steps:
            contact_id = self.request.GET.get("id")
            if contact_id:
                set_opportunity_contact_id(
                    contact_id=contact_id, company=self.request.active_company
                )
            response = super().form_valid(form)
            return HttpResponse(
                "<script>htmx.trigger('#tab-opportunities-btn','click');closeModal();</script>"
            )

        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        opportunity_id = self.kwargs.get("pk")
        if request.user.has_perm(
            "opportunities.change_opportunity"
        ) or request.user.has_perm("opportunities.add_opportunity"):
            return super().get(request, *args, **kwargs)

        if opportunity_id:
            opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
            if opportunity.owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
class OpportunityChangeOwnerForm(LoginRequiredMixin, HorillaSingleFormView):
    """
    Change owner form
    """

    model = Opportunity
    fields = ["owner"]
    full_width_fields = ["owner"]
    modal_height = False
    form_title = _("Change Owner")

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "opportunities:opportunity_change_owner", kwargs={"pk": pk}
            )

    def get(self, request, *args, **kwargs):
        opportunity_id = self.kwargs.get("pk")
        if request.user.has_perm(
            "opportunities.change_opportunity"
        ) or request.user.has_perm("opportunities.add_opportunity"):
            return super().get(request, *args, **kwargs)

        if opportunity_id:
            opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
            if opportunity.owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityDetailView(RecentlyViewedMixin, LoginRequiredMixin, HorillaDetailView):

    model = Opportunity
    pipeline_field = "stage"
    tab_url = reverse_lazy("opportunities:opportunity_detail_view_tabs")
    breadcrumbs = [
        ("Sales", "leads:leads_view"),
        ("Opportunites", "opportunities:opportunities_view"),
    ]

    body = [
        "name",
        "amount",
        "expected_revenue",
        "quantity",
        "close_date",
        "probability",
        "forecast_category",
    ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("opportunities.change_opportunity")
            or self.get_queryset().filter(owner=self.request.user).exists()
        )

        if show_actions:
            actions.extend(
                [
                    {
                        "action": _("Edit"),
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
                        "action": _("Change Owner"),
                        "src": "assets/icons/a2.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                        hx-get="{get_change_owner_url}?new=true"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
                    },
                ]
            )
            if self.request.user.has_perm("opportunities.delete_opportunity"):
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

    def get(self, request, *args, **kwargs):
        if not self.model.objects.filter(
            owner_id=self.request.user, pk=self.kwargs["pk"]
        ).first() and not self.request.user.has_perm("campaigns.view_campaign"):
            from django.shortcuts import render

            return render(self.request, "error/403.html")
        return super().get(request, *args, **kwargs)


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityDetailViewTabView(LoginRequiredMixin, HorillaDetailTabView):

    def __init__(self, **kwargs):
        request = getattr(_thread_local, "request", None)
        self.request = request
        self.object_id = self.request.GET.get("object_id")
        super().__init__(**kwargs)

    urls = {
        "details": "opportunities:opportunity_details_tab",
        "activity": "opportunities:opportunity_activity_detail_view",
        "related_lists": "opportunities:opportunity_related_lists",
        "notes_attachments": "opportunities:opportunity_notes_attachments",
        "history": "opportunities:opportunity_history_tab_view",
    }

    def get(self, request, *args, **kwargs):
        user = request.user
        opportunity_id = self.object_id

        is_owner = Opportunity.objects.filter(owner_id=user, pk=opportunity_id).exists()
        has_permission = user.has_perm(
            "opportunities.view_opportunity"
        ) or user.has_perm("opportunities.view_own_opportunities")
        if not (is_owner or has_permission):
            return render(request, "error/403.html", status=403)

        return super().get(request, *args, **kwargs)


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityDetailTab(LoginRequiredMixin, HorillaDetailSectionView):

    model = Opportunity
    non_editable_fields = ["expected_revenue"]
    excluded_fields = [
        "id",
        "created_at",
        "additional_info",
        "updated_at",
        "history",
        "is_active",
        "created_by",
        "updated_by",
        "company",
        "forecast_category",
    ]


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityActivityTabView(LoginRequiredMixin, HorillaActivitySectionView):
    """
    Activity Tab View
    """

    model = Opportunity


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunitiesNotesAndAttachments(
    LoginRequiredMixin, HorillaNotesAttachementSectionView
):

    model = Opportunity


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityHistoryTabView(LoginRequiredMixin, HorillaHistorySectionView):
    """
    History Tab View
    """

    model = Opportunity


@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class OpportunityRelatedLists(LoginRequiredMixin, HorillaRelatedListSectionView):

    model = Opportunity

    @cached_property
    def related_list_config(self):
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        pk = self.request.GET.get("object_id")
        referrer_url = "opportunity_detail_view"

        contact_col_attrs = []
        if self.request.user.has_perm("contacts.view_contact"):
            contact_col_attrs = [
                {
                    "first_name": {
                        "style": "cursor:pointer",
                        "class": "hover:text-primary-600",
                        "hx-get": f"{{get_detail_url}}?referrer_app={self.model._meta.app_label}&referrer_model={self.model._meta.model_name}&referrer_id={pk}&referrer_url={referrer_url}&{query_string}",
                        "hx-target": "#mainContent",
                        "hx-swap": "outerHTML",
                        "hx-push-url": "true",
                        "hx-select": "#mainContent",
                    }
                }
            ]

        config = {
            "custom_related_lists": {
                "contact": {
                    "app_label": "contacts",
                    "model_name": "Contact",
                    "intermediate_model": "OpportunityContactRole",
                    "intermediate_field": "opportunity_roles",
                    "related_field": "opportunity",
                    "config": {
                        "title": _("Contact Roles"),
                        "columns": [
                            (
                                self.model._meta.get_field("contact_roles")
                                .related_model._meta.get_field("contact")
                                .related_model._meta.get_field("first_name")
                                .verbose_name,
                                "first_name",
                            ),
                            (
                                self.model._meta.get_field("contact_roles")
                                .related_model._meta.get_field("contact")
                                .related_model._meta.get_field("last_name")
                                .verbose_name,
                                "last_name",
                            ),
                            (
                                self.model._meta.get_field("contact_roles")
                                .related_model._meta.get_field("role")
                                .verbose_name,
                                "opportunity_roles__role",
                            ),
                            (
                                self.model._meta.get_field("contact_roles")
                                .related_model._meta.get_field("is_primary")
                                .verbose_name,
                                "opportunity_roles__is_primary",
                            ),
                        ],
                        "can_add": True,
                        "add_url": reverse_lazy(
                            "opportunities:add_opportunity_contact_role"
                        ),
                        "actions": [
                            {
                                "action": "edit",
                                "src": "/assets/icons/edit.svg",
                                "img_class": "w-4 h-4",
                                "attrs": """
                                    hx-get="{get_opportunity_contact_role_edit_url}"
                                    hx-target="#modalBox"
                                    hx-swap="innerHTML"
                                    onclick="event.stopPropagation();openModal()"
                                    hx-indicator="#modalBox"
                                    """,
                            },
                            {
                                "action": "Delete",
                                "src": "assets/icons/a4.svg",
                                "img_class": "w-4 h-4",
                                "attrs": """
                                        hx-post="{get_opportunity_contact_role_delete_url}"
                                        hx-target="#deleteModeBox"
                                        hx-swap="innerHTML"
                                        hx-trigger="click"
                                        hx-vals='{{"check_dependencies": "true"}}'
                                        onclick="openDeleteModeModal()"
                                        """,
                            },
                        ],
                        "col_attrs": contact_col_attrs,
                    },
                },
            },
        }
        if OpportunitySettings.is_team_selling_enabled():
            config["opportunity_team_members"] = {
                "title": "Opportunity Team",
                "columns": [
                    (
                        self.model._meta.get_field("opportunity_team_members")
                        .related_model._meta.get_field("user")
                        .verbose_name,
                        "user",
                    ),
                    (
                        self.model._meta.get_field("opportunity_team_members")
                        .related_model._meta.get_field("team_role")
                        .verbose_name,
                        "get_team_role_display",
                    ),
                ],
                "can_add": False,
                "custom_buttons": [
                    {
                        "label": _("Add Team"),
                        "url": reverse_lazy("opportunities:add_default_team"),
                        "attrs": """
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            hx-indicator="#modalBox"
                        """,
                        "icon": "fa-solid fa-users",
                        "class": "text-xs px-4 py-1.5 bg-primary-600 rounded-md hover:bg-primary-800 transition duration-300 text-white",
                    },
                    {
                        "label": _("Add Members"),
                        "url": reverse_lazy("opportunities:add_opportunity_member"),
                        "attrs": """
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            hx-indicator="#modalBox"
                        """,
                        "icon": "fa-solid fa-user-plus",
                        "class": "text-xs px-4 py-1.5 bg-white border border-primary-600 text-primary-600 rounded-md hover:bg-primary-50 transition duration-300",
                    },
                ],
                "actions": [
                    {
                        "action": "Edit",
                        "src": "/assets/icons/edit.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                                    hx-get="{get_edit_url}"
                                    hx-target="#modalBox"
                                    hx-swap="innerHTML"
                                    onclick="event.stopPropagation();openModal()"
                                    hx-indicator="#modalBox"
                                    """,
                    },
                    {
                        "action": "Delete",
                        "src": "/assets/icons/a4.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                                    hx-post="{get_delete_url}"
                                    hx-target="#deleteModeBox"
                                    hx-swap="innerHTML"
                                    hx-trigger="click"
                                    hx-vals='{{"check_dependencies": "true"}}'
                                    onclick="openDeleteModeModal()"
                                    """,
                    },
                ],
            }
            if OpportunitySettings.is_split_enabled():
                config["splits"] = {
                    "title": _("Opportunity Splits"),
                    "columns": [
                        (
                            self.model._meta.get_field("splits")
                            .related_model._meta.get_field("user")
                            .verbose_name,
                            "user",
                        ),
                        (
                            self.model._meta.get_field("splits")
                            .related_model._meta.get_field("split_type")
                            .verbose_name,
                            "split_type",
                        ),
                        (
                            self.model._meta.get_field("splits")
                            .related_model._meta.get_field("split_percentage")
                            .verbose_name,
                            "split_percentage",
                        ),
                        (
                            self.model._meta.get_field("splits")
                            .related_model._meta.get_field("split_amount")
                            .verbose_name,
                            "split_amount",
                        ),
                    ],
                    "can_add": False,
                    "custom_buttons": [
                        {
                            "label": _("Manage Opportunity Splits"),
                            "url": reverse_lazy(
                                "opportunities:manage_opportunity_splits"
                            ),
                            "attrs": """
                                hx-target="#contentModalBox"
                                hx-swap="innerHTML"
                                onclick="openContentModal()"
                            """,
                            "class": "text-xs px-4 py-1.5 bg-primary-600 rounded-md hover:bg-primary-800 transition duration-300 text-white",
                        },
                    ],
                    "action_method": "actions",
                }

        return config

    def get_excluded_related_lists(self):
        """
        Dynamically determine which related lists to exclude based on settings
        """
        excluded = ["contact_roles"]

        # If Team Selling is DISABLED, exclude opportunity_team_members from showing
        if not OpportunitySettings.is_team_selling_enabled():
            excluded.append("opportunity_team_members")
        if not OpportunitySettings.is_split_enabled():
            excluded.append("splits")

        return excluded

    @property
    def excluded_related_lists(self):
        """Property wrapper for excluded_related_lists"""
        return self.get_excluded_related_lists()

    @excluded_related_lists.setter
    def excluded_related_lists(self, value):
        """Setter to allow parent view to set the value (but we ignore it)"""
        # We ignore the setter since we calculate dynamically
        pass


@method_decorator(htmx_required, name="dispatch")
class OpportunityContactRoleFormview(LoginRequiredMixin, HorillaSingleFormView):

    model = OpportunityContactRole
    fields = ["is_primary", "role", "contact", "opportunity"]
    full_width_fields = ["is_primary", "role", "contact"]
    modal_height = False
    form_title = _("Add Contact Role")
    hidden_fields = ["opportunity"]

    def form_valid(self, form):
        super().form_valid(form)

        opportunity_contact_role = form.instance
        contact = opportunity_contact_role.contact
        opportunity = opportunity_contact_role.opportunity
        role = opportunity_contact_role.role

        # Automatically create related ContactAccountRelationship
        if opportunity.account:
            ContactAccountRelationship.objects.get_or_create(
                contact=contact,
                account=opportunity.account,
                defaults={"role": role},
                company=self.request.active_company,
            )

        return HttpResponse(
            "<script>htmx.trigger('#tab-contact-btn', 'click');closeModal();</script>"
        )

    def get_initial(self):
        initial = super().get_initial()
        id = self.request.GET.get("id")
        if id:
            initial["opportunity"] = id
        return initial

    @cached_property
    def form_url(self):
        if self.kwargs.get("pk"):
            return reverse_lazy(
                "opportunities:edit_opportunity_contact_role",
                kwargs={"pk": self.kwargs.get("pk")},
            )
        return reverse_lazy("opportunities:add_opportunity_contact_role")

    def get(self, request, *args, **kwargs):

        opportunity_id = request.GET.get("id")
        if request.user.has_perm(
            "opportunities.change_opportunitycontactrole"
        ) or request.user.has_perm("opportunities.add_opportunitycontactrole"):
            return super().get(request, *args, **kwargs)

        if opportunity_id:
            opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
            if opportunity.owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required("accounts.delete_opportunitycontactrole"), name="dispatch"
)
class OpportunityContactRoleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """
    Delete view for Opportunity Contact Role
    """

    model = OpportunityContactRole

    def get_post_delete_response(self):
        return HttpResponse(
            "<script>htmx.trigger('#tab-contact-btn','click');</script>"
        )
