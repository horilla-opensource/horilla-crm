"""
This view handles the methods for user view
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.filters import UserFilter
from horilla_core.forms import UserFormClass
from horilla_core.models import HorillaUser
from horilla_generics.mixins import RecentlyViewedMixin
from horilla_generics.views import (
    HorillaDetailView,
    HorillaKanbanView,
    HorillaListView,
    HorillaMultiStepFormView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaView,
)


class UserView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for user page.
    """

    template_name = "settings/users/users_view.html"
    nav_url = reverse_lazy("horilla_core:user_nav_view")
    list_url = reverse_lazy("horilla_core:user_list_view")
    kanban_url = reverse_lazy("horilla_core:user_kanban_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_horillauser"), name="dispatch")
class UserNavbar(LoginRequiredMixin, HorillaNavView):
    """
    navbar view for users
    """

    nav_title = HorillaUser._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_core:user_list_view")
    main_url = reverse_lazy("horilla_core:user_view")
    filterset_class = UserFilter
    kanban_url = reverse_lazy("horilla_core:user_kanban_view")
    model_name = "HorillaUser"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    exclude_kanban_fields = "country"
    enable_actions = True

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_core.create_horillauser"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:user_create_form')}?new=true""",
                "attrs": {"id": "user-create"},
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_horillauser"), name="dispatch"
)
class UserListView(LoginRequiredMixin, HorillaListView):
    """
    List view of users
    """

    model = HorillaUser
    view_id = "UsersList"
    filterset_class = UserFilter
    search_url = reverse_lazy("horilla_core:user_list_view")
    main_url = reverse_lazy("horilla_core:user_view")
    bulk_update_two_column = True
    table_width = False
    bulk_delete_enabled = False
    table_height_as_class = "h-[500px]"

    def no_record_add_button(self):
        if self.request.user.has_perm("horilla_core.add_horillauser"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:user_create_form')}?new=true""",
                "attrs": 'id="user-create"',
            }

    bulk_update_fields = [
        "department",
        "role",
        "city",
        "state",
        "country",
        "zip_code",
        "language",
        "time_zone",
        "currency",
        "time_format",
        "date_format",
        "number_grouping",
    ]

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (_("First Name"), "get_avatar_with_name"),
            (instance._meta.get_field("state").verbose_name, "state"),
            (instance._meta.get_field("country").verbose_name, "get_country_display"),
            (instance._meta.get_field("contact_number").verbose_name, "contact_number"),
            (instance._meta.get_field("department").verbose_name, "department"),
            (instance._meta.get_field("role").verbose_name, "role"),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_horillauser"):
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
        if self.request.user.has_perm("horilla_core.delete_horillauser"):
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
        if self.request.user.has_perm("horilla_core.view_horillauser"):
            attrs = {
                "hx-get": f"{{get_detail_view_url}}?{query_string}",
                "hx-target": "#users-view",
                "hx-swap": "innerHTML",
                "hx-push-url": "true",
                "hx-select": "#users-view",
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

    def get_queryset(self):
        queryset = super().get_queryset()
        company = getattr(self.request, "active_company", None)
        queryset = queryset.filter(company=company)
        return queryset


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_horillauser"), name="dispatch"
)
class UserKanbanView(LoginRequiredMixin, HorillaKanbanView):
    """
    Kanban View for user
    """

    model = HorillaUser
    view_id = "UsersKanban"
    filterset_class = UserFilter
    search_url = reverse_lazy("horilla_core:user_list_view")
    main_url = reverse_lazy("horilla_core:user_view")
    group_by_field = "department"
    height_kanban = "h-[550px]"

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (_("First Name"), "first_name"),
            (instance._meta.get_field("role").verbose_name, "role"),
            (instance._meta.get_field("department").verbose_name, "department"),
            (instance._meta.get_field("contact_number").verbose_name, "contact_number"),
            (instance._meta.get_field("state").verbose_name, "state"),
            (instance._meta.get_field("country").verbose_name, "country"),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_horillauser"):
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
        if self.request.user.has_perm("horilla_core.delete_horillauser"):
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
class UserFormView(LoginRequiredMixin, HorillaMultiStepFormView):
    """
    Form view for user create and update
    """

    form_class = UserFormClass
    model = HorillaUser
    total_steps = 4
    step_titles = {
        "1": "Personal Information",
        "2": "Address Information",
        "3": "Work Information",
        "4": "Localization Information",
    }

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_core:user_edit_form", kwargs={"pk": pk})
        return reverse_lazy("horilla_core:user_create_form")

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk:
            try:
                self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                messages.error(request, "The requested user does not exist.")
                return HttpResponse("<script>$('reloadButton').click();</script>")
        if self.request.user.pk != self.kwargs.get(
            "pk"
        ) and not self.request.user.has_perm("horilla_core.add_horillauser"):
            return render(self.request, "error/403.html")

        return super().get(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_horillauser"), name="dispatch"
)
class UserDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = HorillaUser

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


class UserDetailView(RecentlyViewedMixin, LoginRequiredMixin, HorillaDetailView):
    """
    Detail view for user page
    """

    template_name = "settings/users/user_detail_view.html"
    model = HorillaUser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_obj = self.get_object()
        self.request.session["last_visited_url"] = self.request.get_full_path()
        context["current_obj"] = current_obj
        return context


class MyProfileView(LoginRequiredMixin, TemplateView):
    """
    my profile page
    """

    template_name = "settings/users/my_profile.html"


@method_decorator(htmx_required, name="dispatch")
class LoginHistoryView(LoginRequiredMixin, HorillaView):
    """
    Main login history view of user
    """

    template_name = "settings/users/users_view.html"
    nav_url = reverse_lazy("horilla_core:login_history_navbar")
    list_url = reverse_lazy("horilla_core:login_history_list")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_horillauser"), name="dispatch")
class LoginHistoryNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Login history navbar
    """

    from login_history.models import LoginHistory

    nav_title = LoginHistory._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_core:login_history_list")
    main_url = reverse_lazy("horilla_core:login_history_view")
    model_name = "LoginHistory"
    model_app_label = "loginhistory"
    nav_width = False
    gap_enabled = False
    navbar_indication = True
    all_view_types = False
    recently_viewed_option = False
    filter_option = False
    one_view_only = True
    reload_option = False
    border_enabled = False
    search_option = False

    def get_navbar_indication_attrs(self):

        last_url = self.request.session.get("last_visited_url")

        return {
            "hx-get": last_url,
            "hx-target": "#users-view",
            "hx-swap": "innerHTML",
            "hx-push-url": "true",
            "hx-select": "#users-view",
        }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_horillauser"), name="dispatch"
)
class LoginHistoryListView(LoginRequiredMixin, HorillaListView):
    """
    Login History list view of the user
    """

    from login_history.models import LoginHistory

    model = LoginHistory
    view_id = "LoginHistory"

    search_url = reverse_lazy("horilla_core:login_history_list")
    main_url = reverse_lazy("horilla_core:login_history_view")
    bulk_delete_enabled = False
    bulk_update_option = False
    enable_sorting = False
    table_width = False
    table_height_as_class = "h-[500px]"

    no_record_msg = "No login history available for this user."

    header_attrs = [
        {
            "short_user_agent": {"style": "width: 250px;"},
            "is_login_icon": {"style": "width: 80px;"},
            "ip": {"style": "width: 100px;"},
            "user_status": {"style": "width: 100px;"},
            "formatted_datetime": {"style": "width: 125px;"},
        },
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.GET.get("pk")
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (_("Browser"), "user_agent"),
            (_("Login Time"), "formatted_datetime"),
            (_("Is Active"), "is_login_icon"),
            (_("IP"), "ip"),
            (_("Status"), "user_status"),
        ]
