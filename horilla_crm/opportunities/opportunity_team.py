"""
Views for managing Opportunity Teams and their members.

This module provides list, detail, form, and delete views for opportunity teams
and their members, including HTMX-based navigation, filtering, and CRUD handling.
"""

import logging
from functools import cached_property
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.db import models, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView, View

from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import htmx_required
from horilla_crm.opportunities.filters import (
    OpportunityTeamFilter,
    OpportunityTeamMembersFilter,
)
from horilla_crm.opportunities.forms import (
    AddDefaultTeamForm,
    OpportunityMemberForm,
    OpportunityTeamForm,
    OpportunityTeamMemberForm,
)
from horilla_crm.opportunities.models import (
    DefaultOpportunityMember,
    Opportunity,
    OpportunitySettings,
    OpportunitySplit,
    OpportunityTeam,
    OpportunityTeamMember,
)
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)


class OpportunityTeamView(LoginRequiredMixin, HorillaView):
    """Displays the main opportunity team page."""

    template_name = "opportunity_team/opportunity_team_view.html"
    nav_url = reverse_lazy("opportunities:opportunity_team_nav_view")
    list_url = reverse_lazy("opportunities:opportunity_team_list_view")


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamNavbar(LoginRequiredMixin, HorillaNavView):
    """Navbar for opportunity team listing with filters and create option."""

    nav_title = OpportunityTeam._meta.verbose_name_plural
    search_url = reverse_lazy("opportunities:opportunity_team_list_view")
    main_url = reverse_lazy("opportunities:opportunity_team_view")
    filterset_class = OpportunityTeamFilter
    model_name = "OpportunityTeam"
    model_app_label = "opportunities"
    nav_width = False
    gap_enabled = False
    all_view_types = False
    recently_viewed_option = False
    filter_option = False
    one_view_only = True
    reload_option = False

    @cached_property
    def new_button(self):
        """Return 'New' button config if user has add permission."""
        return {
            "url": f"""{ reverse_lazy('opportunities:create_opportunity_team')}?new=true""",
            "attrs": {"id": "opportunity-team-create"},
        }


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamListView(LoginRequiredMixin, HorillaListView):
    """Lists opportunity teams owned by the logged-in user."""

    model = OpportunityTeam
    view_id = "opportunity-team-list"
    filterset_class = OpportunityTeamFilter
    search_url = reverse_lazy("opportunities:opportunity_team_list_view")
    main_url = reverse_lazy("opportunities:opportunity_team_view")
    save_to_list_option = False
    bulk_select_option = False
    clear_session_button_enabled = False
    table_width = False
    enable_sorting = False

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(owner=self.request.user.pk)
        return queryset

    @cached_property
    def col_attrs(self):
        """Defines HTMX attributes for clickable team name column."""
        htmx_attrs = {
            "hx-get": "{get_detail_view_url}",
            "hx-target": "#opportunity-team-view",
            "hx-swap": "outerHTML",
            "hx-push-url": "true",
            "hx-select": "#opportunity-team-view",
        }
        return [
            {
                "team_name": {
                    "style": "cursor:pointer",
                    "class": "hover:text-primary-600",
                    **htmx_attrs,
                }
            }
        ]

    def no_record_add_button(self):
        """Return 'Add' button config for no-record state."""
        return {
            "url": f"""{ reverse_lazy('opportunities:create_opportunity_team')}?new=true""",
            "attrs": 'id="opportunity-team-create"',
        }

    @cached_property
    def columns(self):
        """Defines columns for the opportunity team list view."""
        instance = self.model()
        return [
            (instance._meta.get_field("team_name").verbose_name, "team_name"),
            (instance._meta.get_field("description").verbose_name, "description"),
        ]

    @cached_property
    def actions(self):
        """Defines action buttons for each opportunity team in the list view."""
        return [
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
            },
        ]


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamFormView(LoginRequiredMixin, HorillaSingleFormView):
    """Handles creation and update of opportunity teams with members."""

    model = OpportunityTeam
    form_class = OpportunityTeamForm
    full_width_fields = ["team_name", "description"]
    condition_fields = ["user", "team_role", "opportunity_access_level"]
    modal_height = False
    form_title = _("Create Opportunity Team")
    condition_field_title = _("Add Members")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condition_model"] = DefaultOpportunityMember
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object and self.object.pk:
            existing_members = DefaultOpportunityMember.objects.filter(
                team=self.object
            ).order_by("created_at")
            context["existing_conditions"] = existing_members
        form = context.get("form")
        if form and hasattr(form, "condition_field_choices"):
            context["condition_field_choices"] = form.condition_field_choices
        else:
            temp_form = self.get_form_class()(
                condition_model=DefaultOpportunityMember, request=self.request
            )
            if hasattr(temp_form, "condition_field_choices"):
                context["condition_field_choices"] = temp_form.condition_field_choices

        return context

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.error(
                self.request, "You must be logged in to perform this action."
            )
            return self.form_invalid(form)

        self.object = form.save(commit=False)
        if self.kwargs.get("pk"):
            self.object.updated_at = timezone.now()
            self.object.updated_by = self.request.user
        else:
            self.object.created_at = timezone.now()
            self.object.created_by = self.request.user
            self.object.updated_at = timezone.now()
            self.object.updated_by = self.request.user
        self.object.owner = self.request.user
        self.object.company = (
            getattr(_thread_local, "request", None).active_company
            if hasattr(_thread_local, "request")
            else self.request.user.company
        )
        self.object.save()
        form.save_m2m()

        condition_rows = form.cleaned_data.get("condition_rows", [])
        if self.kwargs.get("pk"):
            DefaultOpportunityMember.objects.filter(team=self.object).delete()

        for row in condition_rows:
            try:
                DefaultOpportunityMember.objects.create(
                    team=self.object,
                    user=row.get("user"),
                    team_role=row.get("team_role"),
                    opportunity_access_level=row.get("opportunity_access_level"),
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
            except Exception as e:
                messages.error(self.request, f"Failed to save team member: {str(e)}")
                return self.form_invalid(form)

        self.request.session["condition_row_count"] = 0
        self.request.session.modified = True
        messages.success(
            self.request,
            f"{self.model._meta.verbose_name.title()} {'updated' if self.kwargs.get('pk') else 'created'} successfully!",
        )
        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")

    @cached_property
    def form_url(self):
        """Constructs the form URL for creating or editing an opportunity team."""
        model_name = self.request.GET.get("model_name")
        obj = self.request.GET.get("obj")
        pk = self.kwargs.get("pk")
        if pk:
            base_url = reverse_lazy(
                "opportunities:edit_opportunity_team", kwargs={"pk": pk} if pk else None
            )
        else:
            base_url = reverse_lazy("opportunities:create_opportunity_team")
        if model_name:
            return f"{base_url}?{urlencode({'model_name': model_name,'obj': obj})}"
        return base_url


class OpportunityTeamDetailView(LoginRequiredMixin, DetailView):
    """Shows details and members of a specific opportunity team."""

    template_name = "opportunity_team/opportunity_team_detail_view.html"
    model = OpportunityTeam

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        try:
            self.object = self.get_object()
        except Exception as e:
            if request.headers.get("HX-Request") == "true":
                messages.error(self.request, e)
                return HttpResponse(headers={"HX-Refresh": "true"})
            raise HorillaHttp404(e)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_obj = self.get_object()
        members = DefaultOpportunityMember.objects.filter(team=current_obj)
        context["current_obj"] = current_obj
        context["members"] = members
        context["nav_url"] = reverse_lazy(
            "opportunities:opportunity_team_detail_nav_view"
        )
        context["list_url"] = reverse_lazy(
            "opportunities:opportunity_team_detail_list_view"
        )
        return context


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamDetailNavbar(LoginRequiredMixin, HorillaNavView):
    """Navbar for navigating inside a single opportunity team detail view."""

    search_url = reverse_lazy("opportunities:opportunity_team_detail_list_view")
    filterset_class = OpportunityTeamFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "OpportunityTeam"
    nav_width = False
    gap_enabled = False
    navbar_indication = True
    navbar_indication_attrs = {
        "hx-get": reverse_lazy("opportunities:opportunity_team_view"),
        "hx-target": "#opportunity-team-view",
        "hx-swap": "outerHTML",
        "hx-push-url": "true",
        "hx-select": "#opportunity-team-view",
    }

    @cached_property
    def new_button(self):
        """Return 'New' button config for adding team members."""
        obj = self.request.GET.get("obj")
        return {
            "url": f"""{ reverse_lazy('opportunities:create_opportunity_team_member')}?obj={obj}""",
            "attrs": {"id": "opportunity-team-member-create"},
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_id = self.request.GET.get("obj")
        obj = OpportunityTeam.objects.filter(pk=obj_id).first()
        self.nav_title = obj.team_name if obj else ""
        context["nav_title"] = self.nav_title
        return context


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamDetailListView(LoginRequiredMixin, HorillaListView):
    """Lists members of a specific opportunity team."""

    model = DefaultOpportunityMember
    view_id = "opportunity-team-members-list"
    filterset_class = OpportunityTeamMembersFilter
    search_url = reverse_lazy("opportunities:opportunity_team_detail_list_view")
    main_url = reverse_lazy("opportunities:opportunity_team_view")
    save_to_list_option = False
    bulk_select_option = False
    clear_session_button_enabled = False
    table_width = False
    enable_sorting = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        request = getattr(_thread_local, "request", None)
        obj_id = request.GET.get("obj")
        if obj_id:
            self.main_url = reverse_lazy(
                "opportunities:opportunity_team_detail_view", kwargs={"pk": obj_id}
            )

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("user").verbose_name, "user"),
            (
                instance._meta.get_field("team_role").verbose_name,
                "get_team_role_display",
            ),
            (
                instance._meta.get_field("opportunity_access_level").verbose_name,
                "get_opportunity_access_level_display",
            ),
        ]

    @cached_property
    def actions(self):
        """Defines action buttons for each team member in the list view."""
        return [
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
            },
        ]

    def get_queryset(self):
        obj_id = self.request.GET.get("obj")
        queryset = super().get_queryset()
        queryset = queryset.filter(team=obj_id)
        return queryset


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamMemberCreateView(LoginRequiredMixin, HorillaSingleFormView):
    """Form view to create new members in an opportunity team."""

    model = DefaultOpportunityMember
    form_class = OpportunityTeamMemberForm
    fields = ["team"]
    condition_fields = ["user", "team_role", "opportunity_access_level"]
    modal_height = False
    form_title = _("Create Opportunity Team")
    hidden_fields = ["team"]
    condition_field_title = _("Add Members")

    def get_initial(self):
        initial = super().get_initial()
        obj_id = self.request.GET.get("obj")
        initial["team"] = obj_id
        return initial

    @cached_property
    def form_url(self):
        """Constructs the form URL for editing a team member."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "opportunities:edit_opportunity_team_member", kwargs={"pk": pk}
            )
        return reverse_lazy("opportunities:create_opportunity_team_member")

    def form_valid(self, form):
        """Override to handle condition fields properly"""

        team_id = form.cleaned_data.get("team")
        if not team_id:
            form.add_error("team", "Team is required.")
            return self.form_invalid(form)

        created_objects = []
        row_indices = set()
        validation_errors = []

        for key in self.request.POST.keys():
            for field_name in self.condition_fields:
                if key.startswith(f"{field_name}_"):
                    try:
                        row_index = key.split("_")[-1]
                        if row_index.isdigit():
                            row_indices.add(row_index)
                    except:
                        pass

        submitted_users = set()

        for row_index in sorted(row_indices):
            condition_data = {}
            has_data = False
            row_num = int(row_index) + 1

            for field_name in self.condition_fields:
                field_key = f"{field_name}_{row_index}"
                value = self.request.POST.get(field_key)
                if value and value.strip():
                    condition_data[field_name] = value.strip()
                    has_data = True

            if has_data:

                user_id = condition_data.get("user")

                if user_id in submitted_users:
                    validation_errors.append("User has already been added to this team")
                    continue

                try:
                    existing = self.model.objects.filter(
                        user_id=user_id,
                        team_id=team_id.id if hasattr(team_id, "id") else team_id,
                    ).exists()
                    if existing:
                        try:

                            user_model = get_user_model()
                            user_obj = user_model.objects.get(pk=user_id)
                            user_name = (
                                f"{user_obj.first_name} {user_obj.last_name}".strip()
                                or user_obj.username
                            )
                        except:
                            user_name = f"User ID {user_id}"

                        validation_errors.append(
                            f"{user_name} is already a member of this team"
                        )
                        continue
                except Exception as e:
                    logger.error("Error checking existing user: %s", e)

                submitted_users.add(user_id)

                try:
                    new_obj = self.model()
                    new_obj.team = team_id

                    for field_name, value in condition_data.items():
                        try:
                            model_field = self.model._meta.get_field(field_name)
                            if isinstance(model_field, models.ForeignKey):
                                related_obj = model_field.related_model.objects.get(
                                    pk=value
                                )
                                setattr(new_obj, field_name, related_obj)
                            else:
                                setattr(new_obj, field_name, value)
                        except Exception as e:
                            validation_errors.append(
                                f"Row {row_num}: Invalid {field_name} - {str(e)}"
                            )
                            break
                    else:
                        # Set timestamps and company
                        new_obj.created_at = timezone.now()
                        new_obj.created_by = self.request.user
                        new_obj.updated_at = timezone.now()
                        new_obj.updated_by = self.request.user
                        new_obj.company = (
                            getattr(_thread_local, "request", None).active_company
                            if hasattr(_thread_local, "request")
                            else self.request.user.company
                        )

                        new_obj.save()
                        created_objects.append(new_obj)

                except Exception as e:
                    error_msg = str(e)
                    if (
                        "UNIQUE constraint failed" in error_msg
                        and "user_id" in error_msg
                        and "team_id" in error_msg
                    ):
                        try:

                            user_model = get_user_model()
                            user_obj = user_model.objects.get(pk=user_id)
                            user_name = (
                                f"{user_obj.first_name} {user_obj.last_name}".strip()
                                or user_obj.username
                            )
                        except:
                            user_name = f"User ID {user_id}"
                        validation_errors.append(
                            f"{user_name} is already a member of this team"
                        )
                    else:
                        validation_errors.append(
                            f"Row {row_num}: Error creating team member - {error_msg}"
                        )

        if validation_errors:
            for error in validation_errors:
                form.add_error(None, error)
            return self.form_invalid(form)

        if not created_objects:
            form.add_error(
                None, "At least one team member must be added with all required fields."
            )
            return self.form_invalid(form)

        self.request.session["condition_row_count"] = 0
        self.request.session.modified = True

        success_msg = f"Created {len(created_objects)} team member(s) successfully!"
        messages.success(self.request, success_msg)

        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamMemberUpdateView(LoginRequiredMixin, HorillaSingleFormView):
    """Form view to update an existing opportunity team member."""

    model = DefaultOpportunityMember
    form_class = OpportunityTeamMemberForm
    fields = ["team", "user", "team_role", "opportunity_access_level"]
    full_width_fields = ["user", "team_role", "opportunity_access_level"]
    form_title = _("Update Team Member")
    modal_height = False
    hidden_fields = ["team"]

    @cached_property
    def form_url(self):
        """Constructs the form URL for editing a team member."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "opportunities:edit_opportunity_team_member", kwargs={"pk": pk}
            )
        return None


@method_decorator(htmx_required, name="dispatch")
class OpportunityMemberUpdateView(LoginRequiredMixin, HorillaSingleFormView):
    """Form view to update an existing opportunity  member."""

    model = OpportunityTeamMember
    fields = ["team_role", "opportunity_access"]
    full_width_fields = ["team_role", "opportunity_access"]
    form_title = _("Update Team Member")
    modal_height = False

    @cached_property
    def form_url(self):
        """Constructs the form URL for editing a team member."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "opportunities:edit_opportunity_member", kwargs={"pk": pk}
            )
        return None


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Deletes an opportunity team and returns HTMX response."""

    model = OpportunityTeam

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(htmx_required, name="dispatch")
class OpportunityTeamMembersDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Deletes an opportunity team member and returns HTMX response."""

    model = DefaultOpportunityMember

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


@method_decorator(htmx_required, name="dispatch")
class OpportunityMembersDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Deletes an opportunity team member and returns HTMX response."""

    model = OpportunityTeamMember

    def delete(self, request, *args, **kwargs):
        """
        Override delete to check if member has splits assigned before deletion.
        """
        try:
            self.object = self.get_object()
            team_member = self.object
            opportunity = team_member.opportunity
            user = team_member.user

            # Check if this user has any splits assigned in this opportunity
            has_splits = OpportunitySplit.objects.filter(
                opportunity=opportunity, user=user
            ).exists()

            if has_splits:
                # Get split types where user has splits
                split_types_with_user = (
                    OpportunitySplit.objects.filter(opportunity=opportunity, user=user)
                    .select_related("split_type")
                    .values_list("split_type__split_label", flat=True)
                )

                split_types_list = ", ".join(split_types_with_user)

                messages.error(
                    request,
                    _(
                        f"Cannot delete {user.get_full_name() or user.username} from the opportunity team. "
                        f"This member has splits assigned in: {split_types_list}. "
                    ),
                )
                return HttpResponse(
                    "<script>$('#reloadButton').click();$('#reloadMessagesButton').click();closeDeleteModeModal();</script>"
                )

            # If no splits, proceed with normal deletion
            return super().delete(request, *args, **kwargs)

        except Exception as e:
            logger.error(f"Error in OpportunityMembersDeleteView.delete: {str(e)}")
            messages.error(
                request, _("An error occurred while deleting the team member.")
            )
            return HttpResponse(
                "<script>$('#reloadButton').click();$('#reloadMessagesButton').click();closeDeleteModeModal();</script>"
            )

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


class AddDefaultTeamView(LoginRequiredMixin, HorillaSingleFormView):
    """
    View to add default team members from an OpportunityTeam to an Opportunity
    """

    form_class = AddDefaultTeamForm
    form_title = _("Add Default Team")
    view_id = "add-default-team"
    full_width_fields = ["team"]
    modal_height = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        opportunity_id = self.request.GET.get("opportunity_id")
        if opportunity_id:
            kwargs["opportunity"] = get_object_or_404(Opportunity, pk=opportunity_id)
        return kwargs

    def form_valid(self, form):
        """
        When form is valid, add all default members from the selected team
        to the opportunity as OpportunityTeamMembers
        """
        opportunity_id = self.request.GET.get("id")

        if not opportunity_id:
            messages.error(self.request, _("Opportunity ID is required"))
            return self.form_invalid(form)

        try:
            opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
            selected_team = form.cleaned_data["team"]

            # Get all default members from the selected team
            default_members = DefaultOpportunityMember.objects.filter(
                team=selected_team
            )

            if not default_members.exists():
                messages.warning(
                    self.request,
                    _("The selected team has no default members configured."),
                )
                return HttpResponse("<script>closeModal();</script>")

            added_count = 0
            skipped_count = 0

            for default_member in default_members:
                existing_member = OpportunityTeamMember.objects.filter(
                    opportunity=opportunity, user=default_member.user
                ).first()

                if existing_member:
                    skipped_count += 1
                    continue

                OpportunityTeamMember.objects.create(
                    opportunity=opportunity,
                    user=default_member.user,
                    team_role=default_member.team_role,
                    opportunity_access=default_member.opportunity_access_level,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                    company=self.request.user.company,
                )
                added_count += 1

            if added_count > 0:
                messages.success(
                    self.request,
                    _(
                        f"Successfully added {added_count} team member(s) from {selected_team.team_name}."
                    ),
                )

            if skipped_count > 0:
                messages.info(
                    self.request,
                    _(
                        f"{skipped_count} member(s) were already part of the opportunity team."
                    ),
                )

            return HttpResponse(
                "<script>$('#reloadButton').click();closeModal();</script>"
            )

        except Exception as e:
            messages.error(
                self.request, _(f"Error adding default team members: {str(e)}")
            )
            return self.form_invalid(form)

    @cached_property
    def form_url(self):
        """Constructs the form URL for editing a team member."""
        return reverse_lazy("opportunities:add_default_team")


@method_decorator(htmx_required, name="dispatch")
class AddOpportunityMemberView(LoginRequiredMixin, HorillaSingleFormView):
    """Form view to create new members in an opportunity team."""

    model = OpportunityTeamMember
    form_class = OpportunityMemberForm
    fields = ["opportunity"]
    condition_fields = ["user", "team_role", "opportunity_access"]
    modal_height = False
    form_title = _("Add Opportunity Members")
    hidden_fields = ["opportunity"]
    condition_field_title = _("Add Members")

    def get_initial(self):
        initial = super().get_initial()
        obj_id = self.request.GET.get("id")
        initial["opportunity"] = obj_id
        return initial

    @cached_property
    def form_url(self):
        """Constructs the form URL for adding  member."""
        return reverse_lazy("opportunities:add_opportunity_member")

    def form_valid(self, form):
        """Override to handle condition fields properly"""

        opp_id = form.cleaned_data.get("opportunity")
        if not opp_id:
            form.add_error("opportunity", "Opportunity is required.")
            return self.form_invalid(form)

        created_objects = []
        row_indices = set()
        validation_errors = []
        users_to_create = []
        submitted_users = set()

        for key in self.request.POST.keys():
            for field_name in self.condition_fields:
                if key.startswith(f"{field_name}_"):
                    row_index = key.split("_")[-1]
                    if row_index.isdigit():
                        row_indices.add(row_index)

        for row_index in sorted(row_indices):
            condition_data = {}
            has_data = False
            row_num = int(row_index) + 1

            for field_name in self.condition_fields:
                field_key = f"{field_name}_{row_index}"
                value = self.request.POST.get(field_key)
                if value and value.strip():
                    condition_data[field_name] = value.strip()
                    has_data = True

            if not has_data:
                continue

            user_id = condition_data.get("user")

            if user_id in submitted_users:
                validation_errors.append(f"Row {row_num}: Duplicate user in submission")
                continue

            submitted_users.add(user_id)

            if self.model.objects.filter(
                user_id=user_id,
                opportunity_id=opp_id.id if hasattr(opp_id, "id") else opp_id,
            ).exists():
                try:
                    user_model = get_user_model()
                    user_obj = user_model.objects.get(pk=user_id)
                    user_name = (
                        f"{user_obj.first_name} {user_obj.last_name}".strip()
                        or user_obj.username
                    )
                except:
                    user_name = f"User ID {user_id}"

                validation_errors.append(
                    f"{user_name} is already a member of this opportunity"
                )
                continue

            users_to_create.append(condition_data)

        if validation_errors:
            for err in validation_errors:
                form.add_error(None, err)
            return self.form_invalid(form)

        if not users_to_create:
            form.add_error(None, "At least one valid team member must be added.")
            return self.form_invalid(form)

        with transaction.atomic():
            for condition_data in users_to_create:
                new_obj = self.model()
                new_obj.opportunity = opp_id

                for field_name, value in condition_data.items():
                    model_field = self.model._meta.get_field(field_name)
                    if isinstance(model_field, models.ForeignKey):
                        related_obj = model_field.related_model.objects.get(pk=value)
                        setattr(new_obj, field_name, related_obj)
                    else:
                        setattr(new_obj, field_name, value)

                new_obj.created_at = timezone.now()
                new_obj.created_by = self.request.user
                new_obj.updated_at = timezone.now()
                new_obj.updated_by = self.request.user
                new_obj.company = (
                    getattr(_thread_local, "request", None).active_company
                    if hasattr(_thread_local, "request")
                    else self.request.user.company
                )
                new_obj.save()
                created_objects.append(new_obj)

        self.request.session["condition_row_count"] = 0
        self.request.session.modified = True

        messages.success(
            self.request, f"Added {len(created_objects)} member(s) successfully!"
        )
        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")


class TeamSellingSetupView(LoginRequiredMixin, TemplateView):
    """
    View to display and manage Team Selling setup
    """

    template_name = "opportunity_team/team_selling_setup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.request.active_company
        settings = OpportunitySettings.get_settings(company)
        context["settings"] = settings
        context["team_selling_enabled"] = settings.team_selling_enabled
        return context


class ToggleTeamSellingView(LoginRequiredMixin, View):
    """
    HTMX view to toggle team selling feature on/off
    """

    def post(self, request, *args, **kwargs):
        company = self.request.active_company
        settings = OpportunitySettings.get_settings(company)
        action = request.POST.get("action")

        if action == "enable":
            settings.team_selling_enabled = True
            settings.save()
            messages.success(
                request,
                _(
                    "Team Selling has been enabled successfully! "
                    "Users can now create opportunity teams and add team members."
                ),
            )
        elif action == "disable":
            settings.team_selling_enabled = False
            settings.save()
            OpportunityTeam.objects.all().delete()
            OpportunityTeamMember.objects.all().delete()
            messages.success(
                request,
                _(
                    "Team Selling has been disabled and all existing opportunity teams "
                    "and their members have been deleted."
                ),
            )
        view_url = reverse_lazy("opportunities:team_selling_setup")

        response_html = (
            f"<span "
            f'hx-trigger="load" '
            f'hx-get="{view_url}" '
            f'hx-select="#opportunity-team-settings" '
            f'hx-target="#opportunity-team-settings" '
            f'hx-swap="outerHTML" '
            f'hx-push-url="false" '
            f'hx-select-oob="#settings-sidebar">'
            f"</span>"
        )
        return HttpResponse(mark_safe(response_html))
