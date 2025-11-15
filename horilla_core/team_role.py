"""
This view handles the methods for team role view
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.filters import TeamRoleFilter
from horilla_core.models import TeamRole
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)


class TeamRoleView(LoginRequiredMixin, HorillaView):
    """
    Template view for team role page
    """

    template_name = "team_role/team_role_view.html"
    nav_url = reverse_lazy("horilla_core:team_role_nav_view")
    list_url = reverse_lazy("horilla_core:team_role_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_teamrole"), name="dispatch")
class TeamRoleNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar fro team role
    """

    nav_title = TeamRole._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_core:team_role_list_view")
    main_url = reverse_lazy("horilla_core:team_role_view")
    filterset_class = TeamRoleFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "TeamRole"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    url_name = "team_role_list_view"

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_core.add_teamrole"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:team_role_create_form')}?new=true""",
                "attrs": {"id": "team-role-create"},
            }

    @cached_property
    def actions(self):
        if self.request.user.has_perm("horilla_core.view_teamrole"):
            return [
                {
                    "action": _("Add column to list"),
                    "attrs": f"""
                            hx-get="{reverse_lazy('horilla_generics:column_selector')}?app_label={self.model_app_label}&model_name={self.model_name}&url_name={self.url_name}"
                            onclick="openModal()"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            """,
                }
            ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_teamrole"), name="dispatch"
)
class TeamRoleListView(LoginRequiredMixin, HorillaListView):
    """
    List view of team role
    """

    model = TeamRole
    view_id = "team_role_list"
    filterset_class = TeamRoleFilter
    search_url = reverse_lazy("horilla_core:team_role_list_view")
    main_url = reverse_lazy("horilla_core:team_role_view")
    table_width = False
    bulk_select_option = False
    header_attrs = [
        {"description": {"style": "width: 300px;"}},
    ]

    def no_record_add_button(self):
        if self.request.user.has_perm("horilla_core.add_teamrole"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:team_role_create_form')}?new=true""",
                "attrs": 'id="team-role-create"',
            }

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("team_role_name").verbose_name, "team_role_name"),
            (instance._meta.get_field("description").verbose_name, "description"),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_teamrole"):
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
                }
            )
        if self.request.user.has_perm("horilla_core.delete_teamrole"):
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
    permission_required_or_denied("horilla_core.add_teamrole"), name="dispatch"
)
class TeamRoleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for team role
    """

    model = TeamRole
    fields = ["team_role_name", "description"]
    full_width_fields = ["team_role_name", "description"]
    modal_height = False
    form_title = _("Team Role")

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_core:team_role_update_form", kwargs={"pk": pk})
        return reverse_lazy("horilla_core:team_role_create_form")

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
    permission_required_or_denied("horilla_core.delete_teamrole"), name="dispatch"
)
class TeamRoleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = TeamRole

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")
