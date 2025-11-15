"""
This view handles the methods for user view
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.filters import CompanyFilter
from horilla_core.models import Company
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaView,
)


class BranchesView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for branches page.
    """

    template_name = "branches/branches.html"
    nav_url = reverse_lazy("horilla_core:branches_nav_view")
    list_url = reverse_lazy("horilla_core:branches_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_company"), name="dispatch")
class BranchNavbar(LoginRequiredMixin, HorillaNavView):
    """
    navbar view for users
    """

    nav_title = Company._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_core:branches_list_view")
    main_url = reverse_lazy("horilla_core:branches_view")
    filterset_class = CompanyFilter
    model_name = "Company"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    url_name = "branches_list_view"
    one_view_only = True
    reload_option = False
    all_view_types = False

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_core.add_company"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:create_company')}?new=true""",
                "attrs": {"id": "branch-create"},
            }

    @cached_property
    def actions(self):
        if self.request.user.has_perm("horilla_core.view_company"):
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
    permission_required_or_denied("horilla_core.view_company"), name="dispatch"
)
class BranchListView(LoginRequiredMixin, HorillaListView):
    """
    List view of users
    """

    model = Company
    view_id = "branch-container"
    filterset_class = CompanyFilter
    search_url = reverse_lazy("horilla_core:branches_list_view")
    main_url = reverse_lazy("horilla_core:branches_view")
    bulk_update_two_column = True
    table_width = False
    bulk_select_option = False

    def no_record_add_button(self):
        if self.request.user.has_perm("horilla_core.add_company"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:create_company')}?new=true""",
                "attrs": 'id="branch-create"',
            }

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("name").verbose_name, "get_avatar_with_name"),
            (instance._meta.get_field("email").verbose_name, "email"),
            (
                instance._meta.get_field("no_of_employees").verbose_name,
                "no_of_employees",
            ),
            (instance._meta.get_field("hq").verbose_name, "hq"),
            (instance._meta.get_field("currency").verbose_name, "currency"),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_company"):
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
        if self.request.user.has_perm("horilla_core.delete_company"):
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
    def col_attrs(self):
        query_params = self.request.GET.dict()
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        attrs = {}
        if self.request.user.has_perm("horilla_core.view_company"):
            attrs = {
                "hx-get": f"{{get_detail_view_url}}?{query_string}",
                "hx-target": "#branches-view",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "hx-select": "#branches-view",
                "style": "cursor:pointer",
                "class": "hover:text-primary-600",
            }
        return [
            {
                "get_avatar_with_name": {
                    **attrs,
                }
            }
        ]


class BranchDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for user page
    """

    template_name = "branches/branch_detail_view.html"
    model = Company

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
        context["current_obj"] = current_obj
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_company"), name="dispatch"
)
class BranchDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = Company
    reassign_all_visibility = False
    reassign_individual_visibility = False
    hx_target = "#branches-view"

    def get_post_delete_response(self):
        branches_view_url = reverse_lazy("horilla_core:branches_view")
        response_html = (
            f"<span "
            f'hx-trigger="load" '
            f'hx-get="{branches_view_url}" '
            f'hx-select="#branches-view" '
            f'hx-target="#branches-view" '
            f'hx-swap="outerHTML" '
            f'hx-select-oob="#dropdown-companies">'
            f"</span>"
        )
        return HttpResponse(mark_safe(response_html))
