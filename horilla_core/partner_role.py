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
from horilla_core.filters import PartnerRoleFilter
from horilla_core.models import PartnerRole
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)


class PartnerRoleView(LoginRequiredMixin, HorillaView):
    """
    Template view for partner role page
    """

    template_name = "partner_role/partner_role_view.html"
    nav_url = reverse_lazy("horilla_core:partner_role_nav_view")
    list_url = reverse_lazy("horilla_core:partner_role_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_partnerrole"), name="dispatch")
class PartnerRoleNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar fro partner role
    """

    nav_title = PartnerRole._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_core:partner_role_list_view")
    main_url = reverse_lazy("horilla_core:partner_role_view")
    filterset_class = PartnerRoleFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "PartnerRole"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    url_name = "partner_role_list_view"

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_core.add_partnerrole"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:partner_role_create_form')}?new=true""",
                "attrs": {"id": "partner-role-create"},
            }

    @cached_property
    def actions(self):
        if self.request.user.has_perm("horilla_core.view_partnerrole"):
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
    permission_required_or_denied("horilla_core.view_partnerrole"), name="dispatch"
)
class PartnerRoleListView(LoginRequiredMixin, HorillaListView):
    """
    List view of partner role
    """

    model = PartnerRole
    view_id = "partner_role_list"
    filterset_class = PartnerRoleFilter
    search_url = reverse_lazy("horilla_core:partner_role_list_view")
    main_url = reverse_lazy("horilla_core:partner_role_view")
    table_width = False
    bulk_select_option = False
    header_attrs = [
        {"description": {"style": "width: 300px;"}},
    ]

    def no_record_add_button(self):
        if self.request.user.has_perm("horilla_core.add_partnerrole"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:partner_role_create_form')}?new=true""",
                "attrs": {"id": "partner-role-create"},
            }

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (
                instance._meta.get_field("partner_role_name").verbose_name,
                "partner_role_name",
            ),
            (instance._meta.get_field("description").verbose_name, "description"),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_partnerrole"):
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
        if self.request.user.has_perm("horilla_core.delete_partnerrole"):
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
    permission_required_or_denied("horilla_core.add_partnerrole"), name="dispatch"
)
class PartnerRoleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for partner role
    """

    model = PartnerRole
    fields = ["partner_role_name", "description"]
    full_width_fields = ["partner_role_name", "description"]
    modal_height = False
    form_title = _("partner role")

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_core:partner_role_update_form", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_core:partner_role_create_form")

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
    permission_required_or_denied("horilla_core.delete_partnerrole"), name="dispatch"
)
class PartnerRoleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = PartnerRole

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")
