"""
Handles campaign-related views, including list, create, update, and delete operations.
"""

import logging
from functools import cached_property
from urllib.parse import urlencode

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, View

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_crm.campaigns.filters import CampaignFilter
from horilla_crm.campaigns.forms import (
    CampaignFormClass,
    CampaignMemberForm,
    ChildCampaignForm,
)
from horilla_crm.campaigns.models import Campaign, CampaignMember
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

logger = logging.getLogger(__name__)


class CampaignView(LoginRequiredMixin, HorillaView):
    """
    Render the campaign page
    """

    nav_url = reverse_lazy("campaigns:campaign_nav_view")
    list_url = reverse_lazy("campaigns:campaign_list_view")
    kanban_url = reverse_lazy("campaigns:campaign_kanban_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required(["campaigns.view_campaign", "campaigns.view_own_campaign"]),
    name="dispatch",
)
class CampaignNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar View for Campaign page
    """

    nav_title = Campaign._meta.verbose_name_plural
    search_url = reverse_lazy("campaigns:campaign_list_view")
    main_url = reverse_lazy("campaigns:campaign_view")
    kanban_url = reverse_lazy("campaigns:campaign_kanban_view")
    model_str = "campaigns.Campaign"
    model_name = "Campaign"
    model_app_label = "campaigns"
    filterset_class = CampaignFilter
    exclude_kanban_fields = "company"
    enable_actions = True

    @cached_property
    def new_button(self):
        """
        Function to return new button configuration
        """
        if self.request.user.has_perm("campaigns:add_campaign"):
            return {
                "url": f"""{ reverse_lazy('campaigns:campaign_create')}?new=true""",
                "attrs": {"id": "campaign-create"},
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignListView(LoginRequiredMixin, HorillaListView):
    """
    Campaign List view
    """

    model = Campaign
    paginate_by = 20
    view_id = "Campaign_List"
    filterset_class = CampaignFilter
    search_url = reverse_lazy("campaigns:campaign_list_view")
    main_url = reverse_lazy("campaigns:campaign_view")

    @cached_property
    def columns(self):
        """
        Function to return columns for the list view
        """
        instance = self.model()
        return [
            (instance._meta.get_field("campaign_name").verbose_name, "campaign_name"),
            (
                instance._meta.get_field("campaign_type").verbose_name,
                "get_campaign_type_display",
            ),
            (instance._meta.get_field("campaign_owner").verbose_name, "campaign_owner"),
            (instance._meta.get_field("status").verbose_name, "get_status_display"),
            (
                instance._meta.get_field("expected_revenue").verbose_name,
                "expected_revenue",
            ),
            (instance._meta.get_field("budget_cost").verbose_name, "budget_cost"),
        ]

    @cached_property
    def col_attrs(self):
        """
        Function to return attributes for columns in the list view
        """
        query_params = self.request.GET.dict()
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        attrs = {}
        if self.request.user.has_perm(
            "campaigns.view_campaign"
        ) or self.request.user.has_perm("campaigns.view_own_campaign"):
            attrs = {
                "hx-get": f"{{get_detail_view_url}}?{query_string}",
                "hx-target": "#mainContent",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "hx-select": "#mainContent",
                "style": "cursor:pointer",
                "class": "hover:text-primary-600",
            }
        return [
            {
                "campaign_name": {
                    **attrs,
                }
            }
        ]

    bulk_update_fields = [
        "campaign_type",
        "campaign_owner",
        "status",
        "expected_revenue",
        "budget_cost",
    ]

    @cached_property
    def actions(self):
        """
        Function to return list of actions for each record in the list view
        """
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("campaigns.change_campaign")
            or self.get_queryset().filter(campaign_owner=self.request.user).exists()
        )

        if show_actions:
            actions.extend(
                [
                    {
                        "action": "Edit",
                        "src": "assets/icons/edit.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                            hx-get="{get_edit_campaign_url}?new=true"
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
            if self.request.user.has_perm("campaigns.delete_campaign"):
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

    def no_record_add_button(self):
        """
        Function to return no record add button configuration
        """
        if self.request.user.has_perm("campaigns.add_campaign"):
            return {
                "url": f"""{ reverse_lazy('campaigns:campaign_create')}?new=true""",
                "attrs": 'id="campaign-create"',
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("campaigns.delete_campaign"), name="dispatch"
)
class CampaignDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """
    Campaign delete view
    """

    model = Campaign

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignKanbanView(LoginRequiredMixin, HorillaKanbanView):
    """
    Kanban view for campaign
    """

    model = Campaign
    view_id = "Campaign_Kanban"
    filterset_class = CampaignFilter
    search_url = reverse_lazy("campaigns:campaign_list_view")
    main_url = reverse_lazy("campaigns:campaign_view")
    group_by_field = "status"

    @cached_property
    def columns(self):
        """
        Function to return columns for kanban view
        """
        instance = self.model()
        return [
            (instance._meta.get_field("campaign_name").verbose_name, "campaign_name"),
            (instance._meta.get_field("campaign_owner").verbose_name, "campaign_owner"),
            (instance._meta.get_field("campaign_type").verbose_name, "campaign_type"),
            (
                instance._meta.get_field("expected_revenue").verbose_name,
                "expected_revenue",
            ),
            (instance._meta.get_field("budget_cost").verbose_name, "budget_cost"),
        ]

    @cached_property
    def kanban_attrs(self):
        """
        Function to return attributes for kanban cards
        """
        query_params = self.request.GET.dict()
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        if self.request.user.has_perm(
            "campaigns.view_campaign"
        ) or self.request.user.has_perm("campaigns.view_own_campaign"):
            return f"""
                    hx-get="{{get_detail_view_url}}?{query_string}"
                    hx-target="#mainContent"
                    hx-swap="outerHTML"
                    hx-push-url="true"
                    hx-select="#mainContent"
                    style ="cursor:pointer",
                    """

    @cached_property
    def actions(self):
        """
        Return list of actions for the detail view
        """
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("campaigns.change_campaign")
            or self.get_queryset().filter(campaign_owner=self.request.user).exists()
        )

        if show_actions:
            actions.extend(
                [
                    {
                        "action": "Edit",
                        "src": "assets/icons/edit.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                            hx-get="{get_edit_campaign_url}?new=true"
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
            if self.request.user.has_perm("campaigns.delete_campaign"):
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
class CampaignFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    """
    form view for campaign
    """

    form_class = CampaignFormClass
    model = Campaign
    fullwidth_fields = ["number_sent", "description"]
    total_steps = 3
    step_titles = {
        "1": "Campaign Information",
        "2": "Financial Information",
        "3": "Additional Information",
    }

    @cached_property
    def form_url(self):
        """
        Return the URL for the form submission
        """
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("campaigns:campaign_edit", kwargs={"pk": pk})
        return reverse_lazy("campaigns:campaign_create")

    def get(self, request, *args, **kwargs):

        campaign_id = request.GET.get("id")
        if request.user.has_perm("campaigns.change_campaign") or request.user.has_perm(
            "campaigns.add_campaign"
        ):
            return super().get(request, *args, **kwargs)

        if campaign_id:
            campaign = get_object_or_404(Campaign, pk=campaign_id)
            if campaign.campaign_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(htmx_required, name="dispatch")
class CampaignChangeOwnerForm(LoginRequiredMixin, HorillaSingleFormView):
    """
    Change owner form
    """

    model = Campaign
    fields = ["campaign_owner"]
    full_width_fields = ["campaign_owner"]
    modal_height = False
    form_title = _("Change Owner")

    @cached_property
    def form_url(self):
        """
        Return the URL for the form submission
        """
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("campaigns:campaign_change_owner", kwargs={"pk": pk})

    def get(self, request, *args, **kwargs):

        campaign_id = request.GET.get("id")
        if request.user.has_perm("campaigns.change_campaign") or request.user.has_perm(
            "campaigns.add_campaign"
        ):
            return super().get(request, *args, **kwargs)

        if campaign_id:
            campaign = get_object_or_404(Campaign, pk=campaign_id)
            if campaign.campaign_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")


@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignDetailView(RecentlyViewedMixin, LoginRequiredMixin, HorillaDetailView):
    """
    Detail view for campaign
    """

    model = Campaign
    pipeline_field = "status"
    breadcrumbs = [
        ("Sales", "leads:leads_view"),
        ("Campaigns", "campaigns:campaign_view"),
    ]
    body = [
        "campaign_name",
        "campaign_owner",
        "start_date",
        "end_date",
        "campaign_type",
        "expected_revenue",
        "expected_response",
    ]

    tab_url = reverse_lazy("campaigns:campaign_detail_view_tabs")

    @cached_property
    def actions(self):
        """
        Return list of actions for the detail view
        """
        actions = []

        show_actions = (
            self.request.user.is_superuser
            or self.request.user.has_perm("campaigns.change_campaign")
            or self.get_queryset().filter(campaign_owner=self.request.user).exists()
        )

        if show_actions:
            actions.extend(
                [
                    {
                        "action": "Edit",
                        "src": "assets/icons/edit.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                            hx-get="{get_edit_campaign_url}?new=true"
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
            if self.request.user.has_perm("campaigns.delete_campaign"):
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
            campaign_owner_id=self.request.user, pk=self.kwargs["pk"]
        ).first() and not self.request.user.has_perm("campaigns.view_campaign"):
            return render(self.request, "error/403.html")
        return super().get(request, *args, **kwargs)


@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignDetailsTab(LoginRequiredMixin, HorillaDetailSectionView):
    """
    Details Tab view of campaign detail view
    """

    model = Campaign
    non_editable_fields = [
        "leads_in_campaign",
        "converted_leads_in_campaign",
        "contacts_in_campaign",
        "opportunities_in_campaign",
        "won_opportunities_in_campaign",
        "value_opportunities",
        "value_won_opportunities",
        "responses_in_campaign",
    ]
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
        "campaign_owner",
    ]


@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignDetailViewTabs(LoginRequiredMixin, HorillaDetailTabView):
    """
    Tab Views for Campaign detail view
    """

    def __init__(self, **kwargs):
        request = getattr(_thread_local, "request", None)
        self.request = request
        self.object_id = self.request.GET.get("object_id")
        super().__init__(**kwargs)

    urls = {
        "details": "campaigns:campaign_details_tab_view",
        "activity": "campaigns:campaign_activity_tab_view",
        "related_lists": "campaigns:campaign_related_list_tab_view",
        "notes_attachments": "campaigns:campaign_notes_attachments",
        "history": "campaigns:campaign_history_tab_view",
    }

    def get(self, request, *args, **kwargs):
        user = request.user
        lead_id = self.object_id

        is_owner = Campaign.objects.filter(campaign_owner_id=user, pk=lead_id).exists()
        has_permission = user.has_perm("campaigns.view_campaign") or user.has_perm(
            "campaigns.view_own_campaign"
        )

        if not (is_owner or has_permission):
            return render(request, "error/403.html")

        return super().get(request, *args, **kwargs)


@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignNotesAndAttachments(
    LoginRequiredMixin, HorillaNotesAttachementSectionView
):
    """Notes and Attachments Tab View"""

    model = Campaign


@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignActivityTab(LoginRequiredMixin, HorillaActivitySectionView):
    """
    Campaign detain view activity tab
    """

    model = Campaign


@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignHistoryTab(LoginRequiredMixin, HorillaHistorySectionView):
    """
    History tab foe campaign detail view
    """

    model = Campaign


@method_decorator(
    permission_required_or_denied(
        ["campaigns.view_campaign", "campaigns.view_own_campaign"]
    ),
    name="dispatch",
)
class CampaignRelatedListsTab(LoginRequiredMixin, HorillaRelatedListSectionView):
    """
    Related list tab view
    """

    model = Campaign

    @cached_property
    def related_list_config(self):
        """
        Return configuration for related lists
        """
        user = self.request.user
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        pk = self.request.GET.get("object_id")
        referrer_url = "campaign_detail_view"

        members_config = {
            "title": "Campaign Members",
            "can_add": True,
            "add_url": reverse_lazy("campaigns:add_campaign_members"),
            "columns": [
                (
                    CampaignMember._meta.get_field("member_type").verbose_name,
                    "get_member_type_display",
                ),
                ("Name", "get_title"),
                (
                    CampaignMember._meta.get_field("member_status").verbose_name,
                    "get_member_status_display",
                ),
            ],
            "actions": [
                {
                    "action": "edit",
                    "src": "/assets/icons/edit.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                        hx-get="{get_edit_campaign_member}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="event.stopPropagation();openModal()"
                        hx-indicator="#modalBox"
                    """,
                },
                (
                    {
                        "action": "Delete",
                        "src": "assets/icons/a4.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                        hx-post="{get_delete_url}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        hx-trigger="click"
                        hx-vals='{{"check_dependencies": "false"}}'
                        onclick="openModal()"
                    """,
                    }
                    if self.request.user.has_perm("campaigns.delete_campaignmember")
                    else {}
                ),
            ],
        }

        if user.has_perm("leads.view_lead") or user.has_perm("contacts.view_contact"):
            members_config["col_attrs"] = [
                {
                    "get_title": {
                        "style": "cursor:pointer",
                        "class": "hover:text-primary-600",
                        "hx-get": (
                            f"{{get_detail_view}}?referrer_app={self.model._meta.app_label}"
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

        child_campaigns_config = {
            "title": "Child Campaigns",
            "can_add": True,
            "add_url": reverse_lazy("campaigns:create_child_campaign"),
            "columns": [
                (
                    Campaign._meta.get_field("campaign_name").verbose_name,
                    "campaign_name",
                ),
                (Campaign._meta.get_field("start_date").verbose_name, "start_date"),
                (Campaign._meta.get_field("end_date").verbose_name, "end_date"),
            ],
            "actions": [
                {
                    "action": "edit",
                    "src": "/assets/icons/edit.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                        hx-get="{get_edit_campaign_url}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="event.stopPropagation();openModal()"
                        hx-indicator="#modalBox"
                    """,
                },
                (
                    {
                        "action": "Delete",
                        "src": "assets/icons/a4.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                        hx-delete="{get_delete_child_campaign_url}"
                        hx-on:click="hxConfirm(this,'Are you sure you want to remove this child campaign relationship?')"
                        hx-target="#deleteModeBox"
                        hx-swap="innerHTML"
                        hx-trigger="confirmed"
                    """,
                    }
                    if self.request.user.has_perm("campaigns.delete_campaign")
                    else {}
                ),
            ],
        }

        if user.has_perm("campaigns.view_campaign"):
            child_campaigns_config["col_attrs"] = [
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

        opportunities_config = {
            "title": "Related Opportunities",
            "columns": [
                (
                    Campaign._meta.get_field("opportunities")
                    .related_model._meta.get_field("name")
                    .verbose_name,
                    "name",
                ),
                (
                    Campaign._meta.get_field("opportunities")
                    .related_model._meta.get_field("amount")
                    .verbose_name,
                    "amount",
                ),
                (
                    Campaign._meta.get_field("opportunities")
                    .related_model._meta.get_field("close_date")
                    .verbose_name,
                    "close_date",
                ),
                (
                    Campaign._meta.get_field("opportunities")
                    .related_model._meta.get_field("expected_revenue")
                    .verbose_name,
                    "expected_revenue",
                ),
            ],
        }

        if user.has_perm("opportunities.view_opportunity"):
            opportunities_config["col_attrs"] = [
                {
                    "name": {
                        "style": "cursor:pointer",
                        "class": "hover:text-primary-600",
                        "hx-get": (
                            f"{{get_detail_url}}?referrer_app={self.model._meta.app_label}"
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
            "members": members_config,
            "child_campaigns": child_campaigns_config,
            "opportunities": opportunities_config,
        }

    excluded_related_lists = ["contacts"]


@method_decorator(htmx_required, name="dispatch")
class AddChildCampaignFormView(LoginRequiredMixin, FormView):
    """
    Form view to select an existing campaign and assign it as a child campaign.
    """

    template_name = "single_form_view.html"
    header = True
    form_class = ChildCampaignForm

    def get(self, request, *args, **kwargs):

        campaign_id = request.GET.get("id")
        if (
            request.user.has_perm("campaigns.change_campaign")
            or request.user.has_perm("campaigns.create_campaign")
            or request.user.is_superuser
        ):
            return super().get(request, *args, **kwargs)

        if campaign_id:
            campaign = get_object_or_404(Campaign, pk=campaign_id)
            if campaign.campaign_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")

    def get_form_kwargs(self):
        """
        Pass the request to the form for queryset filtering and validation.
        """
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_initial(self):
        """
        Prepopulate the form with initial data if needed.
        """
        initial = super().get_initial()
        parent_id = self.request.GET.get("id")

        if parent_id:
            try:
                parent_campaign = Campaign.objects.get(pk=parent_id)
                initial["parent_campaign"] = parent_campaign
            except Exception as e:
                logger.error(e)  # Debug

        return initial

    def get_context_data(self, **kwargs):
        """
        Add context data for the template.
        """
        context = super().get_context_data(**kwargs)
        context["form_title"] = _("Add Child Campaign")
        context["full_width_fields"] = ["campaign"]  # Make sure campaign is full width
        context["form_url"] = self.get_form_url()

        form_url = self.get_form_url()

        context["hx_attrs"] = {
            "hx-post": str(form_url),
            "hx-target": "#modalBox",
            "hx-swap": "innerHTML",
        }
        context["modal_height"] = False
        context["view_id"] = "add-child-campaign-form-view"
        context["condition_fields"] = []
        context["header"] = self.header

        return context

    def form_valid(self, form):
        """
        Update the selected campaign's parent_campaign field and return HTMX response.
        """
        if not self.request.user.is_authenticated:
            messages.error(
                self.request, _("You must be logged in to perform this action.")
            )
            return self.form_invalid(form)

        selected_campaign = form.cleaned_data["campaign"]
        parent_campaign = form.cleaned_data[
            "parent_campaign"
        ]  # Get from form data instead of GET

        if not parent_campaign:
            form.add_error(None, _("No parent campaign specified in the request."))
            return self.form_invalid(form)

        try:
            if selected_campaign.id == parent_campaign.id:
                form.add_error("campaign", _("A campaign cannot be its own parent."))
                return self.form_invalid(form)

            if selected_campaign.parent_campaign:
                form.add_error(
                    "campaign", _("This campaign already has a parent campaign.")
                )
                return self.form_invalid(form)

            # Update the selected campaign
            selected_campaign.parent_campaign = parent_campaign
            selected_campaign.updated_at = timezone.now()
            selected_campaign.updated_by = self.request.user
            selected_campaign.save()

            messages.success(self.request, _("Child campaign assigned successfully!"))

        except ValueError:
            form.add_error(None, _("Invalid parent campaign ID format."))
            return self.form_invalid(form)

        return HttpResponse(
            "<script>htmx.trigger('#tab-child_campaigns-btn', 'click');closeModal();</script>"
        )

    def get_form_url(self):
        """
        Get the form URL for submission.
        """
        return reverse_lazy("campaigns:create_child_campaign")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("campaigns.delete_campaign"), name="dispatch"
)
class ChildCampaignDeleteView(LoginRequiredMixin, View):
    """
    View to remove parent-child relationship from a campaign.
    """

    def delete(self, request, pk, *args, **kwargs):
        """
        Handle DELETE request to remove parent campaign relationship.
        """

        child_campaign = get_object_or_404(Campaign, pk=pk)

        has_permission = (
            request.user.has_perm("campaigns.change_campaign")
            or child_campaign.campaign_owner == request.user
            or (
                child_campaign.parent_campaign
                and child_campaign.parent_campaign.campaign_owner == request.user
            )
        )

        if not has_permission:
            messages.error(
                request, _("You don't have permission to perform this action.")
            )
            return HttpResponse(
                "<script>htmx.trigger('#tab-child_campaigns-btn', 'click');</script>",
                status=403,
            )

        parent_campaign = child_campaign.parent_campaign

        if not parent_campaign:
            messages.warning(
                request, _("This campaign doesn't have a parent campaign.")
            )
            return HttpResponse(
                "<script>htmx.trigger('#tab-child_campaigns-btn', 'click');</script>"
            )

        try:
            child_campaign.parent_campaign = None
            child_campaign.updated_at = timezone.now()
            child_campaign.updated_by = request.user
            child_campaign.save()

            messages.success(
                request,
                _(
                    f"Successfully removed {child_campaign.campaign_name} from {parent_campaign.campaign_name}'s child campaigns."
                ),
            )

            return HttpResponse(
                "<script>htmx.trigger('#tab-child_campaigns-btn', 'click');</script>"
            )

        except Exception as e:
            print(f"Error removing child campaign: {e}")
            messages.error(
                request, _("An error occurred while removing the child campaign.")
            )
            return HttpResponse(
                "<script>htmx.trigger('#tab-child_campaigns-btn', 'click');</script>",
            )


@method_decorator(htmx_required, name="dispatch")
class AddToCampaignFormview(LoginRequiredMixin, HorillaSingleFormView):
    """
    Add lead to campaign form view
    """

    model = CampaignMember
    fields = ["lead", "campaign", "member_status"]
    full_width_fields = ["campaign", "member_status"]
    modal_height = False
    form_title = _("Add to Campaign")
    hidden_fields = ["lead"]

    def get(self, request, *args, **kwargs):

        lead_id = request.GET.get("id")
        if request.user.has_perm("leads.change_lead") or request.user.has_perm(
            "leads.add_lead"
        ):
            return super().get(request, *args, **kwargs)

        if lead_id:
            lead = apps.get_model("leads", "Lead")

            lead = get_object_or_404(lead, pk=lead_id)

            if lead.lead_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")

    def form_valid(self, form):
        super().form_valid(form)
        return HttpResponse(
            "<script>htmx.trigger('#tab-campaigns-btn', 'click');closeModal();</script>"
        )

    def get_initial(self):
        initial = super().get_initial()
        lead_id = self.request.GET.get("id")
        if lead_id:
            initial["lead"] = lead_id
        return initial

    @cached_property
    def form_url(self):
        """
        Return the form URL for submission.
        """
        if self.kwargs.get("pk"):
            return reverse_lazy(
                "campaigns:edit_campaign_member", kwargs={"pk": self.kwargs.get("pk")}
            )
        return reverse_lazy("campaigns:add_to_campaign")


@method_decorator(htmx_required, name="dispatch")
class AddCampaignMemberFormview(LoginRequiredMixin, HorillaSingleFormView):
    """
    Form view to craete and edit campaign member
    """

    model = CampaignMember
    form_class = CampaignMemberForm
    modal_height = False
    form_title = _("Add Campaign Members")
    full_width_fields = ["member_status", "member_type", "lead", "contact"]

    def get(self, request, *args, **kwargs):

        campaign_id = request.GET.get("id")
        if request.user.has_perm("campaigns.change_campaign") or request.user.has_perm(
            "campaigns.add_campaign"
        ):
            return super().get(request, *args, **kwargs)

        if campaign_id:
            campaign = get_object_or_404(Campaign, pk=campaign_id)
            if campaign.campaign_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")

    def get_initial(self):
        initial = super().get_initial()
        campaign_id = (
            self.request.GET.get("id")
            if self.request.GET.get("id")
            else self.request.GET.get("campaign")
        )
        member_type = self.request.GET.get("member_type")
        if member_type:
            initial["member_type"] = member_type
        if campaign_id:
            initial["campaign"] = campaign_id
        return initial

    def form_valid(self, form):
        super().form_valid(form)
        return HttpResponse(
            "<script>htmx.trigger('#tab-members-btn', 'click');closeModal();</script>"
        )

    @cached_property
    def form_url(self):
        """
        Return the form URL for submission.
        """
        if self.kwargs.get("pk"):
            return reverse_lazy(
                "campaigns:edit_added_campaign_members",
                kwargs={"pk": self.kwargs.get("pk")},
            )
        return reverse_lazy("campaigns:add_campaign_members")


@method_decorator(
    permission_required_or_denied("campaigns.delete_campaignmember"), name="dispatch"
)
class CampaignMemberDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """
    Campaign member delete view
    """

    model = CampaignMember

    def get_post_delete_response(self):
        return HttpResponse(
            "<script>htmx.trigger('#tab-members-btn','click');$('#reloadButton').click();</script>"
        )


@method_decorator(htmx_required, name="dispatch")
class AddContactToCampaignFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    Form iew for adding contacts into campaigns
    """

    model = CampaignMember
    fields = ["contact", "campaign", "member_status"]
    full_width_fields = ["campaign", "member_status"]
    modal_height = False
    form_title = _("Add to Campaign")
    hidden_fields = ["contact"]

    def form_valid(self, form):
        form.instance.member_type = "contact"
        super().form_valid(form)
        return HttpResponse(
            "<script>htmx.trigger('#tab-campaigns-btn', 'click');closeModal();</script>"
        )

    def get_initial(self):
        initial = super().get_initial()
        contact_id = self.request.GET.get("id")
        if contact_id:
            initial["contact"] = contact_id
        return initial

    def get(self, request, *args, **kwargs):

        contact_id = request.GET.get("id")
        if request.user.has_perm("contacts.change_contact") or request.user.has_perm(
            "contacts.add_contact"
        ):
            return super().get(request, *args, **kwargs)

        if contact_id:
            contact = apps.get_model("contacts", "Contact")

            contact = get_object_or_404(contact, pk=contact_id)

            if contact.contact_owner == request.user:
                return super().get(request, *args, **kwargs)

        return render(request, "error/403.html")

    @cached_property
    def form_url(self):
        """
        Return the form URL for submission.
        """
        if self.kwargs.get("pk"):
            return reverse_lazy(
                "campaigns:edit_contact_to_campaign",
                kwargs={"pk": self.kwargs.get("pk")},
            )
        return reverse_lazy("campaigns:add_contact_to_campaign")


@method_decorator(
    permission_required_or_denied("campaigns.delete_campaignmember"), name="dispatch"
)
class CampaignContactMemberDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """
    Campaign contact member delete view
    """

    model = CampaignMember

    def get_post_delete_response(self):
        return HttpResponse(
            "<script>htmx.trigger('#tab-campaigns-btn','click');</script>"
        )
